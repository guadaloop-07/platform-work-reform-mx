from datetime import date
from uuid import uuid4

import psycopg
import pytest
from test_enoe_prepared_person import HEADER

from platform_work_reform.enoe_preparation import audit
from platform_work_reform.enoe_releases import release
from platform_work_reform.enoe_staging import ARCHIVE_SHA256

pytestmark = pytest.mark.integration


def insert_run(conn, year, quarter):
    pilot = (year, quarter) == (2025, 3)
    reviewed = {} if pilot else release(year, quarter)
    digest = ARCHIVE_SHA256 if pilot else reviewed["archive_sha256"]
    completed = "0" if pilot else reviewed["completed_interview_code"]
    header = HEADER.copy()
    if (year, quarter) == (2025, 2):
        rename = {"cve_loc": "loc", "cve_mun": "mun", "cve_ageb": "ageb", "cve_ent": "ent"}
        header = [rename.get(x, x) for x in header if x != "cvegeo"]
    source = conn.execute(
        """INSERT INTO meta.source_file(source_name,original_name,sha256,byte_size)
           VALUES ('enoe','synthetic.zip',%s,1) RETURNING id""",
        (digest,),
    ).fetchone()[0]
    run = conn.execute(
        """INSERT INTO meta.ingestion_run(source_file_id,status,finished_at)
           VALUES (%s,'succeeded',now()) RETURNING id""",
        (source,),
    ).fetchone()[0]
    conn.execute(
        "INSERT INTO staging.enoe_load VALUES (%s,%s,%s,%s)",
        (run, source, date(year, quarter * 3 - 2, 1), f"enoe-{year}q{quarter}-v1"),
    )
    conn.execute(
        "INSERT INTO staging.enoe_table VALUES (%s,'SDEM',%s,1,%s,%s)",
        (run, header, "a" * 64, "b" * 64),
    )
    return run, header, completed


def insert_person(conn, run, header, number, **changes):
    values = (
        dict.fromkeys(header, "")
        | {
            "eda": "30",
            "r_def": "0",
            "c_res": "1",
            "fac_tri": "10",
            "clase1": "1",
            "clase2": "1",
        }
        | changes
    )
    key = ["01"] * 8 + [str(number)]
    conn.execute(
        "INSERT INTO staging.enoe_row VALUES (%s,'SDEM',%s,%s,%s)",
        (run, number, key, [values[name].encode() for name in header]),
    )
    return key


def test_four_periods_preserve_universe_codes_and_run_scoped_joins(isolated_database):
    with psycopg.connect(**isolated_database.connection_parameters()) as conn:
        runs = []
        for year, quarter in [(2025, 2), (2025, 3), (2025, 4), (2026, 2)]:
            run, header, completed = insert_run(conn, year, quarter)
            runs.append(run)
            cases = [
                ({}, "eligible", 10),
                ({"eda": "98"}, "eligible", 10),
                ({"eda": "99"}, "outside_universe", None),
                ({"eda": "14", "fac_tri": ""}, "outside_universe", None),
                ({"eda": ""}, "invalid", None),
                ({"fac_tri": "0"}, "invalid", None),
                ({"clase1": "2", "clase2": "1"}, "invalid", None),
                ({"c_res": "2"}, "outside_universe", None),
                ({"eda": "bad"}, "invalid", None),
            ]
            for number, (changes, _, _) in enumerate(cases, 1):
                insert_person(conn, run, header, number, **({"r_def": completed} | changes))
            # The same person key has a questionnaire only in this run.
            if quarter == 4:
                for table in ("COE1", "COE2"):
                    conn.execute(
                        "INSERT INTO staging.enoe_table VALUES (%s,%s,%s,1,%s,%s)",
                        (run, table, ["text"], "a" * 64, "b" * 64),
                    )
                    conn.execute(
                        "INSERT INTO staging.enoe_row VALUES (%s,%s,1,%s,%s)",
                        (run, table, ["01"] * 8 + ["1"], [b"raw\xcb"]),
                    )
            rows = conn.execute(
                """SELECT preparation_status,quarterly_weight,r_def,coe1_row_number
                   FROM enoe.prepared_person_v1 WHERE run_id=%s ORDER BY sdem_row_number""",
                (run,),
            ).fetchall()
            assert [(r[0], r[1]) for r in rows] == [(s, w) for _, s, w in cases]
            assert all(r[2] == completed for r in rows)
        assert conn.execute("SELECT count(*) FROM enoe.person_quarter_v1").fetchone() == (36,)
        assert conn.execute("SELECT count(*) FROM enoe.person_quarter_pilot").fetchone() == (9,)
        assert conn.execute(
            "SELECT count(*) FROM enoe.person_quarter_v1 WHERE coe1_row_number IS NOT NULL"
        ).fetchone() == (1,)
        conn.execute(
            "UPDATE staging.enoe_table SET header[1]='changed' WHERE run_id=%s", (runs[0],)
        )
        assert conn.execute(
            "SELECT count(*) FROM enoe.person_quarter_v1 WHERE run_id=%s", (runs[0],)
        ).fetchone() == (0,)
        conn.execute(
            "UPDATE staging.enoe_load SET layout_version='unknown' WHERE run_id=%s", (runs[1],)
        )
        assert conn.execute(
            "SELECT count(*) FROM enoe.person_quarter_v1 WHERE run_id=%s", (runs[1],)
        ).fetchone() == (0,)
        conn.execute("UPDATE meta.ingestion_run SET status='failed' WHERE id=%s", (runs[2],))
        assert conn.execute(
            "SELECT count(*) FROM enoe.person_quarter_v1 WHERE run_id=%s", (runs[2],)
        ).fetchone() == (0,)
        conn.execute(
            """UPDATE meta.source_file SET sha256=%s WHERE id=
                (SELECT source_file_id FROM staging.enoe_load WHERE run_id=%s)""",
            ("c" * 64, runs[3]),
        )
        assert conn.execute("SELECT count(*) FROM enoe.person_quarter_v1").fetchone() == (0,)


