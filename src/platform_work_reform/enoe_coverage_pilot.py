"""National occupational-screen coverage diagnostics, without causal inference."""

import argparse
import csv
import hashlib
import io
import json
import sys
import zipfile
from collections import Counter
from pathlib import Path
from uuid import UUID

from platform_work_reform.config import Settings
from platform_work_reform.enoe_contract import key_fields, validate_header
from platform_work_reform.enoe_pilot_indicators import FIELDS, Audit
from platform_work_reform.enoe_preparation import audit as preparation_audit
from platform_work_reform.enoe_releases import release
from platform_work_reform.enoe_staging import ARCHIVE_SHA256, CONTRACTS, digest, members

VERSION = "enoe-coverage-pilot-v2"
PERIODS = ((2025, 2), (2025, 3), (2025, 4), (2026, 2))
GROUPS = ("passenger", "delivery", "passenger_narrow", "transport_delivery_broad")
DELIVERY = {"8344", "9321", "9722", "9723"}


def groups(occupation: str, activity: str) -> list[str]:
    """Overlapping sensitivity screens, never identified platform workers or bounds."""
    result = []
    if occupation == "8342":
        result.append("passenger")
        if activity == "4850":
            result.append("passenger_narrow")
    if occupation in DELIVERY:
        result.append("delivery")
    if occupation in DELIVERY | {"8341", "8342"}:
        result.append("transport_delivery_broad")
    return result


def records(archive, table, year, quarter, fields):
    """Read only ASCII codes; Latin-1 is a reversible byte transport, not text detection."""
    with archive.open(members(table, year, quarter)[0]) as raw:
        reader = csv.reader(io.TextIOWrapper(raw, encoding="latin-1", newline=""), strict=True)
        header = next(reader)
        validate_header(year, quarter, table, header)
        keys = key_fields(year, quarter, table)
        positions = [header.index(f) for f in (*keys, *fields)]
        seen = set()
        for row in reader:
            if len(row) != len(header):
                raise ValueError("Source width mismatch")
            values = [row[i].strip() for i in positions]
            for value in values:
                value.encode("ascii", errors="strict")
            key = tuple(values[: len(keys)])
            if not all(key) or key in seen:
                raise ValueError("Missing or duplicate source person key")
            seen.add(key)
            yield key, dict(zip(fields, values[len(keys) :], strict=True))


class Group:
    def __init__(self):
        self.n = Counter()
        self.w = Counter()
        self.composition = {f: Counter() for f in ("sex", "age", "education", "pos_ocu", "t_tra")}

    def add(self, sdem, coe1, coe2):
        weight = sdem["fac_tri"]
        if not weight.isascii() or not weight.isdigit() or int(weight) <= 0:
            raise ValueError("Invalid positive quarterly weight")
        weight = int(weight)
        formality = sdem["emp_ppal"]
        if formality not in {"", "0", "1", "2"}:
            raise ValueError("Invalid emp_ppal code")
        formal_state = {
            "1": "informal",
            "2": "formal",
            "0": "formality_not_applicable",
            "": "formality_blank",
        }[formality]
        self.n[formal_state] += 1
        self.w[formal_state] += weight
        medical = None if coe2 is None else coe2["p6d"]
        if medical not in {None, "", "1", "2", "3", "4", "5", "6", "9"}:
            raise ValueError("Invalid p6d code")
        state = (
            "missing_coe2"
            if medical is None
            else "blank_routing_unresolved"
            if medical == ""
            else "unknown"
            if medical == "9"
            else "imss"
            if medical == "1"
            else "other_known"
        )
        for key in ("all", state):
            self.n[key] += 1
            self.w[key] += weight
        if coe1["p4"] == "4":
            self.n["foreign_work"] += 1
            self.w["foreign_work"] += weight
        age = int(sdem["eda"])
        age_group = (
            "unspecified"
            if age == 98
            else "15_29"
            if age < 30
            else "30_49"
            if age < 50
            else "50_plus"
        )
        for name, value in {
            "sex": sdem["sex"],
            "age": age_group,
            "education": sdem["anios_esc"],
            "pos_ocu": sdem["pos_ocu"],
            "t_tra": sdem["t_tra"],
        }.items():
            self.composition[name][value or "blank"] += weight

    def report(self):
        total = self.w["all"]
        known = self.w["imss"] + self.w["other_known"]
        return {
            "sample": dict(self.n),
            "weighted": dict(self.w),
            "formal_percent_all": 100 * self.w["formal"] / total if total else None,
            "informal_percent_all": 100 * self.w["informal"] / total if total else None,
            "imss_percent_all": 100 * self.w["imss"] / total if total else None,
            "imss_percent_known": 100 * self.w["imss"] / known if known else None,
            "composition_weighted": {k: dict(v) for k, v in self.composition.items()},
        }


