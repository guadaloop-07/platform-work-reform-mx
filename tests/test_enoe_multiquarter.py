import csv
import hashlib
import io
import json
import zipfile

import psycopg
import pytest

from platform_work_reform import enoe_contract, enoe_releases, enoe_source_support, enoe_staging
from platform_work_reform.enoe_contract import ContractError, key_fields, validate_header
from platform_work_reform.enoe_quarter_matrix import compare


@pytest.mark.parametrize(
    "year,quarter,entity", [(2025, 2, "ent"), (2025, 4, "cve_ent"), (2026, 2, "cve_ent")]
)
def test_explicit_period_keys_and_member_paths(year, quarter, entity):
    assert key_fields(year, quarter, "SDEM")[3] == entity
    assert f"{year}_{quarter}t.csv" in enoe_staging.members("SDEM", year, quarter)[0]
    with pytest.raises(ContractError, match="header"):
        validate_header(year, quarter, "SDEM", list(key_fields(year, quarter, "SDEM")))


def synthetic_release(tmp_path, monkeypatch, year, quarter):
    reviewed = json.loads(json.dumps(enoe_releases.release(year, quarter)))
    entity = reviewed["entity_field"]
    path = tmp_path / f"{year}q{quarter}.zip"
    with zipfile.ZipFile(path, "w") as archive:
        for table, contract in reviewed["tables"].items():
            key = contract["key"]
            header = list(key)
            extra = [entity, "est_d_tri", "upm"]
            if table == "SDEM":
                extra += ["eda", "r_def", "c_res", "fac_tri", "clase1", "clase2"]
            header += [field for field in extra if field not in header] + ["text"]
            values = dict.fromkeys(header, "01")
            values.update(
                {
                    "eda": "30",
                    "r_def": reviewed["completed_interview_code"],
                    "c_res": "1",
                    "fac_tri": "10",
                    "clase1": "1",
                    "clase2": "1",
                    "text": "raw\xcb",
                }
            )
            stream = io.StringIO(newline="")
            csv.writer(stream).writerows([header, [values[name] for name in header]])
            data = stream.getvalue().encode("latin-1")
            stream = io.StringIO(newline="")
            csv.writer(stream).writerows([["NEMÓNICO"], *[[name] for name in header]])
            dictionary = stream.getvalue().encode("utf-8")
            data_path, dictionary_path = enoe_staging.members(table, year, quarter)
            archive.writestr(data_path, data)
            archive.writestr(dictionary_path, dictionary)
            contract.update(
                rows=1,
                member_sha256=hashlib.sha256(data).hexdigest(),
                dictionary_sha256=hashlib.sha256(dictionary).hexdigest(),
            )
            reviewed["header_signatures"][table] = [
                len(header),
                hashlib.sha256("\n".join(header).encode()).hexdigest(),
            ]
    reviewed["archive_sha256"] = enoe_staging.digest(path)
    reviewed["reference_totals"] = {"population": 10, "pea": 10, "occupied": 10}
    registry = {**enoe_releases.releases(), f"{year}q{quarter}": reviewed}
    monkeypatch.setattr(enoe_releases, "releases", lambda: registry)
    return path


@pytest.mark.integration
def test_multiple_periods_coexist_and_reconcile_without_pilot_view(
    isolated_database, tmp_path, monkeypatch
):
    entries = []
    for year, quarter in [(2025, 2), (2025, 4), (2026, 2)]:
        path = synthetic_release(tmp_path, monkeypatch, year, quarter)
        counts = enoe_staging.load(isolated_database, path, year=year, quarter=quarter)
        assert counts == dict.fromkeys(enoe_contract.KEYS, 1)
        assert enoe_staging.load(isolated_database, path, year=year, quarter=quarter) == counts
        with psycopg.connect(**isolated_database.connection_parameters()) as conn:
            run = conn.execute(
                "SELECT run_id FROM staging.enoe_load WHERE layout_version=%s",
                (f"enoe-{year}q{quarter}-v1",),
            ).fetchone()[0]
        report = enoe_source_support.verify(
            isolated_database, run, path, year=year, quarter=quarter
        )
        assert report["source_staged_design_match"] is True
        assert report["sdem_audit"]["weighted_totals"]["population"] == 10
        assert report["variance_ready"] is False
        entries.append({"year": year, "quarter": quarter, "archive": str(path), "run_id": str(run)})
    matrix = compare(isolated_database, entries)
    assert len(matrix["quarters"]) == 3
    assert matrix["precision_validated"] is False
    assert all(
        pair["shared_singleton_stratum_codes"] == 1 for pair in matrix["singleton_code_overlaps"]
    )
    with pytest.raises(ValueError, match="Duplicate quarter"):
        compare(isolated_database, [entries[0], entries[0]])
    with psycopg.connect(**isolated_database.connection_parameters()) as conn:
        assert conn.execute("SELECT count(*) FROM staging.enoe_load").fetchone() == (3,)
        assert conn.execute("SELECT count(*) FROM enoe.person_quarter_pilot").fetchone() == (0,)


@pytest.mark.integration
def test_wrong_release_period_is_rejected_without_writes(isolated_database, tmp_path, monkeypatch):
    path = synthetic_release(tmp_path, monkeypatch, 2025, 2)
    with pytest.raises(ValueError, match="reviewed"):
        enoe_staging.load(isolated_database, path, year=2025, quarter=4)
    with psycopg.connect(**isolated_database.connection_parameters()) as conn:
        assert conn.execute("SELECT count(*) FROM staging.enoe_load").fetchone() == (0,)
