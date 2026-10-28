import hashlib
import json

import psycopg
import pytest

from platform_work_reform.imss_contract import LEGACY
from platform_work_reform.imss_publish import publish
from platform_work_reform.imss_staging import load

pytestmark = pytest.mark.integration


def make_source(tmp_path, suffix, number):
    source = tmp_path / f"asg-2025-06-30{suffix}.csv"
    source.write_text("|".join(LEGACY) + "\n" + "|".join([str(number)] * len(LEGACY)) + "\n")
    manifest = tmp_path / f"manifest{suffix}.json"
    manifest.write_text(
        json.dumps(
            {
                "files": [
                    {
                        "name": source.name,
                        "period": "2025-06-30",
                        "size_bytes": source.stat().st_size,
                        "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                    }
                ]
            }
        )
    )
    return source, manifest


def test_publish_reconciles_and_selects_only_one_version(isolated_database, tmp_path):
    first, manifest = make_source(tmp_path, "", 1)
    load(isolated_database, first, manifest, "utf-8")
    assert publish(isolated_database, first, manifest, "utf-8") == 1
    assert publish(isolated_database, first, manifest, "utf-8") == 1
    with psycopg.connect(**isolated_database.connection_parameters()) as c:
        assert c.execute("SELECT ptpd, asegurados FROM imss.monthly_cells").fetchall() == [
            (None, 1)
        ]
        assert c.execute("SELECT count(*) FROM meta.quality_check").fetchone() == (1,)
    second, second_manifest = make_source(tmp_path, "-revision", 2)
    load(isolated_database, second, second_manifest, "utf-8")
    with pytest.raises(ValueError, match="already selected"):
        publish(isolated_database, second, second_manifest, "utf-8")
    with psycopg.connect(**isolated_database.connection_parameters()) as c:
        assert c.execute("SELECT count(*) FROM imss.monthly_cells").fetchone() == (1,)


def test_changed_staging_rejected_before_publication(isolated_database, tmp_path):
    source, manifest = make_source(tmp_path, "", 1)
    load(isolated_database, source, manifest, "utf-8")
    with psycopg.connect(**isolated_database.connection_parameters()) as c:
        c.execute("UPDATE staging.imss_row SET raw_fields[14]='2'")
    with pytest.raises(ValueError, match="reconciliation failed"):
        publish(isolated_database, source, manifest, "utf-8")
    with psycopg.connect(**isolated_database.connection_parameters()) as c:
        assert c.execute("SELECT count(*) FROM imss.selected_month").fetchone() == (0,)
