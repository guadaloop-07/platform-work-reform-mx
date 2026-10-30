import psycopg
import pytest

from platform_work_reform.migrate import upgrade

pytestmark = pytest.mark.integration


def register_file(connection, digest="a" * 64):
    return connection.execute(
        """INSERT INTO meta.source_file(source_name, original_name, sha256, byte_size)
           VALUES ('imss', 'synthetic.csv', %s, 10) RETURNING id""",
        (digest,),
    ).fetchone()[0]


def test_empty_database_migrates_and_upgrade_is_repeatable(isolated_database):
    upgrade(isolated_database)
    with psycopg.connect(**isolated_database.connection_parameters()) as connection:
        assert connection.execute("SELECT version_num FROM meta.alembic_version").fetchone() == (
            "0005",
        )
        assert connection.execute("SHOW server_encoding").fetchone() == ("UTF8",)
        names = {
            row[0]
            for row in connection.execute(
                "SELECT schema_name FROM information_schema.schemata"
            ).fetchall()
        }
        assert {"meta", "staging", "imss", "enoe", "reference", "analysis"} <= names


def test_file_identity_and_invalid_digest_are_enforced(isolated_database):
    with psycopg.connect(**isolated_database.connection_parameters()) as connection:
        register_file(connection)
        with pytest.raises(psycopg.errors.UniqueViolation), connection.transaction():
            register_file(connection)
        with pytest.raises(psycopg.errors.CheckViolation), connection.transaction():
            register_file(connection, "not-a-sha256")


def test_run_status_and_provenance_constraints(isolated_database):
    with psycopg.connect(**isolated_database.connection_parameters()) as connection:
        first = register_file(connection)
        second = register_file(connection, "b" * 64)
        run = connection.execute(
            "INSERT INTO meta.ingestion_run(source_file_id) VALUES (%s) RETURNING id", (first,)
        ).fetchone()[0]
        with pytest.raises(psycopg.errors.CheckViolation), connection.transaction():
            connection.execute(
                "UPDATE meta.ingestion_run SET status='succeeded' WHERE id=%s", (run,)
            )
        with pytest.raises(psycopg.errors.ForeignKeyViolation), connection.transaction():
            connection.execute(
                """INSERT INTO meta.dataset_version(dataset_name, reference_period,
                   source_file_id, ingestion_run_id, schema_version, transform_version, row_count)
                   VALUES ('imss.cells', '2025-07-31', %s, %s, 'v1', 'test', 0)""",
                (second, run),
            )
        with pytest.raises(psycopg.errors.CheckViolation), connection.transaction():
            connection.execute(
                """INSERT INTO meta.dataset_version(dataset_name, reference_period,
                   source_file_id, ingestion_run_id, schema_version, transform_version, row_count)
                   VALUES ('imss.cells', '2025-07-31', %s, %s, 'v1', 'test', -1)""",
                (first, run),
            )


def test_failure_audit_survives_rolled_back_data_work(isolated_database):
    params = isolated_database.connection_parameters()
    with psycopg.connect(**params) as connection:
        file_id = register_file(connection)
    with pytest.raises(psycopg.errors.DivisionByZero), psycopg.connect(**params) as connection:
        connection.execute("INSERT INTO meta.ingestion_run(source_file_id) VALUES (%s)", (file_id,))
        connection.execute("SELECT 1 / 0")
    # Audit with a separate transaction after the failed data transaction rolls back.
    with psycopg.connect(**params) as connection:
        connection.execute(
            """INSERT INTO meta.ingestion_run(source_file_id, status, finished_at, error_summary)
               VALUES (%s, 'failed', now(), 'synthetic failure')""",
            (file_id,),
        )
    with psycopg.connect(**params) as connection:
        assert connection.execute(
            "SELECT status, error_summary FROM meta.ingestion_run"
        ).fetchall() == [("failed", "synthetic failure")]
