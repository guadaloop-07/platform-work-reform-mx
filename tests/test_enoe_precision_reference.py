import pytest

from platform_work_reform.enoe_precision_reference import HEADERS, VARIABLES, read_cells, reconcile


def reference_cells():
    cells = dict(HEADERS)
    for row, name in enumerate(VARIABLES, start=2):
        fields = {
            "C": "ENOE",
            "D": "2025",
            "E": "Trimestral",
            "F": "III",
            "G": "Definitivo",
            "I": "00",
            "K": "Nacional",
            "N": name,
            "O": "Tasa" if row == 5 else "Total",
            "P": "100",
            "Q": "5",
            "R": "5",
            "S": "90",
            "T": "91.775",
            "U": "108.225",
        }
        cells.update({f"{col}{row}": value for col, value in fields.items()})
    return cells


def test_reference_interval_check_does_not_claim_variance_validation():
    result = reconcile(reference_cells())
    assert result["reference_interval_arithmetic_match"] is True
    assert result["sampling_variance_validated"] is False


def test_mismatching_interval_is_visible():
    cells = {**reference_cells(), "T2": "91"}
    result = reconcile(cells)
    assert result["reference_interval_arithmetic_match"] is False
    assert result["references"][0]["interval_arithmetic_match"] is False


@pytest.mark.parametrize(
    "cell,value", [("D2", "2024"), ("S2", "95"), ("K2", "State"), ("R1", "other"), ("N2", "other")]
)
def test_wrong_period_population_level_or_header_rejected(cell, value):
    with pytest.raises(ValueError, match="Unsupported"):
        reconcile({**reference_cells(), cell: value})


def test_unreviewed_workbook_rejected_before_xml_parse(tmp_path):
    path = tmp_path / "unreviewed.xlsx"
    path.write_bytes(b"not an official workbook")
    with pytest.raises(ValueError, match="hash"):
        read_cells(path)
