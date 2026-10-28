import codecs

import pytest

from platform_work_reform.encoding import inspect, normalize


def test_ascii_is_ambiguous(tmp_path):
    source = tmp_path / "source"
    source.write_bytes(b"simple ascii")
    result = inspect(source)
    assert result["compatible"] == ["utf-8", "cp1252", "iso-8859-1"]
    assert not result["utf8_bom"]


def test_bom_and_cp1252_conversion(tmp_path):
    source = tmp_path / "source"
    output = tmp_path / "out"
    source.write_bytes(codecs.BOM_UTF8 + "año".encode())
    assert inspect(source)["utf8_bom"]
    normalize(source, output, "utf-8-sig")
    assert output.read_bytes() == "año".encode()
    output.unlink()
    source.write_bytes("año €".encode("cp1252"))
    assert "utf-8" not in inspect(source)["compatible"]
    normalize(source, output, "cp1252")
    assert output.read_text() == "año €"


def test_invalid_input_does_not_publish_and_never_overwrites(tmp_path):
    source = tmp_path / "source"
    output = tmp_path / "out"
    source.write_bytes(b"bad\xff")
    with pytest.raises(UnicodeDecodeError):
        normalize(source, output, "utf-8")
    assert not output.exists()
    output.write_text("existing")
    with pytest.raises(ValueError):
        normalize(source, output, "cp1252")
    assert output.read_text() == "existing"
    assert source.read_bytes() == b"bad\xff"
