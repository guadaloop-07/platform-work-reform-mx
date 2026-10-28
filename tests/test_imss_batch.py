import hashlib
import json
from datetime import date

import psycopg
import pytest

from platform_work_reform.imss_batch import run, select_files, source_encoding
from platform_work_reform.imss_contract import LEGACY


def test_encoding_ambiguity_and_bom(tmp_path):
    path = tmp_path / "file.csv"
    header = "|".join(LEGACY) + "\n"
    path.write_bytes((header + "|".join(["1"] * len(LEGACY)) + "\n").encode("cp1252"))
    assert source_encoding(path) == "cp1252"
    path.write_bytes(path.read_bytes() + b"\x80")
    with pytest.raises(ValueError, match="Ambiguous"):
        source_encoding(path)
    path.write_text(header, encoding="utf-8-sig")
    assert source_encoding(path) == "utf-8-sig"


def test_month_coverage_and_duplicate_versions():
    start, end = date(2025, 1, 1), date(2025, 2, 28)
    entries = [{"name": "one.csv", "period": "2025-01-31"}]
    with pytest.raises(ValueError, match="every requested month"):
        select_files({"files": entries}, start, end)
    entries.extend(
        [
            {"name": "two.csv", "period": "2025-02-28"},
            {"name": "revision.csv", "period": "2025-02-28"},
        ]
    )
    with pytest.raises(ValueError, match="Multiple source versions"):
        select_files({"files": entries}, start, end)


@pytest.mark.integration
def test_batch_publishes_then_resumes_without_duplication(isolated_database, tmp_path, monkeypatch):
    source = tmp_path / "source"
    source.mkdir()
    path = source / "asg-2025-06-30.csv"
    path.write_bytes(
        ("|".join(LEGACY) + "\n" + "|".join(["1"] * len(LEGACY)) + "\n").encode("cp1252")
    )
    manifest = tmp_path / "inventory.json"
    manifest.write_text(
        json.dumps(
            {
                "files": [
                    {
                        "name": path.name,
                        "period": "2025-06-30",
                        "size_bytes": path.stat().st_size,
                        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    }
                ]
            }
        )
    )
    progress = tmp_path / "progress.jsonl"
    monkeypatch.setattr(
        "platform_work_reform.imss_batch.database_free_bytes", lambda: 100 * 1024**3
    )
    args = (isolated_database, source, manifest, date(2025, 6, 1), date(2025, 6, 30), progress)
    run(*args)
    run(*args)
    with psycopg.connect(**isolated_database.connection_parameters()) as connection:
        assert connection.execute("SELECT ptpd, asegurados FROM imss.monthly_cells").fetchall() == [
            (None, 1)
        ]
    assert [json.loads(line)["status"] for line in progress.read_text().splitlines()] == [
        "selected",
        "already_selected",
    ]
