"""Read provisional monthly platform job aggregates from selected IMSS versions."""

import json
from decimal import Decimal

import psycopg

from platform_work_reform.config import Settings

CONTRACT = "user-transcription-2026-11-09-v1"


def summarize(layout: str, groups: list[tuple], total: tuple) -> dict:
    """Reconcile disjoint raw-code groups; never report partial sums as totals."""
    if layout not in {"legacy-v1", "platform-v1"}:
        raise ValueError("Unsupported IMSS layout")
    buckets = {}
    for code, count, value, missing, invalid in groups:
        key = {"1": "platform", "0": "nonplatform"}.get(code, "missing")
        if code not in ("1", "0", None, "", "NA"):
            raise ValueError("Invalid ptpd code")
        if layout == "legacy-v1" and code is not None:
            raise ValueError("Legacy layout unexpectedly contains ptpd")
        if invalid:
            raise ValueError("Invalid affiliated job count")
        bucket = buckets.setdefault(key, [0, Decimal(0), 0])
        bucket[0] += count
        bucket[1] += value if value is not None else Decimal(0)
        bucket[2] += missing
    count, value, missing, invalid = total
    if (
        invalid
        or count <= 0
        or sum(x[0] for x in buckets.values()) != count
        or sum(x[1] for x in buckets.values()) != (value if value is not None else 0)
        or sum(x[2] for x in buckets.values()) != missing
    ):
        raise ValueError("Monthly reconciliation failed")
    result = {}
    for key in ("platform", "nonplatform", "missing"):
        n, subtotal, absent = buckets.get(key, [0, Decimal(0), 0])
        available = layout == "platform-v1" or key == "missing"
        result[key] = {
            "rows": n,
            "ta_missing_rows": absent,
            "ta": str(subtotal) if available and not absent else None,
        }
    return {
        "classification_status": "unavailable" if layout == "legacy-v1" else "provisional",
        "rows": count,
        "ta_missing_rows": missing,
        "total_ta": str(value) if not missing else None,
        "categories": result,
        "reconciled": True,
    }


def series(settings: Settings) -> dict:
    with psycopg.connect(**settings.connection_parameters()) as connection:
        connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        metadata = connection.execute("""
            SELECT s.reference_period, s.run_id, l.source_file_id, l.layout_version,
                   f.sha256, f.original_name, l.row_count,
                   r.status='succeeded' AND EXISTS (
                     SELECT 1 FROM meta.quality_check q WHERE q.ingestion_run_id=s.run_id
                     AND q.check_name='source_reconciliation_v1' AND q.passed)
            FROM imss.selected_month s JOIN staging.imss_load l USING (run_id)
            JOIN meta.source_file f ON f.id=l.source_file_id
            JOIN meta.ingestion_run r ON r.id=s.run_id
            ORDER BY s.reference_period
        """).fetchall()
        if not metadata or any(not row[7] for row in metadata):
            raise ValueError("Expected reconciled successful selected months")
        grouped = connection.execute("""
            SELECT reference_period, grouping(ptpd), ptpd, count(*), sum(ta),
                   count(*) FILTER (WHERE ta IS NULL),
                   count(*) FILTER (WHERE ta < 0 OR ta <> trunc(ta)
                     OR ta::text IN ('NaN', 'Infinity', '-Infinity'))
            FROM imss.monthly_cells
            GROUP BY GROUPING SETS ((reference_period, ptpd), (reference_period))
        """).fetchall()
    by_month = {}
    totals = {}
    for period, is_total, code, *values in grouped:
        if is_total:
            totals[period] = tuple(values)
        else:
            by_month.setdefault(period, []).append((code, *values))
    months = []
    for period, run, source, layout, sha256, name, row_count, _ in metadata:
        if period not in totals or totals[period][0] != row_count:
            raise ValueError("Selected month row count mismatch")
        months.append(
            {
                "reference_period": str(period),
                "run_id": str(run),
                "source_file_id": str(source),
                "source_sha256": sha256,
                "source_name": name,
                "layout_version": layout,
                **summarize(layout, by_month.get(period, []), totals[period]),
            }
        )
    return {
        "contract": CONTRACT,
        "source_status": "user_supplied_transcription_official_verification_pending",
        "unit": "affiliated_jobs",
        "measure": "ta",
        "platform_filter": "ptpd = 1",
        "months": months,
    }


def main() -> None:
    print(json.dumps(series(Settings.from_env()), indent=2))


if __name__ == "__main__":
    main()
