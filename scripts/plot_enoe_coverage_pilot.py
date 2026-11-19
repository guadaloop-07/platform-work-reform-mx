"""Render the reviewed aggregate pilot; requires the locked development dependencies."""

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    report = json.loads(args.report.read_text())
    if report["version"] != "enoe-coverage-pilot-v1":
        raise ValueError("Unsupported pilot version")
    periods = report["periods"]
    fig, ax = plt.subplots(figsize=(10, 5.8), layout="constrained")
    # Unequal calendar spacing preserves the missing 2026 Q1 interval.
    x = [0, 1, 2, 4]
    labels = {"passenger": "Passenger drivers (8342)", "delivery": "Delivery occupations"}
    for name, marker in (("passenger", "o"), ("delivery", "s")):
        values = [p["groups"][name]["imss_percent_all"] for p in periods]
        ax.plot(
            x, [float("nan") if v is None else v for v in values], marker=marker, label=labels[name]
        )
    ax.set(
        xticks=x,
        xticklabels=[p["period"] for p in periods],
        ylim=(0, 25),
        ylabel="Reported principal-job IMSS access (% of occupational screen)",
        title=(
            "ENOE national occupational screens\n"
            "Descriptive estimates; platform work is not identified"
        ),
    )
    ax.grid(axis="y", alpha=0.25)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(loc="upper left", frameon=False)
    fig.supxlabel(
        "Source: reviewed ENOE archives; positive fac_tri, "
        "occupied ages 15+ including age code 98.\n"
        "Unknown/blank answers remain in denominator. "
        "No confidence intervals: precision unvalidated (#42).\n"
        "2025Q2 is not free of anticipation/exposure. Lines connect observed quarters only.",
        fontsize=9,
    )
    fig.savefig(args.report.with_name("coverage.png"), dpi=180)
    fig.savefig(args.report.with_name("coverage.svg"))
    plt.close(fig)


if __name__ == "__main__":
    main()
