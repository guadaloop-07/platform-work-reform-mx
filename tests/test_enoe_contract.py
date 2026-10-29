import pytest

from platform_work_reform.enoe_contract import (
    ContractError,
    compare_keys,
    key_fields,
    unique_keys,
    validate_header,
)


def test_only_reviewed_period_and_tables_are_supported():
    assert key_fields(2025, 3, "SDEM")[-1] == "N_REN"
    for period, table in [((2025, 2), "SDEM"), ((2025, 3), "UNKNOWN")]:
        with pytest.raises(ContractError):
            key_fields(*period, table)


def test_header_checks_keys_and_rejects_duplicate_names():
    fields = key_fields(2025, 3, "VIV")
    validate_header(2025, 3, "VIV", [*fields, "OTHER"])
    with pytest.raises(ContractError, match="Missing key"):
        validate_header(2025, 3, "VIV", fields[:-1])
    with pytest.raises(ContractError, match="Duplicate"):
        validate_header(2025, 3, "VIV", [*fields, fields[0]])


def test_keys_preserve_strings_and_reject_invalid_or_duplicate_keys():
    fields = key_fields(2025, 3, "SDEM")
    row = dict.fromkeys(fields, "01")
    assert next(iter(unique_keys(2025, 3, "SDEM", [row])))[0] == "01"
    with pytest.raises(ContractError, match="Duplicate"):
        unique_keys(2025, 3, "SDEM", [row, row])
    with pytest.raises(ContractError, match="nonblank"):
        unique_keys(2025, 3, "SDEM", [{**row, "N_REN": " "}])
    with pytest.raises(ContractError, match="Missing"):
        unique_keys(2025, 3, "SDEM", [{}])


def test_comparison_exposes_both_unmatched_sides():
    result = compare_keys({("a",), ("b",)}, {("a", "1"), ("a", "2"), ("c", "1")})
    assert (
        result.matched_children,
        result.unmatched_children,
        result.parents_without_children,
    ) == (2, 1, 1)
