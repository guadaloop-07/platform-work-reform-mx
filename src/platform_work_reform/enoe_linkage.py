"""Audit short-panel ENOE linkage; release aggregate feasibility diagnostics only."""

import argparse
import csv
import hashlib
import io
import json
import sys
import zipfile
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from uuid import UUID

from platform_work_reform.config import Settings
from platform_work_reform.enoe_contract import key_fields, validate_header
from platform_work_reform.enoe_pilot_indicators import FIELDS, Audit
from platform_work_reform.enoe_preparation import audit as preparation_audit
from platform_work_reform.enoe_releases import release
from platform_work_reform.enoe_staging import ARCHIVE_SHA256, CONTRACTS, digest, members
from platform_work_reform.enoe_transitions import TransitionAudit, write_transitions

VERSION = "enoe-linkage-audit-v2"
PERIODS = ((2025, 2), (2025, 3))
KEY = ("entity", "con", "v_sel", "n_hog", "h_mud", "n_ren")
DEMOGRAPHICS = ("n_ent", "sex", "nac_dia", "nac_mes", "nac_anio", "upm", "cd_a")
GROUPS = ("all_eligible", "passenger", "delivery", "passenger_narrow", "transport_delivery_broad")


def screens(row):
    """Baseline occupation-only screens; never select on subsequent employment."""
    result = ["all_eligible"] if row["eligible"] else []
    if not row["eligible"] or row["clase2"] != "1":
        return result
    occupation, activity = row.get("p3"), row.get("p4a")
    delivery = {"8344", "9321", "9722", "9723"}
    if occupation == "8342":
        result.append("passenger")
        if activity == "4850":
            result.append("passenger_narrow")
    if occupation in delivery:
        result.append("delivery")
    if occupation in delivery | {"8341", "8342"}:
        result.append("transport_delivery_broad")
    return result


def read_records(archive, table, quarter, fields):
    """Exact within-quarter keys, with ASCII-only selected codes and no text repair."""
    with archive.open(members(table, 2025, quarter)[0]) as stream:
        reader = csv.reader(io.TextIOWrapper(stream, encoding="latin-1", newline=""), strict=True)
        header = next(reader)
        validate_header(2025, quarter, table, header)
        selected = tuple(dict.fromkeys((*key_fields(2025, quarter, table), *fields)))
        positions = [header.index(name) for name in selected]
        seen = set()
        for raw in reader:
            if len(raw) != len(header):
                raise ValueError("Unexpected source width")
            row = dict(zip(selected, (raw[p].strip() for p in positions), strict=True))
            for value in row.values():
                value.encode("ascii", errors="strict")
            key = tuple(row[f] for f in key_fields(2025, quarter, table))
            if not all(key) or key in seen:
                raise ValueError("Missing or duplicate within-quarter person key")
            seen.add(key)
            yield key, row


def candidate_key(row):
    if row["tipo"] != "1":
        return None
    key = tuple(row[f] for f in KEY)
    return key if all(key) else None


def index_people(rows):
    """Quarantine every occurrence of reduced-key collisions; never choose first/last."""
    grouped = defaultdict(list)
    excluded = Counter()
    for row in rows:
        key = candidate_key(row)
        if key is None:
            excluded["unsupported_type" if row["tipo"] != "1" else "missing_key"] += 1
        else:
            grouped[key].append(row)
    unique = {key: values[0] for key, values in grouped.items() if len(values) == 1}
    ambiguous = {key for key, values in grouped.items() if len(values) > 1}
    return (
        unique,
        ambiguous,
        {
            "unique_candidate_keys": len(unique),
            "ambiguous_keys": len(ambiguous),
            "ambiguous_rows": sum(len(grouped[k]) for k in ambiguous),
            **dict(excluded),
        },
    )


