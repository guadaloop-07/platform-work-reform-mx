"""Pre-ingestion checks for the documented 2025 Q3 ENOE join keys.

These checks are not a complete CSV layout or a substitute for reconciliation.
"""

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256


class ContractError(ValueError):
    """An input is outside the documented contract or has invalid keys."""


DWELLING = ("tipo", "mes_cal", "cd_a", "cve_ent", "con", "v_sel")
HOUSEHOLD = (*DWELLING, "n_hog", "h_mud")
PERSON = (*HOUSEHOLD, "n_ren")
KEYS = {"VIV": DWELLING, "HOG": HOUSEHOLD, "SDEM": PERSON, "COE1": PERSON, "COE2": PERSON}
RAW_TEXT_FIELDS = ("cs_p21_des", "cs_p23_des")
HEADER_SIGNATURES = {
    "VIV": (26, "f666b0bfcd8f14a88696a2a17c0134e118fed120c49b2ff55476f60c3a8bb581"),
    "HOG": (38, "91cde8fd01486f2e2a78887e30c135a69fe13a6d416d1c3c612a9b5ba677b8f9"),
    "SDEM": (115, "13613857a5a025f9ebd57d92e35ca905fb2336855dc6269f3a6bf0951a55fe54"),
    "COE1": (174, "5d743d50d7d7ddf17b72849889a090d234e6c56dc2af8960fa1f25130c7e50c5"),
    "COE2": (84, "db0aa70068284708f268cbe5021bf92eb8df39a5df1f95858df0e8d31ded16f2"),
}
RELATIONSHIPS = {
    ("VIV", "HOG"),
    ("HOG", "SDEM"),
    ("SDEM", "COE1"),
    ("SDEM", "COE2"),
    ("COE1", "COE2"),
}


def preserve_sdem_text_bytes(row: Mapping[str, str]) -> dict[str, bytes]:
    """Recover logical CSV field bytes from a strict Latin-1 byte-preserving parse.

    Latin-1 is only a reversible byte mapping here, not a claim about the
    source encoding. The complete original CSV is retained separately.
    """
    result = {}
    for field in RAW_TEXT_FIELDS:
        try:
            value = row[field]
        except KeyError as exc:
            raise ContractError(f"Missing source text field: {field}") from exc
        if not isinstance(value, str):
            raise ContractError(f"Source text field must be a string: {field}")
        try:
            result[field] = value.encode("latin-1", errors="strict")
        except UnicodeEncodeError as exc:
            raise ContractError(f"Source text field is not byte-preserving: {field}") from exc
    return result


def key_fields(year: int, quarter: int, table: str) -> tuple[str, ...]:
    """Return fields only for the period whose published dictionary was reviewed."""
    if (year, quarter) != (2025, 3) or table not in KEYS:
        raise ContractError("Unsupported ENOE period or table")
    return KEYS[table]


def validate_header(year: int, quarter: int, table: str, header: Sequence[str]) -> None:
    """Require the exact ordered, reviewed CSV header; values are not validated."""
    fields = key_fields(year, quarter, table)
    if len(header) != len(set(header)):
        raise ContractError("Duplicate column names")
    missing = set(fields) - set(header)
    if missing:
        raise ContractError(f"Missing key fields: {', '.join(sorted(missing))}")
    if any("\n" in name or "\r" in name for name in header):
        raise ContractError("Unknown source header")
    try:
        signature = sha256("\n".join(header).encode("ascii")).hexdigest()
    except UnicodeEncodeError as exc:
        raise ContractError("Unknown source header") from exc
    if (len(header), signature) != HEADER_SIGNATURES[table]:
        raise ContractError("Unknown source header")


def unique_keys(
    year: int, quarter: int, table: str, rows: Iterable[Mapping[str, str]]
) -> set[tuple[str, ...]]:
    """Reject absent, blank, or duplicated keys without normalizing source values."""
    fields = key_fields(year, quarter, table)
    keys: set[tuple[str, ...]] = set()
    for row in rows:
        try:
            key = tuple(row[field] for field in fields)
        except KeyError as exc:
            raise ContractError(f"Missing key field: {exc.args[0]}") from exc
        if any(not isinstance(value, str) or not value.strip() for value in key):
            raise ContractError("Key fields must contain nonblank source strings")
        if key in keys:
            raise ContractError("Duplicate source key")
        keys.add(key)
    return keys


@dataclass(frozen=True)
class JoinCounts:
    parent_keys: int
    child_keys: int
    matched_children: int
    unmatched_children: int
    parents_without_children: int


@dataclass(frozen=True)
class KeySet:
    year: int
    quarter: int
    release: str
    table: str
    keys: set[tuple[str, ...]]


def compare_keys(parent: KeySet, child: KeySet) -> JoinCounts:
    """Compare child keys against the parent prefix, counting individual children."""
    parent_fields = key_fields(parent.year, parent.quarter, parent.table)
    child_fields = key_fields(child.year, child.quarter, child.table)
    if (parent.year, parent.quarter, parent.release) != (child.year, child.quarter, child.release):
        raise ContractError("Cannot compare different periods or releases")
    if not parent.release.strip() or (parent.table, child.table) not in RELATIONSHIPS:
        raise ContractError("Unsupported relationship or release")
    width = len(parent_fields)
    if child_fields[:width] != parent_fields:
        raise ContractError("Incompatible relationship keys")
    if any(len(key) != width for key in parent.keys) or any(
        len(key) != len(child_fields) for key in child.keys
    ):
        raise ContractError("Incompatible key widths")
    matched = [key for key in child.keys if key[:width] in parent.keys]
    covered = {key[:width] for key in matched}
    return JoinCounts(
        len(parent.keys),
        len(child.keys),
        len(matched),
        len(child.keys) - len(matched),
        len(parent.keys - covered),
    )
