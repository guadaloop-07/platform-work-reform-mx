import hashlib
import json
from datetime import date

import pytest

from platform_work_reform.inventory import inventory, write_manifest


def test_inventory_detects_copies_and_revisions(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "asg-2025-07-31.csv").write_bytes(b"original")
    (source / "asg-2025-07-31-copy.csv").write_bytes(b"original")
    (source / "asg-2025-07-31-revision.csv").write_bytes(b"revised")
    (source / "asg-2024-12-31.csv").write_bytes(b"earlier")
    (source / "asg-2010-02-29.csv").write_bytes(b"invalid outside range")
    result = inventory(source, date(2025, 1, 1), date(2025, 12, 31))
    assert len(result["files"]) == 3
    assert len(result["duplicate_content"]) == 1
    assert result["periods_with_revisions"] == ["2025-07-31"]
    assert result["files"][0]["size_bytes"] == len(b"original")


def test_manifest_never_overwrites_or_writes_inside_source(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "asg-2025-07-31.csv").write_bytes(b"original")
    start, end = date(2025, 7, 1), date(2025, 7, 31)
    output = tmp_path / "manifest.json"
    write_manifest(source, start, end, output)
    assert json.loads(output.read_text())["files"][0]["period"] == "2025-07-31"
    with pytest.raises(FileExistsError):
        write_manifest(source, start, end, output)
    with pytest.raises(ValueError, match="outside"):
        write_manifest(source, start, end, source / "manifest.json")
    assert (source / "asg-2025-07-31.csv").read_bytes() == b"original"


def test_invalid_period_and_symlinks_are_rejected(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "asg-2025-02-30.csv").write_text("invalid")
    with pytest.raises(ValueError, match="Invalid date"):
        inventory(source, date(2025, 1, 1), date(2025, 12, 31))
    (source / "asg-2025-02-30.csv").unlink()
    (source / "asg-2025-02-28.csv").symlink_to(tmp_path / "missing")
    with pytest.raises(ValueError, match="regular file"):
        inventory(source, date(2025, 1, 1), date(2025, 12, 31))


def test_file_changed_during_hash_is_rejected(tmp_path, monkeypatch):
    path = tmp_path / "asg-2025-07-31.csv"
    path.write_bytes(b"original")
    real_digest = hashlib.file_digest

    def mutate(stream, algorithm):
        result = real_digest(stream, algorithm)
        path.write_bytes(b"different content")
        return result

    monkeypatch.setattr("platform_work_reform.inventory.hashlib.file_digest", mutate)
    with pytest.raises(ValueError, match="changed while hashing"):
        inventory(tmp_path, date(2025, 7, 1), date(2025, 7, 31))