def pair_evidence(first, second):
    """Conservative diagnostic rules; demographic consistency is not proof of identity."""
    conflicts, unresolved = [], []
    if first["n_ent"] not in {"1", "2", "3", "4"} or second["n_ent"] != str(
        int(first["n_ent"]) + 1
    ):
        conflicts.append("interview_progression")
    for field in ("upm", "cd_a"):
        if not first[field] or not second[field]:
            unresolved.append(f"missing_{field}")
        elif first[field] != second[field]:
            conflicts.append(f"changed_{field}")
    if first["sex"] not in {"1", "2"} or second["sex"] not in {"1", "2"}:
        unresolved.append("sex_unknown")
    elif first["sex"] != second["sex"]:
        conflicts.append("sex")
    if first["c_res"] in {"1", "3"} and second["c_res"] == "3":
        conflicts.append("followup_new_resident")
    ages = (first["eda"], second["eda"])
    if any(not a.isascii() or not a.isdigit() or int(a) >= 98 for a in ages):
        unresolved.append("age_unknown")
    elif "97" in ages:
        if ages[1] == "97" and ages[0] in {"96", "97"}:
            pass  # 97 is a capped age category, not a literal birthday.
        else:
            conflicts.append("age")
    elif int(ages[1]) - int(ages[0]) not in {0, 1}:
        conflicts.append("age")
    birth_known = 0
    for field, maximum in (("nac_dia", 31), ("nac_mes", 12), ("nac_anio", 2025)):
        values = (first[field], second[field])
        lower = 1900 if field == "nac_anio" else 1
        known = [v.isascii() and v.isdigit() and lower <= int(v) <= maximum for v in values]
        if all(known):
            birth_known += 1
            if int(values[0]) != int(values[1]):
                conflicts.append(field)
    for label, person in (("baseline", first), ("followup", second)):
        values = [person[f] for f in ("nac_anio", "nac_mes", "nac_dia")]
        if all(v.isascii() and v.isdigit() for v in values):
            year, month, day = map(int, values)
            if year != 9999 and month != 99 and day != 99:
                try:
                    date(year, month, day)
                except ValueError:
                    conflicts.append(f"invalid_birth_calendar_{label}")
    return {
        "conflicts": conflicts,
        "unresolved": unresolved,
        "birth_components_comparable": birth_known,
        "supported": not conflicts and not unresolved,
    }


def composition(row):
    age = int(row["eda"])
    return {
        "sex": row["sex"],
        "age": "unknown"
        if age >= 98
        else "15_29"
        if age < 30
        else "30_49"
        if age < 50
        else "50_plus",
        "clase2": row["clase2"],
        "pos_ocu": row["pos_ocu"] or "blank",
    }


def audit_pairs(baseline, followup, *, include_transitions=False):
    transitions = TransitionAudit(GROUPS) if include_transitions else None
    left, left_ambiguous, left_info = index_people(baseline)
    right, right_ambiguous, right_info = index_people(followup)
    household = {key[:5] for key in right}
    dwelling = {key[:3] for key in right}
    household_slot = {key[:4] for key in right}
    summaries = {
        name: {"flow": Counter(), "composition": defaultdict(Counter), "followup": Counter()}
        for name in GROUPS
    }
    diagnostics = Counter()
    matrix = Counter()
    residence_matrix = Counter()
    for key in left.keys() & right.keys():
        a, b = left[key], right[key]
        matrix[f"{a['n_ent']}->{b['n_ent']}"] += 1
        residence_matrix[f"{a['c_res']}->{b['c_res']}"] += 1
        evidence = pair_evidence(a, b)
        diagnostics["candidate_pairs"] += 1
        diagnostics[f"birth_components_comparable_{evidence['birth_components_comparable']}"] += 1
        diagnostics.update(f"conflict_{c}" for c in evidence["conflicts"])
        diagnostics.update(f"unresolved_{c}" for c in evidence["unresolved"])
    # Iterate original rows so ambiguous baseline members are not silently dropped.
    for a in baseline:
        names = screens(a)
        if not names:
            continue
        key = candidate_key(a)
        b = right.get(key)
        if key is None:
            status = "unsupported_type_or_missing_key"
        elif key in left_ambiguous:
            status = "ambiguous_baseline_key"
        elif a["n_ent"] == "5":
            status = "scheduled_rotation_exit"
        elif a["n_ent"] not in {"1", "2", "3", "4"}:
            status = "unknown_baseline_interview"
        elif key in right_ambiguous:
            status = "ambiguous_followup_key"
        elif b is None:
            status = (
                "unmatched_person_household_observed"
                if key[:5] in household
                else "unmatched_household_replacement_possible"
                if key[:4] in household_slot
                else "unmatched_household_dwelling_observed"
                if key[:3] in dwelling
                else "unmatched_dwelling_not_in_sdem"
            )
        else:
            evidence = pair_evidence(a, b)
            status = (
                "candidate_conflict"
                if evidence["conflicts"]
                else "candidate_unresolved"
                if evidence["unresolved"]
                else "supported_followup_outside_universe"
                if not b["eligible"]
                else "supported_both_eligible"
            )
        if transitions is not None:
            transitions.add_baseline(a, names, status)
        if status == "supported_both_eligible" and transitions is not None:
            transitions.add_pair(a, b, names, pair_evidence(a, b)["birth_components_comparable"])
        for name in names:
            group = summaries[name]
            group["flow"]["baseline"] += 1
            group["flow"][status] += 1
            continuing = key is not None and a["n_ent"] in {"1", "2", "3", "4"}
            group["flow"]["continuing_baseline"] += continuing
            group["flow"]["candidate_continuing"] += (
                continuing and key not in left_ambiguous and key in right
            )
            bucket = (
                "supported"
                if status == "supported_both_eligible"
                else "scheduled_exit"
                if status == "scheduled_rotation_exit"
                else "other"
            )
            for field, value in composition(a).items():
                group["composition"][f"{bucket}|{field}"][value] += 1
            if status.startswith("unmatched_"):
                for field, value in composition(a).items():
                    group["composition"][f"unmatched|{field}"][value] += 1
            if status == "supported_both_eligible":
                evidence = pair_evidence(a, b)
                group["followup"][
                    f"birth_components_comparable_{evidence['birth_components_comparable']}"
                ] += 1
                group["followup"]["coe1_present"] += b["coe1_present"]
                group["followup"]["coe2_present"] += b["coe2_present"]
                group["followup"]["occupied"] += b["clase2"] == "1"
                group["followup"]["same_screen"] += name in screens(b)
    output = {}
    for name, values in summaries.items():
        flow = values["flow"]
        denominator = flow["continuing_baseline"]
        output[name] = {
            "flow": dict(flow),
            "supported_percent_of_continuing": 100 * flow["supported_both_eligible"] / denominator
            if denominator
            else None,
            "composition_sample_counts": {k: dict(v) for k, v in values["composition"].items()},
            "followup_availability": dict(values["followup"]),
        }
    return {
        "baseline_key_audit": left_info,
        "followup_key_audit": right_info,
        "candidate_diagnostics": dict(diagnostics),
        "interview_matrix": dict(matrix),
        "candidate_residence_matrix": dict(residence_matrix),
        "baseline_type_interview_counts": dict(
            Counter(f"{r['tipo']}|{r['n_ent']}" for r in baseline)
        ),
        "followup_type_interview_counts": dict(
            Counter(f"{r['tipo']}|{r['n_ent']}" for r in followup)
        ),
        "followup_first_interview_rows": sum(r["n_ent"] == "1" for r in followup),
        "groups": output,
        "sample_transitions": transitions.report() if transitions is not None else None,
    }


