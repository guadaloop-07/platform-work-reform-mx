"""Compare fixed Q2–Q3 linked-sample transitions in 2023–2025, without inference."""

import argparse
import csv
import gc
import hashlib
import io
import json
import sys
import zipfile
from pathlib import Path

from platform_work_reform.enoe_linkage import DEMOGRAPHICS, GROUPS, audit_pairs, read_records
from platform_work_reform.enoe_pilot_indicators import FIELDS, Audit
from platform_work_reform.enoe_staging import digest, members

VERSION = "enoe-historical-transitions-v1"
YEARS = (2023, 2024, 2025)
# Freeze parity with the source-reconciled PR #66 result; never tune to historical outcomes.
PARITY_2025 = {
    "all_eligible": (215462, 65173, 7931, 61300, 7685),
    "passenger": (2878, 2018, 348, 860, 264),
    "delivery": (1059, 768, 82, 291, 85),
    "passenger_narrow": (2628, 1958, 334, 670, 237),
    "transport_delivery_broad": (6686, 3678, 625, 3008, 589),
}
PARITY_FIELDS = (
    "linked_n",
    "linked_baseline_informal_n",
    "informal_to_formal_n",
    "linked_baseline_formal_n",
    "formal_to_informal_n",
)


def contracts():
    data = json.loads(Path(__file__).with_name("enoe_history_sources.json").read_text())
    if set(data) != {f"{y}q{q}" for y in YEARS for q in (2, 3)}:
        raise ValueError("Exactly six reviewed source contracts are required")
    for field in ("p3", "p4a", "emp_ppal", "c_res", "n_ent", "clase1", "clase2"):
        meanings = [c["catalogues"][field]["selected_descriptions"] for c in data.values()]
        if any(m != meanings[0] for m in meanings):
            raise ValueError("Selected source meanings require an explicit crosswalk")
    return data


