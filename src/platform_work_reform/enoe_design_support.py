"""Audit observed design support; do not estimate variance or reconstruct a frame."""

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from uuid import UUID

import psycopg

from platform_work_reform.config import Settings
from platform_work_reform.enoe_contract import validate_header
from platform_work_reform.enoe_pilot_indicators import Audit, ascii_value
from platform_work_reform.enoe_staging import ARCHIVE_SHA256

VERSION = "enoe-observed-design-support-2025q3-v2"
FIELDS = ("cve_ent", "est_d_tri", "upm", "eda", "r_def", "c_res", "fac_tri", "clase1", "clase2")
GROUPS = ("all_observed", "completed_residents", "population_15_plus", "pea")


def valid_code(value: str) -> bool:
    return value.isascii() and value.isdigit() and int(value) > 0


@dataclass
class DesignSupport:
    """Retain raw design codes and compare domain membership to parent support."""

    counts: Counter = field(default_factory=Counter)
    missing: Counter = field(default_factory=Counter)
    clusters: dict = field(default_factory=lambda: {name: defaultdict(set) for name in GROUPS})
    point_audit: Audit = field(default_factory=Audit)
    fields_digest: object = field(default_factory=hashlib.sha256, repr=False)

    def add(self, values: dict[str, str]) -> None:
        # Reuse the pilot's reviewed eligibility and activity-code validation.
        previous = self.point_audit.counts["eligible"]
        self.point_audit.add(values, True, True)
        eligible = self.point_audit.counts["eligible"] > previous
        completed = values["r_def"] == self.point_audit.completed_code and values["c_res"] in {
            "1",
            "3",
        }
        membership = {
            "all_observed": True,
            "completed_residents": completed,
            "population_15_plus": eligible,
            "pea": eligible and values["clase1"] == "1",
        }
        bad_keys = [
            name for name in ("cve_ent", "est_d_tri", "upm") if not valid_code(values[name])
        ]
        if completed and bad_keys:
            raise ValueError("Missing or invalid design key among completed residents")
        self.fields_digest.update(
            (json.dumps([values[name] for name in FIELDS], ensure_ascii=False) + "\n").encode(
                "ascii"
            )
        )
        for group, included in membership.items():
            if not included:
                continue
            self.counts[group] += 1
            if bad_keys:
                self.missing[group] += 1
                continue
            # Entity is part of the stratum key; UPMs are nested within strata.
            key = (values["cve_ent"], values["est_d_tri"])
            self.clusters[group][key].add(values["upm"])

    def report(self) -> dict:
        parent = self.clusters["completed_residents"]
        groups = {}
        for group in GROUPS:
            strata = self.clusters[group]
            sizes = Counter(len(upms) for upms in strata.values())
            result = {
                "records": self.counts[group],
                "records_with_invalid_design_keys": self.missing[group],
                "observed_strata": len(strata),
                "observed_nested_upms": sum(len(upms) for upms in strata.values()),
                "singleton_strata": sizes[1],
                "upms_per_stratum_histogram": dict(sorted(sizes.items())),
            }
            if group in {"population_15_plus", "pea"}:
                # Keep parent strata/UPMs even when a domain contributes zero rows.
                domain_sizes = Counter(len(strata.get(key, set())) for key in parent)
                result["domain_support_in_completed_resident_strata"] = {
                    "zero_domain_upms": domain_sizes[0],
                    "one_domain_upm": domain_sizes[1],
                    "two_or_more_domain_upms": sum(n for k, n in domain_sizes.items() if k >= 2),
                    "parent_upms_without_domain_records": sum(
                        len(upms - strata.get(key, set())) for key, upms in parent.items()
                    ),
                }
            groups[group] = result
        return {
            "version": VERSION,
            "groups": groups,
            "weighted_totals": dict(self.point_audit.weights),
            "ordered_fields_sha256": self.fields_digest.hexdigest(),
            "variance_ready": False,
            "limitations": [
                "Observed SDEM support is not the full sampling frame.",
                "Completed residents are a diagnostic parent, not an approved variance frame.",
                "No singleton policy, variance, degrees of freedom "
                "or confidence interval is selected.",
            ],
        }


def audit(settings: Settings, run_id: UUID, *, year: int = 2025, quarter: int = 3) -> dict:
    source_hash, entity_field = ARCHIVE_SHA256, "cve_ent"
    if (year, quarter) != (2025, 3):
        from platform_work_reform.enoe_releases import release

        reviewed = release(year, quarter)
        source_hash, entity_field = reviewed["archive_sha256"], reviewed["entity_field"]
    expected_period = f"{year}-{3 * quarter - 2:02d}-01"
    expected_layout = f"enoe-{year}q{quarter}-v1"
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
                or metadata[0] != source_hash
                or str(metadata[1]) != expected_period
                or metadata[2:4] != (expected_layout, "succeeded")
            ):
                raise ValueError("Unsupported ENOE load")
            header = metadata[4]
            validate_header(year, quarter, "SDEM", header)
            positions = {
                name: header.index(entity_field if name == "cve_ent" else name) for name in FIELDS
            }
            result = DesignSupport()
            if (year, quarter) != (2025, 3):
                result.point_audit.completed_code = reviewed["completed_interview_code"]
            with conn.cursor(name="enoe_design_support") as cursor:
                cursor.execute(
                    """SELECT raw_fields FROM staging.enoe_row
                       WHERE run_id=%s AND table_name='SDEM' ORDER BY row_number""",
                    (run_id,),
                )
                for (raw,) in cursor:
                    result.add({name: ascii_value(raw[pos]) for name, pos in positions.items()})
            output = result.report()
            if (year, quarter) != (2025, 3):
                output["version"] = f"enoe-observed-design-support-{year}q{quarter}-v1"
            output.update({"run_id": str(run_id), "source_sha256": metadata[0]})
            if not result.counts["all_observed"]:
                raise ValueError("Empty ENOE load")
            return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True, type=UUID)
    args = parser.parse_args()
    print(json.dumps(audit(Settings.from_env(), args.run_id), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
