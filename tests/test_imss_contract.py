import pytest

from platform_work_reform.imss_contract import LEGACY, PLATFORM, layout, rows


def test_known_layouts_and_unknown_rejected():
    assert layout(list(LEGACY)) == "legacy-v1"
    assert layout(list(PLATFORM)) == "platform-v1"
    with pytest.raises(ValueError, match="Unknown"):
        layout(list(LEGACY) + ["ptpd"])


def test_rows_preserve_missing_codes_and_reject_bad_width(tmp_path):
    path = tmp_path / "sample.csv"
    header = "|".join(LEGACY)
    values = ["NA", ""] + ["0"] * (len(LEGACY) - 2)
    path.write_bytes((header + "\r\n" + "|".join(values) + "\r\n").encode("cp1252"))
    assert list(rows(path, "cp1252")) == [("legacy-v1", values)]
    path.write_bytes((header + "\n1|2\n").encode("cp1252"))
    with pytest.raises(ValueError, match="column count"):
        list(rows(path, "cp1252"))


def test_utf8_bom_requires_explicit_sig_decoder(tmp_path):
    path = tmp_path / "source.csv"
    path.write_text(
        "|".join(PLATFORM) + "\n" + "|".join(["0"] * len(PLATFORM)) + "\n", encoding="utf-8-sig"
    )
    assert len(list(rows(path, "utf-8-sig"))) == 1
    with pytest.raises(ValueError, match="Unknown"):
        list(rows(path, "utf-8"))
