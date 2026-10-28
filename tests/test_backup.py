import json
import subprocess
import uuid

import psycopg
import pytest
from psycopg import sql

from platform_work_reform.backup import BackupError, backup, metadata_audit, restore

pytestmark = pytest.mark.integration


@pytest.fixture
def restore_target(isolated_database):
    name = "platform_work_reform_restore_" + uuid.uuid4().hex
    try:
        yield name
    finally:
        with psycopg.connect(
            **isolated_database.connection_parameters("postgres"), autocommit=True
        ) as admin:
            admin.execute(
                sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(name))
            )


def test_backup_restore_roundtrip_and_existing_target_refusal(
    isolated_database, restore_target, tmp_path
):
    with psycopg.connect(**isolated_database.connection_parameters()) as connection:
        file_id = connection.execute(
            """INSERT INTO meta.source_file(source_name, original_name, sha256, byte_size)
               VALUES ('imss', 'synthetic.csv', %s, 123) RETURNING id""",
            ("c" * 64,),
        ).fetchone()[0]
        run_id = connection.execute(
            """INSERT INTO meta.ingestion_run(source_file_id, status, finished_at)
               VALUES (%s, 'succeeded', now()) RETURNING id""",
            (file_id,),
        ).fetchone()[0]
        connection.execute(
            """INSERT INTO meta.dataset_version(dataset_name, reference_period,
               source_file_id, ingestion_run_id, schema_version, transform_version, row_count)
               VALUES ('imss.cells', '2025-07-31', %s, %s, 'v1', 'test', 2)""",
            (file_id, run_id),
        )
        connection.execute(
            """INSERT INTO meta.quality_check(ingestion_run_id, check_name, passed)
               VALUES (%s, 'synthetic-check', true)""",
            (run_id,),
        )
        expected = metadata_audit(connection)
    archive = backup(isolated_database, tmp_path / "research.dump")
    manifest = json.loads(archive.with_suffix(".dump.json").read_text())
    assert manifest["audit"] == expected
    assert manifest["audit"]["tables"]["source_file"]["rows"] == 1
    assert archive.stat().st_mode & 0o077 == 0
    restore(isolated_database, archive, restore_target)
    with psycopg.connect(**isolated_database.connection_parameters(restore_target)) as connection:
        assert metadata_audit(connection) == expected
        assert connection.execute("SELECT id FROM meta.source_file").fetchone() == (file_id,)
    with pytest.raises(BackupError, match="already exists"):
        restore(isolated_database, archive, restore_target)
    with psycopg.connect(**isolated_database.connection_parameters()) as connection:
        assert metadata_audit(connection) == expected
    with pytest.raises(BackupError, match="already exists"):
        backup(isolated_database, archive)


def test_corrupted_archive_is_rejected_before_creating_target(
    isolated_database, restore_target, tmp_path
):
    archive = backup(isolated_database, tmp_path / "corrupted.dump")
    with archive.open("ab") as stream:
        stream.write(b"corruption")
    with pytest.raises(BackupError, match="checksum"):
        restore(isolated_database, archive, restore_target)
    with psycopg.connect(**isolated_database.connection_parameters("postgres")) as admin:
        assert (
            admin.execute(
                "SELECT 1 FROM pg_database WHERE datname=%s", (restore_target,)
            ).fetchone()
            is None
        )


def test_failed_dump_does_not_publish_files(isolated_database, tmp_path, monkeypatch):
    def fail(*args, **kwargs):
        raise subprocess.CalledProcessError(1, "synthetic-failure")

    monkeypatch.setattr("platform_work_reform.backup.subprocess.run", fail)
    with pytest.raises(subprocess.CalledProcessError):
        backup(isolated_database, tmp_path / "failed.dump")
    assert list(tmp_path.iterdir()) == []


def test_unsafe_and_source_targets_are_rejected(isolated_database, tmp_path):
    for target in (isolated_database.database, "postgres", "other_project", "bad;name"):
        with pytest.raises(BackupError, match="Restore target"):
            restore(isolated_database, tmp_path / "not-needed.dump", target)


def test_concurrent_write_is_not_mixed_into_exported_snapshot(
    isolated_database, restore_target, tmp_path, monkeypatch
):
    real_run = subprocess.run

    def write_then_dump(command, **kwargs):
        if "pg_dump" in command:
            with psycopg.connect(**isolated_database.connection_parameters()) as connection:
                connection.execute(
                    """INSERT INTO meta.source_file(source_name, original_name, sha256, byte_size)
                       VALUES ('imss', 'concurrent.csv', %s, 10)""",
                    ("d" * 64,),
                )
        return real_run(command, **kwargs)

    monkeypatch.setattr("platform_work_reform.backup.subprocess.run", write_then_dump)
    archive = backup(isolated_database, tmp_path / "snapshot.dump")
    restore(isolated_database, archive, restore_target)
    with psycopg.connect(**isolated_database.connection_parameters()) as connection:
        assert connection.execute("SELECT count(*) FROM meta.source_file").fetchone() == (1,)
    with psycopg.connect(**isolated_database.connection_parameters(restore_target)) as connection:
        assert connection.execute("SELECT count(*) FROM meta.source_file").fetchone() == (0,)
