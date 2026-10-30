import psycopg
import pytest
from test_enoe_staging import make_archive

from platform_work_reform import enoe_staging

pytestmark = pytest.mark.integration


def test_person_view_preserves_people_bytes_and_load_scope(
    isolated_database, tmp_path, monkeypatch
):
    source = make_archive(tmp_path, monkeypatch)
    enoe_staging.load(isolated_database, source)
    with psycopg.connect(**isolated_database.connection_parameters()) as conn:
        run_id = conn.execute("SELECT run_id FROM staging.enoe_load").fetchone()[0]
        conn.execute(
            """INSERT INTO staging.enoe_row
               SELECT run_id, table_name, 2, source_key[1:8] || ARRAY['02'], raw_fields
               FROM staging.enoe_row WHERE run_id=%s AND table_name='SDEM'""",
            (run_id,),
        )
        other_source = conn.execute(
            """INSERT INTO meta.source_file(source_name, original_name, sha256, byte_size)
               VALUES ('enoe', 'other.zip', %s, 1) RETURNING id""",
            ("a" * 64,),
        ).fetchone()[0]
        other_run = conn.execute(
            """INSERT INTO meta.ingestion_run(source_file_id, status, finished_at)
               VALUES (%s, 'succeeded', now()) RETURNING id""",
            (other_source,),
        ).fetchone()[0]
        conn.execute(
            """INSERT INTO staging.enoe_load
               (run_id, source_file_id, reference_period, layout_version)
               VALUES (%s, %s, '2025-07-01', 'enoe-2025q3-v1')""",
            (other_run, other_source),
        )
        conn.execute(
            """INSERT INTO staging.enoe_table
               SELECT %s, table_name, header, row_count, member_sha256, dictionary_sha256
               FROM staging.enoe_table WHERE run_id=%s AND table_name='COE1'""",
            (other_run, run_id),
        )
        conn.execute(
            """INSERT INTO staging.enoe_row
               SELECT %s, table_name, 1, source_key[1:8] || ARRAY['02'], raw_fields
               FROM staging.enoe_row WHERE run_id=%s AND table_name='COE1'""",
            (other_run, run_id),
        )
        rows = conn.execute(
            """SELECT source_key[9], sdem_raw_fields[10], coe1_row_number, coe2_row_number
               FROM enoe.person_quarter_pilot ORDER BY source_key[9]"""
        ).fetchall()
        assert [(row[0], bytes(row[1]), row[2], row[3]) for row in rows] == [
            ("01", b"raw\xcb", 1, 1),
            ("02", b"raw\xcb", None, None),
        ]
        conn.execute(
            "UPDATE staging.enoe_load SET layout_version='other' WHERE run_id=%s", (run_id,)
        )
        assert conn.execute("SELECT count(*) FROM enoe.person_quarter_pilot").fetchone() == (0,)