def profile(archive, year, quarter, completed):
    catalogues = {}
    catalogue_hashes = {}
    for table, field in (("COE1", "p3"), ("COE1", "p4a"), ("COE2", "p6d"), ("SDEM", "emp_ppal")):
        base = members(table, year, quarter)[0].split("/")[0]
        raw = archive.read(f"{base}/catalogos/{field}.csv")
        rows = list(csv.reader(io.StringIO(raw.decode("utf-8", errors="strict"))))
        if not rows or rows[0][0] != "CVE" or any(len(r) != 2 for r in rows):
            raise ValueError("Unexpected catalogue structure")
        codes = [r[0] for r in rows[1:]]
        if len(codes) != len(set(codes)):
            raise ValueError("Duplicate catalogue key")
        catalogues[field] = set(codes)
        catalogue_hashes[field] = hashlib.sha256(raw).hexdigest()
    c1 = dict(records(archive, "COE1", year, quarter, ("p3", "p4a", "p4")))
    c2 = dict(records(archive, "COE2", year, quarter, ("p6d",)))
    fields = (*FIELDS, "sex", "anios_esc", "pos_ocu", "t_tra", "emp_ppal")
    national = Audit(completed_code=completed)
    aggregates = {name: Group() for name in GROUPS}
    flow, weighted_flow = Counter(), Counter()
    for key, values in records(archive, "SDEM", year, quarter, fields):
        before = national.counts["eligible"]
        national.add(values, key in c1, key in c2)
        if national.counts["eligible"] == before or values["clase2"] != "1":
            continue
        if values["emp_ppal"] and values["emp_ppal"] not in catalogues["emp_ppal"]:
            raise ValueError("Out-of-catalogue occupied emp_ppal")
        first, second = c1.get(key), c2.get(key)
        for questionnaire, fields_to_check in ((first, ("p3", "p4a")), (second, ("p6d",))):
            if questionnaire:
                for field in fields_to_check:
                    if questionnaire[field] and questionnaire[field] not in catalogues[field]:
                        raise ValueError("Out-of-catalogue occupied response")
        occupation = first["p3"] if first else None
        state = (
            "missing_coe1"
            if first is None
            else "unknown_occupation"
            if occupation in {"", "9999"}
            else "classified_occupation"
        )
        flow[state] += 1
        weighted_flow[state] += int(values["fac_tri"])
        if first:
            for name in groups(occupation, first["p4a"]):
                aggregates[name].add(values, first, second)
    return {
        "catalogue_sha256": catalogue_hashes,
        "national": national.report(),
        "occupied_flow": dict(flow),
        "occupied_weighted_flow": dict(weighted_flow),
        "questionnaire_rows": {"COE1": len(c1), "COE2": len(c2)},
        "groups": {name: group.report() for name, group in aggregates.items()},
    }


