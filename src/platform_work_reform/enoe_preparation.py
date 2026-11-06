"""Reconcile one explicit reviewed prepared ENOE run; emit aggregates only."""

import argparse
import json
from uuid import UUID

import psycopg

from platform_work_reform.config import Settings
from platform_work_reform.enoe_pilot_indicators import FIELDS, REFERENCE, Audit
from platform_work_reform.enoe_releases import release
from platform_work_reform.enoe_staging import CONTRACTS

VERSION = "enoe-prepared-person-v1"


def audit(settings: Settings, run_id: UUID) -> dict:
    with psycopg.connect(**settings.connection_parameters()) as conn:
        with conn.transaction():
            conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
            conn.execute("SET LOCAL enable_nestloop = off")
            metadata = conn.execute(
                """SELECT DISTINCT reference_period, source_sha256, completed_code
                   FROM enoe.person_quarter_v1 WHERE run_id=%s""",
                (run_id,),
            ).fetchall()
            if len(metadata) != 1:
                raise ValueError("Unsupported or empty reviewed ENOE run")
            period, source_hash, completed_code = metadata[0]
            year, quarter = period.year, (period.month - 1) // 3 + 1
            if (year, quarter) == (2025, 3):
                expected = {c.name: c.rows for c in CONTRACTS}
                reference = REFERENCE
            else:
                reviewed = release(year, quarter)
                expected = {name: c["rows"] for name, c in reviewed["tables"].items()}
                reference = reviewed["reference_totals"]
            result = Audit(completed_code=completed_code)
            with conn.cursor(name="enoe_preparation_audit") as cursor:
                cursor.execute(
                    """SELECT eda,r_def,c_res,fac_tri,clase1,clase2,
                              coe1_row_number IS NOT NULL, coe2_row_number IS NOT NULL,
                              preparation_status, quarterly_weight
                       FROM enoe.prepared_person_v1 WHERE run_id=%s""",
                    (run_id,),
                )
                for row in cursor:
                    values = dict(zip(FIELDS, row[:6], strict=True))
                    if row[8] == "invalid" or any(v is None for v in values.values()):
                        raise ValueError("Invalid prepared person record")
                    before = result.counts["eligible"]
                    result.add(values, row[6], row[7])
                    eligible = result.counts["eligible"] > before
                    if row[8] != ("eligible" if eligible else "outside_universe") or row[9] != (
                        int(values["fac_tri"]) if eligible else None
                    ):
                        raise ValueError(
                            "Prepared universe/weight disagrees with independent audit"
                        )
            output = result.report()
            counts = output["counts"]
            if (
                counts.get("sdem") != expected["SDEM"]
                or counts.get("coe1_matched") != expected["COE1"]
                or counts.get("coe2_matched") != expected["COE2"]
                or output["weighted_totals"] != reference
            ):
                raise ValueError("Prepared counts or national reference mismatch")
            output.update(
                version=VERSION,
                run_id=str(run_id),
                reference_period=str(period),
                source_sha256=source_hash,
                reference_match=True,
                precision_validated=False,
            )
            return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True, type=UUID)
    args = parser.parse_args()
    print(json.dumps(audit(Settings.from_env(), args.run_id), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
