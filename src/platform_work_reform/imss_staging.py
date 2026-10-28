"""Load one inventoried IMSS file transactionally into raw staging."""

import argparse
import hashlib
import json
from datetime import date
from pathlib import Path

import psycopg

from platform_work_reform.config import Settings
from platform_work_reform.imss_contract import rows


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def load(settings: Settings, source: Path, manifest: Path, encoding: str) -> int:
    inventory = json.loads(manifest.read_text(encoding="utf-8"))
    matches = [item for item in inventory["files"] if item["name"] == source.name]
    if len(matches) != 1 or source.is_symlink() or not source.is_file():
        raise ValueError("Expected one inventoried regular file")
    item = matches[0]
    period = date.fromisoformat(item["period"])
    if source.stat().st_size != item["size_bytes"] or digest(source) != item["sha256"]:
        raise ValueError("Source does not match inventory")
    if encoding not in ("utf-8-sig", "utf-8", "cp1252", "iso-8859-1"):
        raise ValueError("Unsupported source encoding")
    with psycopg.connect(**settings.connection_parameters()) as connection:
        source_id = connection.execute(
            """INSERT INTO meta.source_file(source_name, original_name, sha256, byte_size, encoding)
               VALUES ('imss', %s, %s, %s, %s)
               ON CONFLICT (source_name, sha256) DO UPDATE SET sha256=EXCLUDED.sha256
               RETURNING id""",
            (source.name, item["sha256"], item["size_bytes"], encoding),
        ).fetchone()[0]
        previous = connection.execute(
            "SELECT row_count FROM staging.imss_load "
            "WHERE source_file_id=%s AND reference_period=%s",
            (source_id, period),
        ).fetchone()
        if previous:
            return previous[0]
        run = connection.execute(
            """INSERT INTO meta.ingestion_run(source_file_id, status, started_at)
               VALUES (%s, 'running', now()) RETURNING id""",
            (source_id,),
        ).fetchone()[0]
        connection.commit()
        try:
            count = 0
            version = None
            with connection.cursor().copy(
                "COPY staging.imss_row (run_id, row_number, raw_fields) FROM STDIN"
            ) as copy:
                for version, fields in rows(source, encoding):
                    count += 1
                    if version == "legacy-v1":
                        fields.insert(4, None)
                    copy.write_row((run, count, fields))
            if not count:
                raise ValueError("Source contains no data rows")
            if digest(source) != item["sha256"]:
                raise ValueError("Source changed during loading")
            connection.execute(
                """INSERT INTO staging.imss_load
                   (run_id, source_file_id, reference_period, layout_version, row_count)
                   VALUES (%s, %s, %s, %s, %s)""",
                (run, source_id, period, version, count),
            )
            connection.execute(
                "UPDATE meta.ingestion_run SET status='succeeded', finished_at=now() WHERE id=%s",
                (run,),
            )
            connection.commit()
            return count
        except Exception:
            connection.rollback()
            connection.execute(
                """UPDATE meta.ingestion_run SET status='failed', finished_at=now(),
                   error_summary='Staging load failed; inspect local diagnostics' WHERE id=%s""",
                (run,),
            )
            connection.commit()
            raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--encoding", required=True)
    args = parser.parse_args()
    count = load(Settings.from_env(), args.source, args.manifest, args.encoding)
    print(f"Staged {count} rows from {args.source.name}.")


if __name__ == "__main__":
    main()