def member_hash(archive, name):
    with archive.open(name) as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def load_source(data_root, contract):
    year, quarter = contract["year"], contract["quarter"]
    path = data_root / f"{year}q{quarter}" / f"enoe-{year}q{quarter}-official.zip"
    if path.is_symlink() or not path.is_file() or digest(path) != contract["archive_sha256"]:
        raise ValueError("Expected unchanged reviewed historical archive")
    with zipfile.ZipFile(path) as archive:
        if len(archive.namelist()) != len(set(archive.namelist())):
            raise ValueError("Duplicate archive members")
        for table, spec in contract["tables"].items():
            if member_hash(archive, spec["member"]) != spec["member_sha256"]:
                raise ValueError("Source member hash mismatch")
            if member_hash(archive, members(table, year, quarter)[1]) != spec["dictionary_sha256"]:
                raise ValueError("Dictionary hash mismatch")
        catalogues = {}
        for field, spec in contract["catalogues"].items():
            raw = archive.read(spec["member"])
            if hashlib.sha256(raw).hexdigest() != spec["sha256"]:
                raise ValueError("Catalogue hash mismatch")
            parsed = list(
                csv.reader(io.StringIO(raw.decode("utf-8", errors="strict")), strict=True)
            )
            if not parsed or parsed[0] != ["CVE", "DESCRIP"] or any(len(r) != 2 for r in parsed):
                raise ValueError("Unexpected source catalogue")
            codes = {r[0]: r[1] for r in parsed[1:]}
            if len(codes) != len(parsed) - 1 or any(
                codes[k] != v for k, v in spec["selected_descriptions"].items()
            ):
                raise ValueError("Source catalogue meaning mismatch")
            catalogues[field] = codes

        def read(table, fields):
            return read_records(
                archive,
                table,
                quarter,
                fields,
                year=year,
                source_contract=contract["tables"][table],
            )

        c1 = dict(read("COE1", ("p3", "p4a")))
        c2 = {key for key, _ in read("COE2", ())}
        selected = (
            *FIELDS,
            *DEMOGRAPHICS,
            "tipo",
            "con",
            "v_sel",
            "n_hog",
            "h_mud",
            "n_ren",
            "pos_ocu",
            "emp_ppal",
            "est_d_tri",
        )
        population = Audit(completed_code=contract["completed_code"])
        people, fingerprint = [], hashlib.sha256()
        for key, row in read("SDEM", selected):
            fingerprint.update(
                (json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode("ascii")
            )
            before = population.counts["eligible"]
            population.add(row, key in c1, key in c2)
            row["eligible"] = population.counts["eligible"] > before
            row["entity"] = row[contract["entity_field"]]
            row["coe1_present"], row["coe2_present"] = key in c1, key in c2
            row["p3"] = c1[key]["p3"] if key in c1 else None
            row["p4a"] = c1[key]["p4a"] if key in c1 else None
            if row["eligible"] and row["clase2"] == "1":
                for field in ("p3", "p4a", "emp_ppal"):
                    if row[field] and row[field] not in catalogues[field]:
                        raise ValueError("Out-of-catalogue occupied response")
            people.append(row)
    national = population.report()
    counts = national["counts"]
    if (
        len(people) != contract["tables"]["SDEM"]["rows"]
        or len(c1) != contract["tables"]["COE1"]["rows"]
        or len(c2) != contract["tables"]["COE2"]["rows"]
        or counts.get("coe1_matched") != len(c1)
        or counts.get("coe2_matched") != len(c2)
        or national["weighted_totals"] != contract["reference_totals"]
        or digest(path) != contract["archive_sha256"]
    ):
        raise ValueError(
            f"Source/reference reconciliation failed for {year}Q{quarter}: "
            f"{national['weighted_totals']}"
        )
    return people, {
        "year": year,
        "quarter": quarter,
        "archive": str(path),
        "archive_sha256": contract["archive_sha256"],
        "url": contract["url"],
        "reference_url": contract["reference_url"],
        "national_reconciliation": national,
        "selected_sdem_sha256": fingerprint.hexdigest(),
        "reconciled": True,
    }


def summary_rows(year, audit):
    result = []
    for name in GROUPS:
        group = audit["sample_transitions"]["groups"][name]
        flow = audit["groups"][name]["flow"]
        result.append(
            {
                "year": year,
                "screen": name,
                **group["summary"],
                "baseline_sample_n": flow.get("baseline", 0),
                "continuing_sample_n": flow.get("continuing_baseline", 0),
                "supported_percent_of_continuing": audit["groups"][name][
                    "supported_percent_of_continuing"
                ],
                "full_birth_forward_percent": group["full_birth_sensitivity"][
                    "informal_to_formal_percent"
                ],
            }
        )
    return result


def compare(rows):
    expected = {(year, name) for year in YEARS for name in GROUPS}
    keys = [(r["year"], r["screen"]) for r in rows]
    if len(keys) != len(set(keys)) or set(keys) != expected:
        raise ValueError("Exactly one summary per fixed year and screen is required")
    indexed = {(r["year"], r["screen"]): r for r in rows}
    result = []
    for name in GROUPS:
        for metric in ("informal_to_formal_percent", "formal_to_informal_percent"):
            prior = [indexed[(year, name)][metric] for year in (2023, 2024)]
            current = indexed[(2025, name)][metric]
            complete = current is not None and all(p is not None for p in prior)
            result.append(
                {
                    "screen": name,
                    "metric": metric,
                    "value_2025": current,
                    "value_2023": prior[0],
                    "value_2024": prior[1],
                    "difference_vs_2023_pp": current - prior[0]
                    if current is not None and prior[0] is not None
                    else None,
                    "difference_vs_2024_pp": current - prior[1]
                    if current is not None and prior[1] is not None
                    else None,
                    "difference_vs_prior_year_mean_pp": current - sum(prior) / 2
                    if complete
                    else None,
                    "outside_two_prior_values": (current < min(prior) or current > max(prior))
                    if complete
                    else None,
                }
            )
    return result


def check_parity(audit):
    for name, expected in PARITY_2025.items():
        summary = audit["sample_transitions"]["groups"][name]["summary"]
        if tuple(summary[k] for k in PARITY_FIELDS) != expected:
            raise ValueError("2025 linkage/transition parity failed")


def write_comparison(output, report):
    rows = report["summary"]
    with (output / "comparison.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    lines = [
        "# ENOE historical Q2–Q3 sample transitions",
        "",
        "Fixed baseline occupational screens, TIPO=1, consistency-supported eligible pairs. "
        "Rates are unweighted and include follow-up nonemployment "
        "in the baseline-state denominator.",
        "",
        "| Year | Screen | Linked pairs | Informal at baseline | Informal to formal | % | "
        "Formal to informal | Reverse % | Retained continuing % |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]

    def fmt(v):
        return "NA" if v is None else f"{v:.2f}"

    for r in rows:
        lines.append(
            f"| {r['year']} | {r['screen']} | {r['linked_n']:,} | "
            f"{r['linked_baseline_informal_n']:,} | "
            f"{r['informal_to_formal_n']:,} | {fmt(r['informal_to_formal_percent'])} | "
            f"{r['formal_to_informal_n']:,} | {fmt(r['formal_to_informal_percent'])} | "
            f"{fmt(r['supported_percent_of_continuing'])} |"
        )
    lines += [
        "",
        "## Descriptive 2025 comparisons",
        "",
        "| Screen | Direction | 2025 minus 2023 (pp) | 2025 minus 2024 (pp) | "
        "2025 minus equal-year prior mean (pp) |",
        "|---|---|---:|---:|---:|",
    ]
    for c in report["contrasts"]:
        lines.append(
            f"| {c['screen']} | {c['metric']} | {fmt(c['difference_vs_2023_pp'])} | "
            f"{fmt(c['difference_vs_2024_pp'])} | {fmt(c['difference_vs_prior_year_mean_pp'])} |"
        )
    lines += [
        "",
        "Two prior values are not a historical sampling distribution or prediction interval. "
        "An outside-range value is descriptive only, not a significant anomaly or reform effect. "
        "No national expansion, longitudinal weights, confidence intervals "
        "or p-values are supplied. "
        "Age/sex/position composition, retention, full-date sensitivity "
        "and full matrices are in comparison.json. "
        "Screens include nonplatform work and can overlap; "
        "follow-up occupation need not remain the same.",
        "",
    ]
    (output / "comparison.md").write_text("\n".join(lines))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=Path("data/enoe/official"))
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    specs = contracts()
    years = []
    rows = []
    for year in YEARS:
        print(f"Reading and reconciling {year} Q2/Q3", file=sys.stderr)
        first, first_meta = load_source(args.data_root, specs[f"{year}q2"])
        second, second_meta = load_source(args.data_root, specs[f"{year}q3"])
        audit = audit_pairs(first, second, include_transitions=True, year=year)
        if year == 2025:
            check_parity(audit)
        rows.extend(summary_rows(year, audit))
        years.append({"year": year, "sources": [first_meta, second_meta], "audit": audit})
        del first, second
        gc.collect()
    report = {
        "version": VERSION,
        "years": years,
        "summary": rows,
        "contrasts": compare(rows),
        "weighted": False,
        "precision_validated": False,
        "causal_effect_estimated": False,
        "prior_mean_definition": (
            "Arithmetic mean of 2023 and 2024 sample rates, not pooled or population weighted."
        ),
        "parity_2025_passed": True,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "comparison.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    write_comparison(args.output_dir, report)
    print((args.output_dir / "comparison.md").read_text())


if __name__ == "__main__":
    main()