def audit(settings, entry):
    year, quarter = entry["year"], entry["quarter"]
    path = Path(entry["archive"])
    reviewed = None if (year, quarter) == (2025, 3) else release(year, quarter)
    expected = ARCHIVE_SHA256 if reviewed is None else reviewed["archive_sha256"]
    if path.is_symlink() or not path.is_file() or digest(path) != expected:
        raise ValueError("Expected unchanged reviewed source archive")
    prepared = preparation_audit(settings, UUID(entry["run_id"]))
    if (
        prepared["source_sha256"] != expected
        or prepared["reference_period"] != f"{year}-{quarter * 3 - 2:02d}-01"
    ):
        raise ValueError("Run/archive period mismatch")
    with zipfile.ZipFile(path) as archive:
        if len(archive.namelist()) != len(set(archive.namelist())):
            raise ValueError("Duplicate archive members")
        result = profile(
            archive,
            year,
            quarter,
            "0" if reviewed is None else reviewed["completed_interview_code"],
        )
    expected_rows = (
        {c.name: c.rows for c in CONTRACTS}
        if reviewed is None
        else {k: v["rows"] for k, v in reviewed["tables"].items()}
    )
    if (
        digest(path) != expected
        or result["national"]["weighted_totals"] != prepared["weighted_totals"]
        or result["national"]["counts"] != prepared["counts"]
        or any(result["questionnaire_rows"][t] != expected_rows[t] for t in ("COE1", "COE2"))
    ):
        raise ValueError("Source/preparation reconciliation failed")
    return {
        "period": f"{year}Q{quarter}",
        "run_id": entry["run_id"],
        "archive": str(path),
        "source_sha256": expected,
        "reconciled": True,
        **result,
    }


def changes(periods):
    indexed = {p["period"]: p for p in periods}
    result = []
    for name in GROUPS:
        for metric in ("imss_percent_all", "imss_percent_known"):
            start = indexed["2025Q2"]["groups"][name][metric]
            end = indexed["2026Q2"]["groups"][name][metric]
            result.append(
                {
                    "group": name,
                    "metric": metric,
                    "change_pp": None if start is None or end is None else end - start,
                }
            )
    return result


METRICS = {
    "occupied": ("all", "Occupied population"),
    "formal": ("formal", "Formal principal employment"),
    "informal": ("informal", "Informal principal employment"),
    "formality_not_applicable": ("formality_not_applicable", "Formality not applicable"),
    "formality_blank": ("formality_blank", "Formality blank"),
    "imss": ("imss", "Reported principal-job IMSS access"),
}


def immediate_changes(periods):
    """Repeated-cross-section changes, not individual transitions or causal effects."""
    indexed = {p["period"]: p for p in periods}
    result = []
    for name in GROUPS:
        start, end = (indexed[p]["groups"][name] for p in ("2025Q2", "2025Q3"))
        for metric, (key, _) in METRICS.items():
            n0, n1 = (g["sample"].get(key, 0) for g in (start, end))
            w0, w1 = (g["weighted"].get(key, 0) for g in (start, end))
            d0, d1 = (g["weighted"].get("all", 0) for g in (start, end))
            p0, p1 = (100 * w / d if d else None for w, d in ((w0, d0), (w1, d1)))
            result.append(
                {
                    "group": name,
                    "metric": metric,
                    "baseline": "2025Q2",
                    "followup": "2025Q3",
                    "baseline_sample": n0,
                    "followup_sample": n1,
                    "baseline_weighted": w0,
                    "followup_weighted": w1,
                    "change_weighted": w1 - w0,
                    "baseline_percent": p0,
                    "followup_percent": p1,
                    "change_pp": None if p0 is None or p1 is None else p1 - p0,
                }
            )
    return result


