"""Ultimate-cluster formulas; callers must establish the complete supported design."""

from collections import defaultdict
from dataclasses import dataclass
from math import fsum, isfinite, sqrt
from statistics import NormalDist
from typing import Literal


@dataclass(frozen=True)
class UPMTotal:
    """Already weighted totals for one entity/stratum/UPM, including domain zeros."""

    entity: str
    stratum: str
    upm: str
    x: float
    y: float = 0.0


@dataclass(frozen=True)
class Estimate:
    value: float
    variance: float


def estimate(upms: list[UPMTotal], *, kind: Literal["total", "ratio"]) -> Estimate:
    """Apply section 3.9 without collapsing strata or correcting singleton UPMs."""
    if kind not in {"total", "ratio"} or not upms:
        raise ValueError("Specify a supported estimator and nonempty complete UPM support")
    groups = defaultdict(list)
    seen = set()
    for row in upms:
        key = (row.entity, row.stratum, row.upm)
        if any(not isinstance(code, str) or not code.strip() for code in key) or key in seen:
            raise ValueError("Missing or duplicate nested UPM key")
        if not isfinite(row.x) or not isfinite(row.y) or row.y < 0:
            raise ValueError("UPM totals must be finite and denominator totals nonnegative")
        seen.add(key)
        groups[key[:2]].append(row)
    if any(len(rows) < 2 for rows in groups.values()):
        raise ValueError("Singleton stratum: no supported variance policy supplied")
    try:
        x = fsum(row.x for row in upms)
        y = fsum(row.y for row in upms) if kind == "ratio" else 1.0
        if y <= 0:
            raise ValueError("Ratio denominator must be positive")
        value = x / y
        contributions = []
        for rows in groups.values():
            residuals = [row.x - value * row.y if kind == "ratio" else row.x for row in rows]
            mean = fsum(residuals) / len(rows)
            contributions.append(
                len(rows) / (len(rows) - 1) * fsum((z - mean) ** 2 for z in residuals)
            )
        # Divide twice to avoid overflow from explicitly squaring a large denominator.
        variance = fsum(contributions) / y / y
    except (OverflowError, ZeroDivisionError) as error:
        raise ValueError("Numerical overflow in variance calculation") from error
    if not isfinite(value) or not isfinite(variance):
        raise ValueError("Nonfinite variance result")
    return Estimate(value, variance)


def normal_summary(
    result: Estimate, *, confidence: float, critical_decimals: int | None = None
) -> dict:
    """Normal Wald interval with explicit level and optional documented z rounding."""
    if not isfinite(confidence) or not 0 < confidence < 1:
        raise ValueError("Confidence must be a finite fraction strictly between zero and one")
    if not isfinite(result.value) or not isfinite(result.variance) or result.variance < 0:
        raise ValueError("Estimate and nonnegative variance must be finite")
    probability = 0.5 + confidence / 2
    if not 0.5 < probability < 1:
        raise ValueError("Confidence level exceeds supported floating-point resolution")
    standard_error = sqrt(result.variance)
    unrounded_critical = NormalDist().inv_cdf(probability)
    if critical_decimals is not None and (
        type(critical_decimals) is not int or not 0 <= critical_decimals <= 12
    ):
        raise ValueError("Critical-value decimals must be an integer between zero and twelve")
    critical = (
        round(unrounded_critical, critical_decimals)
        if critical_decimals is not None
        else unrounded_critical
    )
    if critical <= 0:
        raise ValueError("Rounded critical value must be positive")
    margin = critical * standard_error
    lower, upper = result.value - margin, result.value + margin
    if not isfinite(lower) or not isfinite(upper):
        raise ValueError("Nonfinite confidence interval")
    cv = standard_error / result.value if result.value > 0 else None
    if cv is not None and not isfinite(cv):
        raise ValueError("Nonfinite coefficient of variation")
    return {
        "estimate": result.value,
        "variance": result.variance,
        "standard_error": standard_error,
        "cv_fraction": cv,
        "confidence_level": confidence,
        "critical_distribution": "standard_normal",
        "critical_value": critical,
        "unrounded_critical_value": unrounded_critical,
        "critical_rounding_decimals": critical_decimals,
        "interval": [lower, upper],
    }
