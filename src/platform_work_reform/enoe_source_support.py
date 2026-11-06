"""Verify observed design support against the unchanged reviewed ENOE archive."""

import argparse
import csv
import io
import json
import zipfile
from collections import defaultdict
from pathlib import Path
from uuid import UUID

from platform_work_reform.config import Settings
from platform_work_reform.enoe_contract import validate_header
from platform_work_reform.enoe_design_support import FIELDS, DesignSupport, audit, valid_code
from platform_work_reform.enoe_staging import (
    ARCHIVE_SHA256,
    CONTRACTS,
    TableContract,
    digest,
    member_digest,
    members,
)


def summarize(support: dict, records: int) -> dict:
    return {
        "records": records,
        "observed_strata": len(support),
        "observed_nested_upms": sum(len(upms) for upms in support.values()),
        "singleton_strata": sum(len(upms) == 1 for upms in support.values()),
    }


def verify_source(path: Path, *, year: int = 2025, quarter: int = 3) -> dict:
    source_hash, contracts, entity_field = ARCHIVE_SHA256, CONTRACTS, "cve_ent"
    if (year, quarter) != (2025, 3):
        from platform_work_reform.enoe_releases import release

        reviewed = release(year, quarter)
        source_hash, entity_field = reviewed["archive_sha256"], reviewed["entity_field"]
        contracts = tuple(
            TableContract(
                name,
                tuple(values["key"]),
                values["rows"],
                values["member_sha256"],
                values["dictionary_sha256"],
            )
            for name, values in reviewed["tables"].items()
        )
    if digest(path) != source_hash:
        raise ValueError("Unsupported ENOE archive hash")
    supports, summaries = {}, {}
    result = DesignSupport()
    if (year, quarter) != (2025, 3):
        result.point_audit.completed_code = reviewed["completed_interview_code"]
    with zipfile.ZipFile(path) as archive:
        if len(archive.namelist()) != len(set(archive.namelist())):
            raise ValueError("Duplicate archive member")
        for contract in contracts:
            if contract.name not in {"VIV", "HOG", "SDEM"}:
                continue
            member, _ = members(contract.name, year, quarter)
            if member_digest(archive, member) != contract.member_sha256:
                raise ValueError("Source member hash mismatch")
            support = defaultdict(set)
            records = 0
            # Latin-1 is reversible byte mapping; selected fields must be ASCII.
            with archive.open(member) as stream:
                reader = csv.reader(io.TextIOWrapper(stream, encoding="latin-1"), strict=True)
                header = next(reader)
                validate_header(year, quarter, contract.name, header)
                for row in reader:
                    if len(row) != len(header):
                        raise ValueError("Malformed source row")
                    values = dict(zip(header, row, strict=True))
                    codes = [values[name].strip() for name in (entity_field, "est_d_tri", "upm")]
                    if not all(valid_code(code) for code in codes):
                        raise ValueError("Invalid source design key")
                    support[tuple(codes[:2])].add(codes[2])
                    if contract.name == "SDEM":
                        result.add(
                            {
                                name: values[entity_field if name == "cve_ent" else name].strip()
                                for name in FIELDS
                            }
                        )
                    records += 1
            if records != contract.rows:
                raise ValueError("Source row count mismatch")
            supports[contract.name] = support
            summaries[contract.name] = summarize(support, records)
    if set(supports) != {"VIV", "HOG", "SDEM"}:
        raise ValueError("Incomplete source contracts")
    sdem = supports["SDEM"]
    singletons = {key for key, upms in sdem.items() if len(upms) == 1}
    comparisons = {}
    for name in ("VIV", "HOG"):
        parent = supports[name]
        if any(not upms <= parent.get(key, set()) for key, upms in sdem.items()):
            raise ValueError("SDEM design support absent from parent table")
        comparisons[name] = {
            "parent_upms_without_sdem": sum(
                len(upms - sdem.get(key, set())) for key, upms in parent.items()
            ),
            "parent_strata_without_sdem": len(parent.keys() - sdem.keys()),
            "sdem_singletons_with_multiple_parent_upms": sum(
                len(parent[key]) > 1 for key in singletons
            ),
        }
    if digest(path) != source_hash:
        raise ValueError("Source archive changed during audit")
    if (year, quarter) != (2025, 3):
        if dict(result.point_audit.weights) != reviewed["reference_totals"]:
            raise ValueError("National point estimates do not match the official reference")
    sdem_audit = result.report()
    if (year, quarter) != (2025, 3):
        sdem_audit["version"] = f"enoe-observed-design-support-{year}q{quarter}-v1"
    return {
        "year": year,
        "quarter": quarter,
        "entity_field": entity_field,
        "version": f"enoe-source-design-support-{year}q{quarter}-v1",
        "source_sha256": source_hash,
        "source_tables": summaries,
        "parent_comparisons": comparisons,
        "sdem_audit": sdem_audit,
        "variance_ready": False,
    }


def verify(
    settings: Settings, run_id: UUID, path: Path, *, year: int = 2025, quarter: int = 3
) -> dict:
    if (year, quarter) == (2025, 3):
        output, staged = verify_source(path), audit(settings, run_id)
    else:
        output = verify_source(path, year=year, quarter=quarter)
        staged = audit(settings, run_id, year=year, quarter=quarter)
    source = output["sdem_audit"]
    for key in ("groups", "weighted_totals", "ordered_fields_sha256"):
        if source[key] != staged[key]:
            raise ValueError("Source/staged design audit mismatch")
    output.update({"run_id": str(run_id), "source_staged_design_match": True})
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--run-id", type=UUID)
    parser.add_argument("--year", type=int, default=2025)
    parser.add_argument("--quarter", type=int, default=3)
    args = parser.parse_args()
    output = (
        verify(Settings.from_env(), args.run_id, args.archive, year=args.year, quarter=args.quarter)
        if args.run_id
        else verify_source(args.archive, year=args.year, quarter=args.quarter)
    )
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
