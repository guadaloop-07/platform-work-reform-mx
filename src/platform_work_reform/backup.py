"""Consistent custom-format backups and verified restores into new databases."""

import argparse
import hashlib
import json
import os
import re
import subprocess
import tempfile
import uuid
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import psycopg
from psycopg import sql

from platform_work_reform.config import Settings

AUDIT_TABLES = ("source_file", "ingestion_run", "dataset_version", "quality_check")


class BackupError(RuntimeError):
    """An actionable failure safe to display without connection secrets."""


def tools_prefix() -> list[str]:
    # CI's service is not managed by Compose; use its explicit container ID.
    container = os.environ.get("PWR_POSTGRES_CONTAINER")
    if container:
        return ["docker", "exec", "-i", container]
    return ["docker", "compose", "exec", "-T", "postgres"]


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def metadata_audit(connection) -> dict:
    connection.execute("SET LOCAL TIME ZONE 'UTC'")
    revision = connection.execute("SELECT version_num FROM meta.alembic_version").fetchone()[0]
    tables = {}
    for table in AUDIT_TABLES:
        checksum = hashlib.sha256()
        count = 0
        query = sql.SQL("SELECT to_jsonb(t)::text FROM meta.{} AS t ORDER BY id").format(
            sql.Identifier(table)
        )
        with connection.cursor(name="audit_" + table) as cursor:
            for (value,) in cursor.execute(query):
                checksum.update(value.encode("utf-8") + b"\n")
                count += 1
        tables[table] = {"rows": count, "sha256": checksum.hexdigest()}
    return {"revision": revision, "tables": tables}


def backup(settings: Settings, output: Path) -> Path:
    output = Path(output)
    manifest_path = output.with_suffix(output.suffix + ".json")
    if output.exists() or manifest_path.exists():
        raise BackupError("Backup output already exists; choose a new filename")
    output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary: list[Path] = []
    published: list[Path] = []
    try:
        descriptor, name = tempfile.mkstemp(prefix=".backup-partial-", dir=output.parent)
        archive_temp = Path(name)
        temporary.append(archive_temp)
        with os.fdopen(descriptor, "wb") as stream:
            with psycopg.connect(**settings.connection_parameters()) as connection:
                connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
                snapshot = connection.execute("SELECT pg_export_snapshot()").fetchone()[0]
                audit = metadata_audit(connection)
                command = tools_prefix() + [
                    "pg_dump",
                    "--format=custom",
                    "--no-owner",
                    "--no-acl",
                    "--username",
                    settings.user,
                    "--dbname",
                    settings.database,
                    "--snapshot",
                    snapshot,
                ]
                subprocess.run(command, stdout=stream, stderr=subprocess.PIPE, check=True)
            stream.flush()
            os.fsync(stream.fileno())
        manifest = {
            "format_version": 1,
            "source_database": settings.database,
            "created_at": datetime.now(UTC).isoformat(),
            "sha256": digest(archive_temp),
            "audit": audit,
        }
        descriptor, name = tempfile.mkstemp(prefix=".manifest-partial-", dir=output.parent)
        manifest_temp = Path(name)
        temporary.append(manifest_temp)
        with os.fdopen(descriptor, "w") as stream:
            json.dump(manifest, stream, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        # Hard links publish exclusively on the same filesystem, never overwrite.
        os.link(archive_temp, output)
        published.append(output)
        os.link(manifest_temp, manifest_path)
        published.append(manifest_path)
    except BaseException:
        for path in reversed(published):
            path.unlink(missing_ok=True)
        raise
    finally:
        for path in temporary:
            path.unlink(missing_ok=True)
    return output


def restore(settings: Settings, archive: Path, target: str) -> None:
    archive = Path(archive)
    if not re.fullmatch(r"platform_work_reform_restore_[a-z0-9_]+", target) or len(target) > 63:
        raise BackupError("Restore target must be a new platform_work_reform_restore_* database")
    if target == settings.database:
        raise BackupError("Cannot restore over the configured source database")
    manifest_path = archive.with_suffix(archive.suffix + ".json")
    try:
        manifest = json.loads(manifest_path.read_text())
        valid = (
            manifest["format_version"] == 1
            and isinstance(manifest["source_database"], str)
            and set(manifest["audit"]["tables"]) == set(AUDIT_TABLES)
            and re.fullmatch(r"[a-f0-9]{64}", manifest["sha256"])
        )
    except (KeyError, TypeError, ValueError, OSError) as exc:
        raise BackupError("Backup manifest is missing or invalid") from exc
    if not valid:
        raise BackupError("Backup manifest is invalid")
    if target == manifest["source_database"]:
        raise BackupError("Cannot restore over the backup's source database")
    if digest(archive) != manifest["sha256"]:
        raise BackupError("Backup checksum does not match its manifest")
    # CREATE DATABASE itself rejects existing names, including concurrent creation.
    try:
        with psycopg.connect(
            **settings.connection_parameters("postgres"), autocommit=True
        ) as admin:
            admin.execute(
                sql.SQL("CREATE DATABASE {} TEMPLATE template0 ENCODING 'UTF8'").format(
                    sql.Identifier(target)
                )
            )
    except psycopg.errors.DuplicateDatabase as exc:
        raise BackupError("Restore target already exists; it has not been changed") from exc
    command = tools_prefix() + [
        "pg_restore",
        "--exit-on-error",
        "--single-transaction",
        "--no-owner",
        "--no-acl",
        "--username",
        settings.user,
        "--dbname",
        target,
    ]
    with archive.open("rb") as stream:
        subprocess.run(
            command, stdin=stream, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True
        )
    with psycopg.connect(
        **replace(settings, database=target).connection_parameters()
    ) as connection:
        if metadata_audit(connection) != manifest["audit"]:
            raise BackupError("Restored metadata does not match the backup manifest")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    save = commands.add_parser("backup")
    save.add_argument("--output", type=Path)
    recover = commands.add_parser("restore")
    recover.add_argument("--archive", type=Path, required=True)
    recover.add_argument("--target", required=True)
    args = parser.parse_args()
    try:
        settings = Settings.from_env()
        if args.command == "backup":
            output = args.output or Path("backups") / (
                datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8] + ".dump"
            )
            print(f"Backup and manifest created: {backup(settings, output)}")
        else:
            restore(settings, args.archive, args.target)
            print(f"Restored and verified: {args.target}")
    except (BackupError, ValueError) as exc:
        parser.exit(1, f"{exc}\n")
    except (psycopg.Error, subprocess.SubprocessError, OSError):
        parser.exit(1, "Database backup/restore failed; inspect service and file availability.\n")


if __name__ == "__main__":
    main()
