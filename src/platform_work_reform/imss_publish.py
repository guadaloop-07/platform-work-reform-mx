"""Reconcile source and staging before selecting an IMSS month."""

import argparse
import json
from decimal import Decimal
from pathlib import Path

import psycopg
from psycopg.types.json import Jsonb

from platform_work_reform.config import Settings
from platform_work_reform.imss_contract import METRICS, rows
from platform_work_reform.imss_staging import digest


def publish(settings: Settings, source: Path, manifest: Path, encoding: str) -> int:
    matches = [x for x in json.loads(manifest.read_text())["files"] if x["name"] == source.name]
    if len(matches) != 1 or source.is_symlink() or not source.is_file():
        raise ValueError("Expected one inventoried regular file")
    item = matches[0]
    if digest(source) != item["sha256"]:
        raise ValueError("Source does not match inventory")
    count = 0
    totals = [Decimal(0)] * len(METRICS)
    missing = [0] * len(METRICS)
    version = None
    for current_version, row in rows(source, encoding):
        version = current_version
        count += 1
        for i, value in enumerate(row[-len(METRICS) :]):
            if value in ("", "NA"):
                missing[i] += 1
            else:
                number = Decimal(value)
                if not number.is_finite():
                    raise ValueError("Non-finite metric")
                totals[i] += number
    if not count or digest(source) != item["sha256"]:
        raise ValueError("Source empty or changed during reconciliation")
    expected = [None if n == count else total for total, n in zip(totals, missing, strict=True)]
    with psycopg.connect(**settings.connection_parameters()) as connection:
        staged = connection.execute(
            """SELECT l.run_id, l.source_file_id, l.layout_version, l.row_count, s.encoding
               FROM staging.imss_load l JOIN meta.source_file s ON s.id=l.source_file_id
               JOIN meta.ingestion_run r ON r.id=l.run_id
               WHERE s.sha256=%s AND s.source_name='imss' AND l.reference_period=%s
               AND r.status='succeeded'""",
            (item["sha256"], item["period"]),
        ).fetchone()
        if not staged or staged[2:] != (version, count, encoding):
            raise ValueError("No matching successful staging load")
        run_id, source_id = staged[:2]
        expressions = []
        for i in range(14, 31):
            expressions.extend(
                [
                    f"sum(NULLIF(NULLIF(raw_fields[{i}], ''), 'NA')::numeric)",
                    f"count(*) FILTER (WHERE raw_fields[{i}] IN ('', 'NA') "
                    f"OR raw_fields[{i}] IS NULL)",
                ]
            )
        query = (
            "SELECT count(*), " + ", ".join(expressions) + " FROM staging.imss_row WHERE run_id=%s"
        )
        actual = connection.execute(query, (run_id,)).fetchone()
        if actual[0] != count or list(actual[1::2]) != expected or list(actual[2::2]) != missing:
            raise ValueError("Source and staging reconciliation failed")
        selected = connection.execute(
            "SELECT run_id FROM imss.selected_month WHERE reference_period=%s", (item["period"],)
        ).fetchone()
        if selected and selected[0] != run_id:
            raise ValueError("Another source version is already selected for this month")
        details = {
            "rows": count,
            "metric_sums": [str(x) if x is not None else None for x in expected],
            "missing_counts": missing,
            "metrics": list(METRICS),
            "sha256": item["sha256"],
        }
        connection.execute(
            """INSERT INTO meta.quality_check(ingestion_run_id, check_name, passed, details)
               VALUES (%s, 'source_reconciliation_v1', true, %s)
               ON CONFLICT (ingestion_run_id, check_name) DO NOTHING""",
            (run_id, Jsonb(details)),
        )
        connection.execute(
            """INSERT INTO meta.dataset_version(dataset_name, reference_period, source_file_id,
               ingestion_run_id, schema_version, transform_version, row_count)
               VALUES ('imss.monthly_cells', %s, %s, %s, %s, 'v1', %s)
               ON CONFLICT DO NOTHING""",
            (item["period"], source_id, run_id, version, count),
        )
        connection.execute(
            "INSERT INTO imss.selected_month(reference_period, run_id) "
            "VALUES (%s,%s) ON CONFLICT DO NOTHING",
            (item["period"], run_id),
        )
        # A concurrent selection for another version must never be silently accepted.
        current = connection.execute(
            "SELECT run_id FROM imss.selected_month WHERE reference_period=%s", (item["period"],)
        ).fetchone()
        if not current or current[0] != run_id:
            raise ValueError("Concurrent conflicting selection")
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--encoding", required=True)
    args = parser.parse_args()
    count = publish(Settings.from_env(), args.source, args.manifest, args.encoding)
    print(f"Reconciled and selected {count} rows.")


if __name__ == "__main__":
    main()