def load_period(settings, entry, *, include_transitions=False):
    quarter = entry["quarter"]
    if (entry["year"], quarter) not in PERIODS:
        raise ValueError("Unsupported period")
    path = Path(entry["archive"])
    reviewed = release(2025, 2) if quarter == 2 else None
    expected_hash = reviewed["archive_sha256"] if reviewed else ARCHIVE_SHA256
    expected_rows = (
        {k: v["rows"] for k, v in reviewed["tables"].items()}
        if reviewed
        else {c.name: c.rows for c in CONTRACTS}
    )
    if path.is_symlink() or not path.is_file() or digest(path) != expected_hash:
        raise ValueError("Expected unchanged reviewed archive")
    prepared = preparation_audit(settings, UUID(entry["run_id"]))
    if (
        prepared["source_sha256"] != expected_hash
        or prepared["reference_period"] != f"2025-{quarter * 3 - 2:02d}-01"
    ):
        raise ValueError("Run/archive period mismatch")
    with zipfile.ZipFile(path) as archive:
        if len(archive.namelist()) != len(set(archive.namelist())):
            raise ValueError("Duplicate archive members")
        dictionary_raw = archive.read(members("SDEM", 2025, quarter)[1])
        dictionary_hash = hashlib.sha256(dictionary_raw).hexdigest()
        c1 = dict(read_records(archive, "COE1", quarter, ("p3", "p4a")))
        c2 = {key for key, _ in read_records(archive, "COE2", quarter, ())}
        catalogues, provenance = {}, {}
        catalogue_fields = [("COE1", "p3"), ("COE1", "p4a")]
        if include_transitions:
            catalogue_fields.append(("SDEM", "emp_ppal"))
        for table, field in catalogue_fields:
            base = members(table, 2025, quarter)[0].split("/")[0]
            raw = archive.read(f"{base}/catalogos/{field}.csv")
            rows = list(csv.reader(io.StringIO(raw.decode("utf-8", errors="strict")), strict=True))
            if not rows or any(len(r) != 2 for r in rows) or rows[0][0] != "CVE":
                raise ValueError("Invalid catalogue")
            catalogues[field] = {r[0] for r in rows[1:]}
            if len(catalogues[field]) != len(rows) - 1:
                raise ValueError("Duplicate catalogue keys")
            provenance[field] = hashlib.sha256(raw).hexdigest()
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
        )
        if include_transitions:
            selected = (*selected, "emp_ppal", "est_d_tri")
        national = Audit()
        people = []
        selected_hash = hashlib.sha256()
        for key, row in read_records(archive, "SDEM", quarter, selected):
            selected_hash.update(
                (json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode("ascii")
            )
            before = national.counts["eligible"]
            national.add(row, key in c1, key in c2)
            row["eligible"] = national.counts["eligible"] > before
            row["entity"] = row["ent" if quarter == 2 else "cve_ent"]
            row["coe1_present"], row["coe2_present"] = key in c1, key in c2
            row["p3"] = c1[key]["p3"] if key in c1 else None
            row["p4a"] = c1[key]["p4a"] if key in c1 else None
            if row["eligible"] and row["clase2"] == "1" and key in c1:
                for field in ("p3", "p4a"):
                    if row[field] and row[field] not in catalogues[field]:
                        raise ValueError("Out-of-catalogue occupied response")
            if include_transitions and row["eligible"] and row["clase2"] == "1":
                if row["emp_ppal"] and row["emp_ppal"] not in catalogues["emp_ppal"]:
                    raise ValueError("Out-of-catalogue emp_ppal")
            people.append(row)
    report = national.report()
    if (
        digest(path) != expected_hash
        or report["counts"] != prepared["counts"]
        or report["weighted_totals"] != prepared["weighted_totals"]
        or len(c1) != expected_rows["COE1"]
        or len(c2) != expected_rows["COE2"]
    ):
        raise ValueError("Source/preparation reconciliation failed")
    return people, {
        "period": f"2025Q{quarter}",
        "run_id": entry["run_id"],
        "archive": str(path),
        "source_sha256": expected_hash,
        "selected_sdem_sha256": selected_hash.hexdigest(),
        "sdem_dictionary_sha256": dictionary_hash,
        "catalogue_sha256": provenance,
        "national_reconciliation": report,
    }


def write_summary(output, report):
    rows = []
    for name, group in report["groups"].items():
        f = group["flow"]
        rows.append(
            {
                "screen": name,
                "baseline_sample": f.get("baseline", 0),
                "scheduled_exit": f.get("scheduled_rotation_exit", 0),
                "continuing_sample": f.get("continuing_baseline", 0),
                "supported_both_eligible": f.get("supported_both_eligible", 0),
                "supported_percent_of_continuing": group["supported_percent_of_continuing"],
            }
        )
    with (output / "linkage.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    lines = [
        "# ENOE 2025 Q2–Q3 linkage feasibility",
        "",
        "Unweighted sample counts. Candidate key: entity, con, v_sel, n_hog, h_mud, n_ren; tipo=1.",
        "",
        "| Baseline screen | Sample | Scheduled fifth-interview exits | Continuing | "
        "Supported both eligible | % of continuing |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        rate = row["supported_percent_of_continuing"]
        lines.append(
            f"| {row['screen']} | {row['baseline_sample']:,} | {row['scheduled_exit']:,} | "
            f"{row['continuing_sample']:,} | {row['supported_both_eligible']:,} | "
            + ("NA" if rate is None else f"{rate:.2f}")
            + " |"
        )
    lines += [
        "",
        "Supported means unique keys, advancing interview, stable context, "
        "compatible sex/age and no comparable birth-date conflict. "
        "It does not prove identity. Missing birth components are recorded, not imputed. "
        "Baseline screens do not require occupation continuity. "
        "Unmatched records are not automatically attrition. "
        "No longitudinal weights, national transitions, platform identification, "
        "causal effects or validated precision are supplied.",
        "",
    ]
    (output / "linkage.md").write_text("\n".join(lines))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--transitions", action="store_true")
    args = parser.parse_args()
    entries = json.loads(args.manifest.read_text())
    if not isinstance(entries, list):
        raise ValueError("Expected manifest list")
    periods = [(e["year"], e["quarter"]) for e in entries]
    if any(p not in {(2025, 2), (2025, 3), (2025, 4), (2026, 2)} for p in periods):
        raise ValueError("Unsupported manifest period")
    if len(periods) != len(set(periods)) or len({e["run_id"] for e in entries}) != len(entries):
        raise ValueError("Duplicate period or run")
    chosen = sorted(
        (e for e in entries if (e["year"], e["quarter"]) in PERIODS), key=lambda e: e["quarter"]
    )
    if len(chosen) != 2:
        raise ValueError("Both reviewed 2025 Q2 and Q3 are required")
    loaded, provenance = [], []
    for entry in chosen:
        print(f"Reconciling 2025Q{entry['quarter']}", file=sys.stderr)
        people, source = load_period(
            Settings.from_env(), entry, include_transitions=args.transitions
        )
        loaded.append(people)
        provenance.append(source)
    report = {
        "version": VERSION,
        "source_provenance": provenance,
        "national_transition_estimates": False,
        "precision_validated": False,
        **audit_pairs(*loaded, include_transitions=args.transitions),
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "linkage.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    write_summary(args.output_dir, report)
    if args.transitions:
        write_transitions(args.output_dir, report)
        print((args.output_dir / "transitions.md").read_text())
    else:
        print((args.output_dir / "linkage.md").read_text())


if __name__ == "__main__":
    main()
