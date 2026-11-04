import csv
import hashlib
import io
import zipfile
from types import SimpleNamespace
from uuid import uuid4

import pytest

from platform_work_reform import enoe_source_support as source
from platform_work_reform.enoe_design_support import FIELDS


def csv_bytes(rows):
    stream = io.StringIO(newline="")
    csv.writer(stream).writerows(rows)
    return stream.getvalue().encode("ascii")


@pytest.fixture
def archive(tmp_path, monkeypatch):
    path = tmp_path / "synthetic.zip"
    contracts = []
    with zipfile.ZipFile(path, "w") as zipped:
        for name in ("VIV", "HOG", "SDEM"):
            header = list(FIELDS) if name == "SDEM" else ["cve_ent", "est_d_tri", "upm"]
            rows = (
                [["01", "A", "1", "30", "0", "1", "10", "1", "1"]]
                if name == "SDEM"
                else [["01", "A", "1"], ["01", "A", "2"], ["01", "B", "3"]]
            )
            # Use numeric raw source design codes, preserving their leading zeros.
            rows = [
                ["001" if code == "A" else "002" if code == "B" else code for code in row]
                for row in rows
            ]
            data = csv_bytes([header, *rows])
            zipped.writestr(source.members(name)[0], data)
            contracts.append(
                SimpleNamespace(
                    name=name, rows=len(rows), member_sha256=hashlib.sha256(data).hexdigest()
                )
            )
    monkeypatch.setattr(source, "ARCHIVE_SHA256", source.digest(path))
    monkeypatch.setattr(source, "CONTRACTS", contracts)
    expected_headers = {
        name: list(FIELDS) if name == "SDEM" else ["cve_ent", "est_d_tri", "upm"]
        for name in ("VIV", "HOG", "SDEM")
    }

    def validate(year, quarter, name, header):
        assert (year, quarter) == (2025, 3)
        if header != expected_headers[name]:
            raise ValueError("Unsupported header")

    monkeypatch.setattr(source, "validate_header", validate)
    return path


def test_parent_support_can_resolve_an_apparent_sdem_singleton(archive):
    report = source.verify_source(archive)
    assert report["source_tables"]["VIV"] == {
        "records": 3,
        "observed_strata": 2,
        "observed_nested_upms": 3,
        "singleton_strata": 1,
    }
    assert report["parent_comparisons"]["VIV"] == {
        "parent_upms_without_sdem": 2,
        "parent_strata_without_sdem": 1,
        "sdem_singletons_with_multiple_parent_upms": 1,
    }
    assert report["variance_ready"] is False


def test_unreviewed_archive_rejected_before_parsing(tmp_path):
    path = tmp_path / "unreviewed.zip"
    path.write_bytes(b"unreviewed")
    with pytest.raises(ValueError, match="archive hash"):
        source.verify_source(path)


def test_member_hash_rejected_even_with_reviewed_archive_hash(archive, monkeypatch):
    monkeypatch.setattr(source, "CONTRACTS", [SimpleNamespace(name="VIV", member_sha256="0" * 64)])
    with pytest.raises(ValueError, match="member hash"):
        source.verify_source(archive)


def test_source_staged_comparison_includes_ordered_fields(archive, monkeypatch):
    result = source.verify_source(archive)["sdem_audit"]
    monkeypatch.setattr(source, "audit", lambda settings, run_id: result)
    assert source.verify(None, uuid4(), archive)["source_staged_design_match"] is True
    changed = {**result, "ordered_fields_sha256": "different"}
    monkeypatch.setattr(source, "audit", lambda settings, run_id: changed)
    with pytest.raises(ValueError, match="mismatch"):
        source.verify(None, uuid4(), archive)


def test_source_count_and_header_gates(archive, monkeypatch):
    contracts = source.CONTRACTS
    monkeypatch.setattr(
        source,
        "CONTRACTS",
        [SimpleNamespace(name="VIV", rows=999, member_sha256=contracts[0].member_sha256)],
    )
    with pytest.raises(ValueError, match="row count"):
        source.verify_source(archive)
    monkeypatch.setattr(source, "CONTRACTS", contracts)
    monkeypatch.setattr(
        source,
        "validate_header",
        lambda *args: (_ for _ in ()).throw(ValueError("Unsupported header")),
    )
    with pytest.raises(ValueError, match="header"):
        source.verify_source(archive)
