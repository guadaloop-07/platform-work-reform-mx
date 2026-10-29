import csv
import hashlib
import io
import os
import zipfile
from pathlib import Path

import psycopg
import pytest

from platform_work_reform import enoe_staging

pytestmark = pytest.mark.integration


def csv_bytes(rows, encoding):
    out = io.StringIO(newline="")
    csv.writer(out, lineterminator="\r\n").writerows(rows)
    return out.getvalue().encode(encoding)


def make_archive(tmp_path, monkeypatch, *, bad=None):
    archive = tmp_path / "enoe.zip"
    contracts = []
    with zipfile.ZipFile(archive, "w") as z:
        for original in enoe_staging.CONTRACTS:
            header = [*original.key, "text"]
            row = ["01"] * len(original.key) + ["raw\xcb"]
            if bad == "orphan" and original.name == "COE2":
                row[0] = "02"
            rows = [header, row]
            if bad == "duplicate" and original.name == "COE2":
                rows.append(row)
            if bad == "width" and original.name == "COE2":
                rows[1] = row[:-1]
            data = csv_bytes(rows, "latin-1")
            dictionary = csv_bytes([["NEMÓNICO"], *[[field] for field in header]], "utf-8")
            data_name, dictionary_name = enoe_staging.members(original.name)
            z.writestr(data_name, data)
            z.writestr(dictionary_name, dictionary)
            contracts.append(
                enoe_staging.TableContract(
                    original.name,
                    original.key,
                    len(rows) - 1,
                    hashlib.sha256(data).hexdigest(),
                    hashlib.sha256(dictionary).hexdigest(),
                )
            )
    monkeypatch.setattr(enoe_staging, "CONTRACTS", tuple(contracts))
    monkeypatch.setattr(enoe_staging, "ARCHIVE_SHA256", enoe_staging.digest(archive))
    return archive


def test_transaction_loads_bytes_and_is_idempotent(isolated_database, tmp_path, monkeypatch):
    source = make_archive(tmp_path, monkeypatch)
    assert enoe_staging.load(isolated_database, source) == dict.fromkeys(
        ("VIV", "HOG", "SDEM", "COE1", "COE2"), 1
    )
    assert enoe_staging.load(isolated_database, source)["SDEM"] == 1
    with psycopg.connect(**isolated_database.connection_parameters()) as conn:
        assert conn.execute("SELECT count(*) FROM staging.enoe_load").fetchone() == (1,)
        value = conn.execute(
            "SELECT raw_fields[10] FROM staging.enoe_row WHERE table_name='SDEM'"
        ).fetchone()[0]
        assert bytes(value) == b"raw\xcb"
        assert conn.execute("SELECT status FROM meta.ingestion_run").fetchone() == ("succeeded",)


@pytest.mark.parametrize("bad", ["orphan", "duplicate", "width"])
def test_bad_release_rolls_back_every_table(isolated_database, tmp_path, monkeypatch, bad):
    source = make_archive(tmp_path, monkeypatch, bad=bad)
    with pytest.raises((ValueError, psycopg.errors.UniqueViolation)):
        enoe_staging.load(isolated_database, source)
    with psycopg.connect(**isolated_database.connection_parameters()) as conn:
        assert conn.execute("SELECT count(*) FROM staging.enoe_load").fetchone() == (0,)
        assert conn.execute("SELECT count(*) FROM staging.enoe_row").fetchone() == (0,)
        assert conn.execute("SELECT count(*) FROM meta.source_file").fetchone() == (0,)


@pytest.mark.skipif(
    not os.environ.get("PWR_ENOE_PILOT_ARCHIVE"), reason="Official pilot archive not configured"
)
def test_official_pilot_in_isolated_database(isolated_database):
    archive = os.environ["PWR_ENOE_PILOT_ARCHIVE"]
    counts = enoe_staging.load(isolated_database, Path(archive))
    assert counts == {contract.name: contract.rows for contract in enoe_staging.CONTRACTS}
