"""Compare explicit reviewed ENOE runs without estimating survey precision."""

import argparse
import csv
import io
import json
import zipfile
from itertools import combinations
from pathlib import Path
from uuid import UUID

import psycopg

from platform_work_reform.config import Settings
from platform_work_reform.enoe_contract import RELATIONSHIPS, key_fields
from platform_work_reform.enoe_releases import release
from platform_work_reform.enoe_source_support import verify
from platform_work_reform.enoe_staging import CONTRACTS, members


def singleton_codes(path: Path, year: int, quarter: int) -> set:
    """Internal code comparison only; no individual or stratum IDs are emitted."""
    entity = "cve_ent" if (year, quarter) == (2025, 3) else release(year, quarter)["entity_field"]
    groups = {}
    with zipfile.ZipFile(path) as archive:
        with archive.open(members("SDEM", year, quarter)[0]) as raw:
            for row in csv.DictReader(io.TextIOWrapper(raw, encoding="latin-1", newline="")):
                key = (row[entity].strip(), row["est_d_tri"].strip())
                groups.setdefault(key, set()).add(row["upm"].strip())
    return {key for key, upms in groups.items() if len(upms) == 1}


def reconcile_staged(settings: Settings, run_id: UUID, year: int, quarter: int) -> dict:
    expected = (
        {c.name: c.rows for c in CONTRACTS}
        if (year, quarter) == (2025, 3)
        else {name: c["rows"] for name, c in release(year, quarter)["tables"].items()}
    )
    with psycopg.connect(**settings.connection_parameters()) as conn:
        with conn.transaction():
            conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
            conn.execute("SET LOCAL enable_nestloop = off")
            actual = dict(
                conn.execute(
                    "SELECT table_name,count(*) FROM staging.enoe_row "
                    "WHERE run_id=%s GROUP BY table_name",
                    (run_id,),
                ).fetchall()
            )
            if actual != expected:
                raise ValueError("Staged row counts differ from the reviewed release")
            joins = {}
            for parent, child in sorted(RELATIONSHIPS):
                width = len(key_fields(year, quarter, parent))
                missing, covered = conn.execute(
                    """SELECT count(*) FILTER (WHERE p.row_number IS NULL),
                              count(DISTINCT p.source_key)
                       FROM staging.enoe_row c LEFT JOIN staging.enoe_row p
                         ON p.run_id=c.run_id AND p.table_name=%s
                        AND p.source_key=c.source_key[1:%s]
                       WHERE c.run_id=%s AND c.table_name=%s""",
                    (parent, width, run_id, child),
                ).fetchone()
                if missing:
                    raise ValueError("Staged child-to-parent mismatch")
                joins[f"{parent}->{child}"] = {
                    "matched_children": actual[child],
                    "unmatched_children": missing,
                    "parents_without_children": actual[parent] - covered,
                }
    return {"table_counts": actual, "joins": joins}


def compare(settings: Settings, entries: list[dict]) -> dict:
    if not entries:
        raise ValueError("Specify at least one explicit quarter and run")
    seen, reports, singletons = set(), [], {}
    for entry in entries:
        year, quarter, run_id = entry["year"], entry["quarter"], UUID(entry["run_id"])
        label = f"{year}q{quarter}"
        if label in seen:
            raise ValueError("Duplicate quarter: select one explicit release/run per period")
        seen.add(label)
        path = Path(entry["archive"])
        result = verify(settings, run_id, path, year=year, quarter=quarter)
        result["staging_reconciliation"] = reconcile_staged(settings, run_id, year, quarter)
        # Every archive/run has passed source verification before comparing code sets.
        singletons[label] = singleton_codes(path, year, quarter)
        if (year, quarter) != (2025, 3):
            result["reference_totals_match"] = (
                result["sdem_audit"]["weighted_totals"]
                == release(year, quarter)["reference_totals"]
            )
        else:
            from platform_work_reform.enoe_pilot_indicators import REFERENCE

            result["reference_totals_match"] = result["sdem_audit"]["weighted_totals"] == REFERENCE
        if not result["reference_totals_match"]:
            raise ValueError("National point-estimate reference mismatch")
        reports.append(result)
    overlaps = [
        {
            "quarters": [left, right],
            "shared_singleton_stratum_codes": len(singletons[left] & singletons[right]),
        }
        for left, right in combinations(sorted(singletons), 2)
    ]
    return {
        "version": "enoe-quarter-design-matrix-v1",
        "quarters": reports,
        "singleton_code_overlaps": overlaps,
        "precision_validated": False,
        "limitations": [
            "Shared entity/stratum codes do not establish unchanged design populations.",
            "This does not identify panel persons or justify a singleton variance policy.",
            "2026 Q2 overlaps IMSS ptpd only in May-June in the selected local releases.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "manifest", type=Path, help="Private JSON list with year, quarter, archive, run_id"
    )
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
