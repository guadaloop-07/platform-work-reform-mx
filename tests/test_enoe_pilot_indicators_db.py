import pytest
from test_enoe_staging import make_archive

from platform_work_reform import enoe_pilot_indicators, enoe_staging

pytestmark = pytest.mark.integration


def test_audit_rejects_unreviewed_run(isolated_database, tmp_path, monkeypatch):
    source = make_archive(tmp_path, monkeypatch)
    enoe_staging.load(isolated_database, source)
    import psycopg

    with psycopg.connect(**isolated_database.connection_parameters()) as conn:
        run_id = conn.execute("SELECT run_id FROM staging.enoe_load").fetchone()[0]
    with pytest.raises(ValueError, match="Unsupported ENOE load"):
        enoe_pilot_indicators.audit(isolated_database, run_id)
