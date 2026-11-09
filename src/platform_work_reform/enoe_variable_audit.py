"""Audit selected ENOE fields against original catalogues; emit aggregates only."""

import argparse
import csv
import hashlib
import io
import json
import zipfile
from collections import Counter
from datetime import date
from pathlib import Path
from uuid import UUID

import psycopg
from psycopg import sql

from platform_work_reform.config import Settings
from platform_work_reform.enoe_contract import key_fields, validate_header
from platform_work_reform.enoe_pilot_indicators import FIELDS as BASE
from platform_work_reform.enoe_pilot_indicators import Audit
from platform_work_reform.enoe_preparation import audit as preparation_audit
from platform_work_reform.enoe_releases import release
from platform_work_reform.enoe_staging import ARCHIVE_SHA256, CONTRACTS, digest, members

VERSION = "enoe-variable-audit-v1"
FIELDS = {
    "SDEM": (
        "c_ocu11c",
        "rama",
        "scian",
        "pos_ocu",
        "seg_soc",
        "medica5c",
        "imssissste",
        "emp_ppal",
        "t_tra",
    ),
    "COE1": ("p3", "p4a", "p4"),
    "COE2": ("p6d", "p7"),
}
UNSPECIFIED = dict(
    zip(
        (
            "c_ocu11c",
            "rama",
            "scian",
            "pos_ocu",
            "seg_soc",
            "medica5c",
            "imssissste",
            "p3",
            "p4a",
            "p4",
            "p6d",
            "p7",
        ),
        ("11", "7", "21", "5", "3", "5", "5", "9999", "9999", "9", "9", "9"),
        strict=True,
    )
)


def parse_catalogue(raw: bytes, *, anomalous: bool = False) -> dict[str, str]:
    """Read keys without repairing original bytes or accepting arbitrary ragged rows."""
    rows = list(csv.reader(io.StringIO(raw.decode("utf-8", errors="strict")), strict=True))
    width = 3 if anomalous else 2
    if not rows or len(rows[0]) < 2 or rows[0][0] != "CVE" or rows[0][1].strip() != "DESCRIP":
        raise ValueError("Unexpected catalogue header")
    if len(rows[0]) != width or (anomalous and rows[0][2] != ""):
        raise ValueError("Unexpected catalogue width")
    result = {}
    for row in rows[1:]:
        if len(row) != width or not row[0] or row[0] in result:
            raise ValueError("Malformed or duplicate catalogue key")
        if anomalous and row[2] and row[0] != "1":
            raise ValueError("Unexpected catalogue anomaly")
        result[row[0]] = ",".join(row[1:]).rstrip(",") if anomalous else row[1]
    return result


def state(field: str, value: str | None, codes: dict[str, str]) -> str:
    if value is None:
        return "missing_questionnaire"
    if value == "":
        return "blank_routing_unresolved"
    if value not in codes:
        return "invalid_code"
    if value == "0" and field in FIELDS["SDEM"]:
        return "coded_not_applicable"
    if value == UNSPECIFIED.get(field):
        return "unspecified"
    if field == "p4a" and "insuficientemente especificad" in codes[value].casefold():
        return "insufficient_detail"
    return "substantive_code"


def fingerprint(records):
    """Hash ordered row numbers, exact keys and selected logical ASCII field values."""
    hasher = hashlib.sha256()
    count = 0
    for number, key, values in records:
        count += 1
        if number != count:
            raise ValueError("Noncontiguous original row numbers")
        hasher.update(
            (
                json.dumps(
                    [number, list(key), list(values)], ensure_ascii=True, separators=(",", ":")
                )
                + "\n"
            ).encode("ascii")
        )
    return count, hasher.hexdigest()


def source_records(archive, table, year, quarter):
    selected = (*BASE, *FIELDS[table]) if table == "SDEM" else FIELDS[table]
    with archive.open(members(table, year, quarter)[0]) as raw:
        reader = csv.reader(io.TextIOWrapper(raw, encoding="latin-1", newline=""), strict=True)
        header = next(reader)
        validate_header(year, quarter, table, header)
        positions = [header.index(f) for f in (*key_fields(year, quarter, table), *selected)]
        width = len(key_fields(year, quarter, table))
        for number, row in enumerate(reader, 1):
            if len(row) != len(header):
                raise ValueError("Source row width mismatch")
            values = [row[i] for i in positions]
            # Selected fields and keys are codes, never ambiguously decoded free text.
            for value in values:
                value.encode("ascii", errors="strict")
            yield number, tuple(values[:width]), tuple(values[width:])


