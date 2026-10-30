"""Reconcile reviewed ENOE 2025 Q3 national point estimates, without publishing microdata."""

import argparse
import json
from collections import Counter
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

import psycopg

from platform_work_reform.config import Settings
from platform_work_reform.enoe_contract import validate_header
from platform_work_reform.enoe_staging import ARCHIVE_SHA256

VERSION = "enoe-national-pilot-v1"
FIELDS = ("eda", "r_def", "c_res", "fac_tri", "clase1", "clase2")
REFERENCE = {"population": 103068355, "pea": 61303255, "occupied": 59533449, "unemployed": 1769806}


def ascii_value(value: bytes) -> str:
    return bytes(value).decode("ascii", errors="strict").strip()


@dataclass
class Audit:
    counts: Counter = field(default_factory=Counter)
    weights: Counter = field(default_factory=Counter)
    missing_coe: Counter = field(default_factory=Counter)

    def add(self, values: dict[str, str], coe1: bool, coe2: bool) -> None:
        age_text, result, residence = (values[x] for x in ("eda", "r_def", "c_res"))
        if age_text and (not age_text.isascii() or not age_text.isdigit()):
            raise ValueError("Invalid age code")
        age = int(age_text) if age_text else None
        if age is not None and not 0 <= age <= 99:
            raise ValueError("Invalid age code")
        if result == "0" and residence in ("1", "3") and age is None:
            raise ValueError("Missing age for completed resident interview")
        eligible = result == "0" and residence in ("1", "3") and age is not None and 15 <= age <= 98
        self.counts["sdem"] += 1
        self.counts["coe1_matched"] += coe1
        self.counts["coe2_matched"] += coe2
        if not coe1 or not coe2:
            group = (
                "under_12" if age == 99 or (age is not None and age < 12) else "other_or_missing"
            )
            self.missing_coe[
                f"{group}|r_def={result}|c_res={residence}|coe1={int(coe1)}|coe2={int(coe2)}"
            ] += 1
        if not eligible:
            self.counts["outside_universe"] += 1
            return
        self.counts["eligible"] += 1
        weight, c1, c2 = (values[x] for x in ("fac_tri", "clase1", "clase2"))
        if not weight.isascii() or not weight.isdigit() or int(weight) <= 0:
            raise ValueError("Missing or invalid quarterly weight in universe")
        if (c1, c2) not in {("1", "1"), ("1", "2"), ("2", "3"), ("2", "4")}:
            raise ValueError("Invalid or inconsistent activity codes in universe")
        w = int(weight)
        self.weights["population"] += w
        if c1 == "1":
            self.weights["pea"] += w
        if c2 == "1":
            self.weights["occupied"] += w
        if c2 == "2":
            self.weights["unemployed"] += w

    def report(self) -> dict:
        if not self.weights["population"] or not self.weights["pea"]:
            raise ValueError("Empty denominator")

        def rate(n: int, d: int) -> str:
            return str((Decimal(100) * n / d).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))

        return {
            "counts": dict(self.counts),
            "questionnaire_missing_categories": dict(sorted(self.missing_coe.items())),
            "weighted_totals": {k: self.weights[k] for k in REFERENCE},
            "participation_percent_rounded": rate(self.weights["pea"], self.weights["population"]),
            "unemployment_percent_rounded": rate(self.weights["unemployed"], self.weights["pea"]),
        }


def audit(settings: Settings, run_id: UUID) -> dict:
    with psycopg.connect(**settings.connection_parameters()) as conn:
        with conn.transaction():
            conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
            metadata = conn.execute(
                """SELECT f.sha256, l.reference_period, l.layout_version, r.status, t.header
                   FROM staging.enoe_load l JOIN meta.source_file f ON f.id=l.source_file_id
                   JOIN meta.ingestion_run r ON r.id=l.run_id
                   JOIN staging.enoe_table t ON t.run_id=l.run_id AND t.table_name='SDEM'
                   WHERE l.run_id=%s""",
                (run_id,),
            ).fetchone()
            if (
                not metadata
                or metadata[0] != ARCHIVE_SHA256
                or str(metadata[1]) != "2025-07-01"
                or metadata[2:4] != ("enoe-2025q3-v1", "succeeded")
            ):
                raise ValueError("Unsupported ENOE load")
            header = metadata[4]
            validate_header(2025, 3, "SDEM", header)
            positions = {name: header.index(name) for name in FIELDS}
            result = Audit()
            with conn.cursor(name="enoe_pilot_audit") as cursor:
                cursor.execute(
                    """SELECT sdem_raw_fields, coe1_row_number IS NOT NULL,
                              coe2_row_number IS NOT NULL
                       FROM enoe.person_quarter_pilot WHERE run_id=%s""",
                    (run_id,),
                )
                for raw, coe1, coe2 in cursor:
                    result.add(
                        {name: ascii_value(raw[pos]) for name, pos in positions.items()}, coe1, coe2
                    )
            output = result.report()
            output.update({"run_id": str(run_id), "source_sha256": metadata[0], "version": VERSION})
            output["reference_match"] = (
                output["weighted_totals"] == REFERENCE
                and output["counts"].get("sdem") == 422306
                and output["counts"].get("coe1_matched") == 346524
                and output["counts"].get("coe2_matched") == 346524
                and output["counts"].get("eligible") == 325108
                and output["participation_percent_rounded"] == "59.5"
                and output["unemployment_percent_rounded"] == "2.9"
            )
            return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", type=UUID, required=True)
    args = parser.parse_args()
    result = audit(Settings.from_env(), args.run_id)
    print(json.dumps(result, indent=2, sort_keys=True))
    if not result["reference_match"]:
        raise SystemExit("Official national reference does not match")


if __name__ == "__main__":
    main()
