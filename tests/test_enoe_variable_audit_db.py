import psycopg
import pytest
from test_enoe_preparation import insert_person, insert_run

from platform_work_reform.enoe_variable_audit import BASE, FIELDS, fingerprint, verify_staging

pytestmark = pytest.mark.integration


def test_selected_fields_fingerprint_is_run_scoped_and_detects_staging_change(isolated_database):
    with psycopg.connect(**isolated_database.connection_parameters()) as conn:
        run, header, _ = insert_run(conn, 2025, 3)
        key = insert_person(conn, run, header, 1, pos_ocu="01", seg_soc=" 1 ")
        fields = (*BASE, *FIELDS["SDEM"])
        defaults = dict.fromkeys(fields, "") | {
            "eda": "30",
            "r_def": "0",
            "c_res": "1",
            "fac_tri": "10",
            "clase1": "1",
            "clase2": "1",
            "pos_ocu": "01",
            "seg_soc": " 1 ",
        }
        expected = fingerprint([(1, key, [defaults[f] for f in fields])])
        verify_staging(conn, run, "SDEM", 2025, 3, 1, expected)
        conn.execute(
            "UPDATE staging.enoe_row SET raw_fields[%s]=%s WHERE run_id=%s",
            (header.index("seg_soc") + 1, b"1", run),
        )
        with pytest.raises(ValueError, match="disagree"):
            verify_staging(conn, run, "SDEM", 2025, 3, 1, expected)
        with pytest.raises(ValueError, match="metadata mismatch"):
            verify_staging(conn, run, "SDEM", 2025, 3, 2, expected)
