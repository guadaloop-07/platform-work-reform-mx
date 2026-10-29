"""Pre-ingestion checks for the documented 2025 Q3 ENOE join keys.

These checks are not a complete CSV layout or a substitute for reconciliation.
"""

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass


class ContractError(ValueError):
    """An input is outside the documented contract or has invalid keys."""


DWELLING = ("tipo", "mes_cal", "cd_a", "cve_ent", "con", "v_sel")
HOUSEHOLD = (*DWELLING, "n_hog", "h_mud")
PERSON = (*HOUSEHOLD, "n_ren")
KEYS = {"VIV": DWELLING, "HOG": HOUSEHOLD, "SDEM": PERSON, "COE1": PERSON, "COE2": PERSON}


def key_fields(year: int, quarter: int, table: str) -> tuple[str, ...]:
    """Return fields only for the period whose published dictionary was reviewed."""
    if (year, quarter) != (2025, 3) or table not in KEYS:
        raise ContractError("Unsupported ENOE period or table")
    return KEYS[table]


def validate_header(year: int, quarter: int, table: str, header: Sequence[str]) -> None:
    """Check key presence, not the complete source layout or column types."""
    fields = key_fields(year, quarter, table)
    if len(header) != len(set(header)):
        raise ContractError("Duplicate column names")
    missing = set(fields) - set(header)
    if missing:
        raise ContractError(f"Missing key fields: {', '.join(sorted(missing))}")


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


def compare_keys(parent: set[tuple[str, ...]], child: set[tuple[str, ...]]) -> JoinCounts:
    """Compare child keys against the parent prefix, counting individual children."""
    if not parent:
        return JoinCounts(0, len(child), 0, len(child), 0)
    width = len(next(iter(parent)))
    if (
        not width
        or any(len(key) != width for key in parent)
        or any(len(key) < width for key in child)
    ):
        raise ContractError("Incompatible key widths")
    matched = [key for key in child if key[:width] in parent]
    covered = {key[:width] for key in matched}
    return JoinCounts(
        len(parent), len(child), len(matched), len(child) - len(matched), len(parent - covered)
    )
