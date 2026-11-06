"""Explicit reviewed non-pilot releases; original field names remain source-specific."""

import json
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def releases() -> dict:
    return json.loads(Path(__file__).with_name("enoe_releases.json").read_text())


def release(year: int, quarter: int) -> dict:
    try:
        return releases()[f"{year}q{quarter}"]
    except KeyError as error:
        raise ValueError("Unsupported ENOE period") from error