def profile(archive, year, quarter, catalogues, completed):
    questionnaires = {}
    for table in ("COE1", "COE2"):
        records = {}
        for _, key, values in source_records(archive, table, year, quarter):
            if key in records:
                raise ValueError("Duplicate questionnaire person key")
            records[key] = tuple(v.strip() for v in values)
        questionnaires[table] = records
    national = Audit(completed_code=completed)
    counts, weights, distributions = {}, {}, {}
    for fields in FIELDS.values():
        for field in fields:
            counts[field], weights[field], distributions[field] = Counter(), Counter(), Counter()
    flow, flow_weights = Counter(), Counter()
    joint = {
        name: Counter() for name in ("p6d_imssissste", "p6d_seg_soc", "p7_t_tra", "p4_p6d", "p4_p7")
    }
    joint_weights = {name: Counter() for name in joint}
    for _, key, raw in source_records(archive, "SDEM", year, quarter):
        values = dict(zip((*BASE, *FIELDS["SDEM"]), (v.strip() for v in raw), strict=True))
        c1, c2 = questionnaires["COE1"].get(key), questionnaires["COE2"].get(key)
        before = national.counts["eligible"]
        national.add(values, c1 is not None, c2 is not None)
        if national.counts["eligible"] == before:
            flow["outside_national_universe"] += 1
            continue
        if values["clase2"] != "1":
            flow["eligible_not_occupied"] += 1
            flow_weights["eligible_not_occupied"] += int(values["fac_tri"])
            continue
        w = int(values["fac_tri"])
        flow["occupied"] += 1
        flow_weights["occupied"] += w
        flow["occupied_missing_coe1"] += c1 is None
        flow["occupied_missing_coe2"] += c2 is None
        flow_weights["occupied_missing_coe1"] += w if c1 is None else 0
        flow_weights["occupied_missing_coe2"] += w if c2 is None else 0
        all_values = dict(values)
        for table, coe in [("COE1", c1), ("COE2", c2)]:
            all_values.update(
                dict(zip(FIELDS[table], coe or (None,) * len(FIELDS[table]), strict=True))
            )
        for fields in FIELDS.values():
            for field in fields:
                value = all_values[field]
                status = state(field, value, catalogues[field])
                counts[field][status] += 1
                weights[field][status] += w
                # No person keys or free text appear in output, including invalid cases.
                if value is not None and status != "invalid_code":
                    distributions[field][value] += 1
        for name, fields in {
            "p6d_imssissste": ("p6d", "imssissste"),
            "p6d_seg_soc": ("p6d", "seg_soc"),
            "p7_t_tra": ("p7", "t_tra"),
            "p4_p6d": ("p4", "p6d"),
            "p4_p7": ("p4", "p7"),
        }.items():
            codes = tuple(
                all_values[f]
                if state(f, all_values[f], catalogues[f]) == "substantive_code"
                else state(f, all_values[f], catalogues[f])
                for f in fields
            )
            joint[name][codes] += 1
            joint_weights[name][codes] += w
    fields_report = {}
    for field in counts:
        if sum(counts[field].values()) != flow["occupied"]:
            raise ValueError("Field partition mismatch")
        if sum(weights[field].values()) != flow_weights["occupied"]:
            raise ValueError("Weighted field partition mismatch")
        fields_report[field] = {
            "states": dict(counts[field]),
            "weighted_states": dict(weights[field]),
            "observed_code_counts": dict(sorted(distributions[field].items())),
        }
    return {
        "national": national.report(),
        "flow_counts": dict(flow),
        "flow_weighted_totals": dict(flow_weights),
        "fields": fields_report,
        "cross_tabs": {
            name: [
                {"codes": list(codes), "rows": n, "weighted_total": joint_weights[name][codes]}
                for codes, n in sorted(items.items(), key=lambda item: str(item[0]))
            ]
            for name, items in joint.items()
        },
    }


def verify_staging(conn, run, table, year, quarter, expected, source_fingerprint):
    selected = (*BASE, *FIELDS[table]) if table == "SDEM" else FIELDS[table]
    metadata = conn.execute(
        "SELECT header,row_count FROM staging.enoe_table WHERE run_id=%s AND table_name=%s",
        (run, table),
    ).fetchone()
    if not metadata or metadata[1] != expected:
        raise ValueError("Staged table metadata mismatch")
    header = metadata[0]
    validate_header(year, quarter, table, header)
    columns = sql.SQL(",").join(
        sql.SQL("raw_fields[{}]").format(sql.Literal(header.index(f) + 1)) for f in selected
    )
    with conn.cursor(name="enoe_variable_fingerprint") as cursor:
        cursor.execute(
            sql.SQL(
                "SELECT row_number,source_key,{} FROM staging.enoe_row "
                "WHERE run_id=%s AND table_name=%s ORDER BY row_number"
            ).format(columns),
            (run, table),
        )
        actual = fingerprint(
            (number, key, [bytes(v).decode("ascii", errors="strict") for v in values])
            for number, key, *values in cursor
        )
    if actual != source_fingerprint or actual[0] != expected:
        raise ValueError("Selected source/staged fields disagree")