def test_reconciliation_rejects_empty_invalid_and_unreconciled_runs(isolated_database):
    with pytest.raises(ValueError, match="Unsupported or empty"):
        audit(isolated_database, uuid4())
    with psycopg.connect(**isolated_database.connection_parameters()) as conn:
        run, header, _ = insert_run(conn, 2025, 3)
        insert_person(conn, run, header, 1, fac_tri="x")
    with pytest.raises(ValueError, match="Invalid prepared"):
        audit(isolated_database, run)
    with psycopg.connect(**isolated_database.connection_parameters()) as conn:
        fields = dict.fromkeys(header, "") | {
            "eda": "30",
            "r_def": "0",
            "c_res": "1",
            "fac_tri": "10",
            "clase1": "1",
            "clase2": "1",
        }
        conn.execute(
            "UPDATE staging.enoe_row SET raw_fields=%s WHERE run_id=%s",
            ([fields[name].encode() for name in header], run),
        )
    with pytest.raises(ValueError, match="reference mismatch"):
        audit(isolated_database, run)


def test_reconciliation_matches_known_synthetic_prepared_totals(isolated_database, monkeypatch):
    from types import SimpleNamespace

    from platform_work_reform import enoe_preparation

    with psycopg.connect(**isolated_database.connection_parameters()) as conn:
        run, header, _ = insert_run(conn, 2025, 3)
        insert_person(conn, run, header, 1)
        insert_person(conn, run, header, 2, clase2="2", fac_tri="5")
        insert_person(conn, run, header, 3, clase1="2", clase2="3", fac_tri="20")
    # Replace only external release references, not SQL preparation or Python arithmetic.
    monkeypatch.setattr(
        enoe_preparation,
        "CONTRACTS",
        [
            SimpleNamespace(name="SDEM", rows=3),
            SimpleNamespace(name="COE1", rows=0),
            SimpleNamespace(name="COE2", rows=0),
        ],
    )
    reference = {"population": 35, "pea": 15, "occupied": 10, "unemployed": 5}
    monkeypatch.setattr(enoe_preparation, "REFERENCE", reference)
    report = audit(isolated_database, run)
    assert report["weighted_totals"] == reference
    assert report["counts"]["eligible"] == 3
    assert report["reference_match"] is True
    assert report["precision_validated"] is False
    assert report["unemployment_percent_rounded"] == "33.3"
    assert sum(report["questionnaire_missing_categories"].values()) == 3
