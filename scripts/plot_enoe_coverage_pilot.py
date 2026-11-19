"""Render the reviewed aggregate pilot; requires the locked development dependencies."""

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import FuncFormatter, MaxNLocator  # noqa: E402


def plot_immediate(report, output):
    rows = report["immediate_changes"]
    fig, axes = plt.subplots(2, 2, figsize=(11, 7.5), layout="constrained")
    for i, (group, title) in enumerate(
        (("passenger", "Passenger drivers"), ("delivery", "Delivery occupations"))
    ):
        selected = {r["metric"]: r for r in rows if r["group"] == group}
        for j, (metric_keys, value_key, unit) in enumerate(
            (
                (("occupied", "formal", "informal", "imss"), "change_weighted", "Weighted people"),
                (("formal", "informal", "imss"), "change_pp", "Percentage points"),
            )
        ):
            values = [selected[k][value_key] for k in metric_keys]
            ax = axes[i, j]
            labels = {
                "occupied": "Occupied",
                "formal": "Formal",
                "informal": "Informal",
                "imss": "IMSS access",
            }
            bars = ax.barh(
                [labels[k] for k in metric_keys],
                [float("nan") if v is None else v for v in values],
                color="#386b9c",
            )
            ax.axvline(0, color="#333333", linewidth=0.8)
            ax.bar_label(
                bars,
                labels=[
                    "NA" if v is None else f"{v:+,.0f}" if j == 0 else f"{v:+.2f}" for v in values
                ],
                padding=4,
            )
            ax.invert_yaxis()
            if j == 0:
                ax.set_xlim(-60000, 60000)
                ax.xaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value / 1000:g}"))
                unit = "Weighted people (thousands)"
            else:
                ax.set_xlim(-4, 4)
            ax.xaxis.set_major_locator(MaxNLocator(nbins=5))
            ax.set(title=title, xlabel=unit)
            ax.spines[["top", "right"]].set_visible(False)
    fig.suptitle("ENOE 2025 Q3 minus Q2\nDescriptive occupational-screen changes")
    fig.supxlabel(
        "Source: reviewed ENOE archives; occupied ages 15+, positive fac_tri. "
        "Formal/informal: emp_ppal; IMSS: p6d=1.\n"
        "Shares use all screen members. IMSS overlaps employment categories. "
        "No platform identifier, causal effects or validated precision (#42).",
        fontsize=9,
    )
    fig.savefig(output / "immediate.png", dpi=180)
    fig.savefig(output / "immediate.svg")
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("--immediate", action="store_true")
    args = parser.parse_args()
    report = json.loads(args.report.read_text())
    if report["version"] not in {"enoe-coverage-pilot-v1", "enoe-coverage-pilot-v2"}:
        raise ValueError("Unsupported pilot version")
    if args.immediate:
        plot_immediate(report, args.report.parent)
        return
    periods = report["periods"]
    fig, ax = plt.subplots(figsize=(10, 5.8), layout="constrained")
    # Unequal calendar spacing preserves the missing 2026 Q1 interval.
    x = [(int(p["period"][:4]) - 2025) * 4 + int(p["period"][-1]) - 2 for p in periods]
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