def reference_agreement(result: dict) -> dict:
    """Compare observed cross-tabs with reviewed 2023 reference rules, not a new precode."""
    routing = result["cross_tabs"]["p4_p6d"]
    abroad_blank = all(
        (row["codes"][0] == "4") == (row["codes"][1] == "blank_routing_unresolved")
        for row in routing
    )
    mapping = {
        "p6d_imssissste": {"1": "1", "2": "2", "3": "2", "4": "2", "5": "3", "6": "4"},
        "p6d_seg_soc": {**dict.fromkeys(("1", "2", "3", "4", "5"), "1"), "6": "2"},
    }
    checks = {"abroad_blank_equivalence_observed": abroad_blank}
    for name, codes in mapping.items():
        codes["unspecified"] = "unspecified"
        if abroad_blank:
            codes["blank_routing_unresolved"] = "unspecified"
        rows = result["cross_tabs"][name]
        compared = [row for row in rows if row["codes"][0] in codes]
        mismatched = [row for row in compared if codes[row["codes"][0]] != row["codes"][1]]
        checks[name] = {
            "compared_rows": sum(row["rows"] for row in compared),
            "unresolved_rows": sum(row["rows"] for row in rows)
            - sum(row["rows"] for row in compared),
            "mismatched_rows": sum(row["rows"] for row in mismatched),
            "mismatched_weighted_total": sum(row["weighted_total"] for row in mismatched),
        }
    return checks


def audit(settings: Settings, entry: dict) -> dict:
    year, quarter = entry["year"], entry["quarter"]
    run, path = UUID(entry["run_id"]), Path(entry["archive"])
    pilot = (year, quarter) == (2025, 3)
    reviewed = {} if pilot else release(year, quarter)
    expected_hash = ARCHIVE_SHA256 if pilot else reviewed["archive_sha256"]
    if path.is_symlink() or not path.is_file() or digest(path) != expected_hash:
        raise ValueError("Expected unchanged reviewed archive")
    prepared = preparation_audit(settings, run)
    if prepared["source_sha256"] != expected_hash:
        raise ValueError("Run/archive period mismatch")
    expected = (
        {c.name: c.rows for c in CONTRACTS}
        if pilot
        else {t: c["rows"] for t, c in reviewed["tables"].items()}
    )
    completed = "0" if pilot else reviewed["completed_interview_code"]
    with (
        zipfile.ZipFile(path) as archive,
        psycopg.connect(**settings.connection_parameters()) as conn,
    ):
        if len(archive.namelist()) != len(set(archive.namelist())):
            raise ValueError("Duplicate archive members")
        conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        metadata = conn.execute(
            "SELECT source_sha256,reference_period,layout_version FROM enoe.person_quarter_v1 "
            "WHERE run_id=%s LIMIT 1",
            (run,),
        ).fetchone()
        if not metadata or metadata[:2] != (
            expected_hash,
            date(year, quarter * 3 - 2, 1),
        ):
            raise ValueError("Unsupported reviewed run")
        catalogues, provenance, fingerprints = {}, {}, {}
        for table, fields in FIELDS.items():
            fingerprints[table] = fingerprint(source_records(archive, table, year, quarter))
            verify_staging(conn, run, table, year, quarter, expected[table], fingerprints[table])
            base = members(table, year, quarter)[0].split("/")[0]
            for field in fields:
                member = f"{base}/catalogos/{field}.csv"
                raw = archive.read(member)
                anomaly = (year, quarter, field) == (2025, 2, "c_ocu11c")
                catalogues[field] = parse_catalogue(raw, anomalous=anomaly)
                provenance[field] = {
                    "member": member,
                    "sha256": hashlib.sha256(raw).hexdigest(),
                    "keys": len(catalogues[field]),
                    "known_serialization_anomaly": anomaly,
                }
        result = profile(archive, year, quarter, catalogues, completed)
    if (
        digest(path) != expected_hash
        or result["national"]["weighted_totals"] != prepared["weighted_totals"]
        or result["national"]["counts"] != prepared["counts"]
    ):
        raise ValueError("Source/preparation reconciliation failed")
    return {
        "year": year,
        "quarter": quarter,
        "run_id": str(run),
        "source_sha256": expected_hash,
        "catalogues": provenance,
        "selected_field_fingerprints": {
            t: {"rows": n, "sha256": h} for t, (n, h) in fingerprints.items()
        },
        "source_staging_match": True,
        "reference_rule_agreement": reference_agreement(result),
        **result,
    }


def compare(settings: Settings, entries: list[dict]) -> dict:
    if not entries or len({(e["year"], e["quarter"]) for e in entries}) != len(entries):
        raise ValueError("Select one explicit run per unique quarter")
    reports = [audit(settings, entry) for entry in entries]
    return {
        "version": VERSION,
        "precision_validated": False,
        "platform_identification_validated": False,
        "routing_status": "release_specific_instrument_confirmation_pending",
        "quarters": reports,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    print(
        json.dumps(
            compare(Settings.from_env(), json.loads(args.manifest.read_text())),
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