def write_immediate(output_dir, rows):
    with (output_dir / "immediate.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    lines = [
        "# ENOE immediate occupational-screen diagnostic",
        "",
        "National occupied ages 15+; 2025 Q2 to Q3. Positive fac_tri. "
        "Principal-job formality is released emp_ppal; IMSS is reported p6d=1.",
        "",
        "| Screen | Measure | Q2 weighted people | Q3 weighted people | Change | "
        "Q2 share (%) | Q3 share (%) | Change (pp) |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        if row["metric"] not in {"occupied", "formal", "informal", "imss"}:
            continue
        shares = [
            "NA" if row[k] is None else f"{row[k]:.2f}"
            for k in ("baseline_percent", "followup_percent", "change_pp")
        ]
        lines.append(
            f"| {row['group']} | {METRICS[row['metric']][1]} | "
            f"{row['baseline_weighted']:,} | {row['followup_weighted']:,} | "
            f"{row['change_weighted']:+,} | " + " | ".join(shares) + " |"
        )
    lines += [
        "",
        "Descriptive repeated cross-sections: no platform identifier, individual "
        "transitions, causal effects, seasonal adjustment or significance claims. "
        "Precision remains unvalidated (#42). Q2 follows the announcement and partly "
        "overlaps legal effectiveness. IMSS access overlaps formal/informal categories; "
        "do not sum these measures. Missing/not-applicable formality states remain in "
        "the denominator and are exported in JSON/CSV. Source/run/hash provenance "
        "and medical missingness are in coverage.json.",
        "",
    ]
    (output_dir / "immediate.md").write_text("\n".join(lines))


def select_entries(entries, window):
    required = list(PERIODS[:2] if window == "immediate" else PERIODS)
    if not isinstance(entries, list):
        raise ValueError("Expected manifest list")
    periods = sorted((e["year"], e["quarter"]) for e in entries)
    if periods != required and not (window == "immediate" and periods == list(PERIODS)):
        raise ValueError("Exactly one reviewed run per required period is required")
    if len({e["run_id"] for e in entries}) != len(entries):
        raise ValueError("Duplicate run IDs")
    return sorted(
        (e for e in entries if (e["year"], e["quarter"]) in required),
        key=lambda e: (e["year"], e["quarter"]),
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--window", choices=("all", "immediate"), default="all")
    args = parser.parse_args()
    entries = json.loads(args.manifest.read_text())
    entries = select_entries(entries, args.window)
    periods = []
    for entry in sorted(entries, key=lambda e: (e["year"], e["quarter"])):
        print(f"Reconciling {entry['year']}Q{entry['quarter']}", file=sys.stderr)
        periods.append(audit(Settings.from_env(), entry))
    report = {
        "version": VERSION,
        "precision_validated": False,
        "causal_effect_estimated": False,
        "platform_population_identified": False,
        "screens": {
            "passenger": ["8342"],
            "delivery": sorted(DELIVERY),
            "passenger_narrow": "p3=8342 and p4a=4850",
            "transport_delivery_broad": sorted(DELIVERY | {"8341", "8342"}),
        },
        "limitations": [
            "Occupation screens include nonplatform work and omit secondary platform work.",
            "2025Q2 is not free of announcement or all legal exposure.",
            "No control group, confidence intervals or significance tests; issue #42 remains open.",
            "2026 instrument routing is not fully validated; foreign work and blanks retained.",
            (
                "All-person IMSS share keeps unknowns in the denominator, not as known negatives; "
                "known-response sensitivity is separate."
            ),
        ],
        "periods": periods,
        "same_quarter_changes": changes(periods) if args.window == "all" else None,
        "immediate_changes": immediate_changes(periods),
        "window": args.window,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "coverage.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    with (args.output_dir / "coverage.csv").open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(
            ("period", "group", "sample_n", "weighted_n", "imss_percent_all", "imss_percent_known")
        )
        for period in periods:
            for name, group in period["groups"].items():
                writer.writerow(
                    (
                        period["period"],
                        name,
                        group["sample"].get("all", 0),
                        group["weighted"].get("all", 0),
                        group["imss_percent_all"],
                        group["imss_percent_known"],
                    )
                )
    write_immediate(args.output_dir, report["immediate_changes"])
    print(
        json.dumps(
            {
                "output_dir": str(args.output_dir),
                "same_quarter_changes": report["same_quarter_changes"],
                "immediate_changes": report["immediate_changes"],
                "precision_validated": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
