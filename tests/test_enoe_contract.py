from hashlib import sha256

import pytest

from platform_work_reform.enoe_contract import (
    HEADER_SIGNATURES,
    ContractError,
    KeySet,
    compare_keys,
    key_fields,
    preserve_sdem_text_bytes,
    unique_keys,
    validate_header,
)


def test_only_reviewed_period_and_tables_are_supported():
    assert key_fields(2025, 3, "SDEM")[-1] == "n_ren"
    for period, table in [((2025, 2), "SDEM"), ((2025, 3), "UNKNOWN")]:
        with pytest.raises(ContractError):
            key_fields(*period, table)


def test_header_checks_complete_ordered_layout(monkeypatch):
    fields = key_fields(2025, 3, "VIV")
    header = [*fields, "other"]
    monkeypatch.setitem(
        HEADER_SIGNATURES, "VIV", (len(header), sha256("\n".join(header).encode()).hexdigest())
    )
    validate_header(2025, 3, "VIV", header)
    with pytest.raises(ContractError, match="Unknown"):
        validate_header(2025, 3, "VIV", [*fields, "other", "extra"])
    with pytest.raises(ContractError, match="Unknown"):
        validate_header(2025, 3, "VIV", [*fields, "changed"])
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
        unique_keys(2025, 3, "SDEM", [{**row, "n_ren": " "}])
    with pytest.raises(ContractError, match="Missing"):
        unique_keys(2025, 3, "SDEM", [{}])


def test_comparison_exposes_both_unmatched_sides():
    parent_key = ("a",) * 6
    other_key = ("b",) * 6
    parent = KeySet(2025, 3, "release-a", "VIV", {parent_key, other_key})
    orphan_key = ("c",) * 6
    child = KeySet(
        2025,
        3,
        "release-a",
        "HOG",
        {(*parent_key, "1", "1"), (*parent_key, "2", "1"), (*orphan_key, "1", "1")},
    )
    result = compare_keys(parent, child)
    assert (
        result.matched_children,
        result.unmatched_children,
        result.parents_without_children,
    ) == (2, 1, 1)
    with pytest.raises(ContractError, match="periods or releases"):
        compare_keys(parent, KeySet(2025, 3, "release-b", "HOG", child.keys))
    with pytest.raises(ContractError, match="Unsupported"):
        compare_keys(parent, KeySet(2025, 3, "release-a", "COE1", set()))
    with pytest.raises(ContractError, match="width"):
        compare_keys(parent, KeySet(2025, 3, "release-a", "HOG", {("wrong",)}))


def test_sdem_text_preserves_bytes_without_deciding_their_meaning():
    original = b"text\xcb\xd0"
    row = {"cs_p21_des": original.decode("latin-1"), "cs_p23_des": ""}
    assert preserve_sdem_text_bytes(row) == {"cs_p21_des": original, "cs_p23_des": b""}
    with pytest.raises(ContractError, match="Missing"):
        preserve_sdem_text_bytes({"cs_p21_des": ""})
    with pytest.raises(ContractError, match="byte-preserving"):
        preserve_sdem_text_bytes({"cs_p21_des": "\u20ac", "cs_p23_des": ""})
