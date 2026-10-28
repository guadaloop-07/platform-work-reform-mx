import hashlib
import json

import psycopg
import pytest

from platform_work_reform.imss_contract import LEGACY, PLATFORM
from platform_work_reform.imss_staging import load

pytestmark = pytest.mark.integration


def make_file(tmp_path, header, data):
    source = tmp_path / "asg-2025-06-30.csv"
    source.write_text("|".join(header) + "\n" + data + "\n", encoding="utf-8")
    manifest = tmp_path / "inventory.json"
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


@pytest.mark.parametrize("header,platform", [(LEGACY, None), (PLATFORM, "1")])
def test_stages_once_preserving_platform_missingness(isolated_database, tmp_path, header, platform):
    fields = ["1"] * len(header)
    source, manifest = make_file(tmp_path, header, "|".join(fields))
    assert load(isolated_database, source, manifest, "utf-8") == 1
    assert load(isolated_database, source, manifest, "utf-8") == 1
    with psycopg.connect(**isolated_database.connection_parameters()) as connection:
        assert connection.execute("SELECT raw_fields[5] FROM staging.imss_row").fetchall() == [
            (platform,)
        ]
        assert connection.execute("SELECT count(*) FROM staging.imss_load").fetchone() == (1,)


def test_invalid_row_rolls_back_but_records_failed_run(isolated_database, tmp_path):
    source, manifest = make_file(tmp_path, LEGACY, "1|2")
    with pytest.raises(ValueError, match="column count"):
        load(isolated_database, source, manifest, "utf-8")
    with psycopg.connect(**isolated_database.connection_parameters()) as connection:
        assert connection.execute("SELECT count(*) FROM staging.imss_row").fetchone() == (0,)
        assert connection.execute("SELECT status FROM meta.ingestion_run").fetchone() == ("failed",)


def test_changed_source_rejected_before_loading(isolated_database, tmp_path):
    source, manifest = make_file(tmp_path, LEGACY, "|".join(["1"] * len(LEGACY)))
    source.write_bytes(source.read_bytes() + b"x")
    with pytest.raises(ValueError, match="does not match"):
        load(isolated_database, source, manifest, "utf-8")
