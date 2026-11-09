import hashlib
import json

import psycopg
import pytest

from platform_work_reform.imss_contract import LEGACY, PLATFORM
from platform_work_reform.imss_platform_series import series
from platform_work_reform.imss_publish import publish
from platform_work_reform.imss_staging import load

pytestmark = pytest.mark.integration


def test_selected_series_provenance_missingness_and_validation(isolated_database, tmp_path):
    for period, header, codes in [
        ("2026-04-30", LEGACY, [None]),
        ("2026-05-31", PLATFORM, ["1", "0", "NA", ""]),
    ]:
        source = tmp_path / f"asg-{period}.csv"
        records = []
        for code in codes:
            row = dict.fromkeys(header, "1")
            row["ta"] = "7" if code == "1" else "3"
            if code is not None:
                row["ptpd"] = code
            records.append("|".join(row[field] for field in header))
        source.write_text("|".join(header) + "\n" + "\n".join(records) + "\n")
        manifest = tmp_path / f"{period}.json"
        manifest.write_text(
            json.dumps(
                {
                    "files": [
                        {
                            "name": source.name,
                            "period": period,
                            "size_bytes": source.stat().st_size,
                            "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                        }
                    ]
                }
            )
        )
        load(isolated_database, source, manifest, "utf-8")
        publish(isolated_database, source, manifest, "utf-8")
    report = series(isolated_database)
    legacy, platform = report["months"]
    assert legacy["categories"]["platform"]["ta"] is None
    assert legacy["total_ta"] == "3"
    assert platform["categories"]["platform"]["ta"] == "7"
    assert platform["categories"]["nonplatform"]["ta"] == "3"
    assert platform["categories"]["missing"]["ta"] == "6"
    assert platform["total_ta"] == "16"
    assert len(platform["source_sha256"]) == 64
    with psycopg.connect(**isolated_database.connection_parameters()) as connection:
        connection.execute(
            "UPDATE staging.imss_row SET raw_fields[16]='NA' WHERE run_id=%s AND row_number=1",
            (platform["run_id"],),
        )
    assert series(isolated_database)["months"][1]["categories"]["platform"]["ta"] is None
    with psycopg.connect(**isolated_database.connection_parameters()) as connection:
        connection.execute(
            "UPDATE staging.imss_row SET raw_fields[5]='2' WHERE run_id=%s AND row_number=1",
            (platform["run_id"],),
        )
    with pytest.raises(ValueError, match="Invalid ptpd"):
        series(isolated_database)
