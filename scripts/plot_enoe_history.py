"""Render fixed historical sample rates from the audited comparison JSON."""

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
    if report["version"] != "enoe-historical-transitions-v1":
        raise ValueError("Unsupported comparison version")
    indexed = {(r["year"], r["screen"]): r for r in report["summary"]}
    fig, axes = plt.subplots(1, 2, figsize=(11, 5.8), layout="constrained")
    years = [2023, 2024, 2025]
    for ax, metric, title in zip(
        axes,
        ("informal_to_formal_percent", "formal_to_informal_percent"),
        ("Informal to formal", "Formal to informal"),
        strict=True,
    ):
        for name, label, marker in (
            ("passenger", "Passenger drivers", "o"),
            ("delivery", "Delivery occupations", "s"),
        ):
            values = [indexed[(y, name)][metric] for y in years]
            ax.plot(
                years,
                [float("nan") if v is None else v for v in values],
                marker=marker,
                label=label,
            )
            for y, v in zip(years, values, strict=True):
                if v is not None:
                    ax.annotate(
                        f"{v:.2f}%",
                        (y, v),
                        xytext=(0, 9 if name == "passenger" else -16),
                        textcoords="offset points",
                        ha="center",
                        fontsize=10,
                    )
        ax.set(
            title=title, xticks=years, xlabel="Year (Q2 to Q3)", ylabel="Unweighted sample rate (%)"
        )
        ax.set_ylim(
            0,
            max(
                40,
                max(indexed[(y, n)][metric] or 0 for y in years for n in ("passenger", "delivery"))
                * 1.25,
            ),
        )
        ax.margins(x=0.15)
        ax.grid(axis="y", alpha=0.25)
        ax.spines[["top", "right"]].set_visible(False)
    axes[0].legend(loc="upper left", frameon=False)
    fig.suptitle(
        "ENOE linked-sample employment transitions\nFixed baseline occupational screens, 2023–2025"
    )
    fig.supxlabel(
        "Source: six reviewed original ENOE releases. "
        "TIPO=1; consistent eligible pairs; emp_ppal.\n"
        "Each direction has its own baseline-state denominator, "
        "including follow-up nonemployment.\n"
        "No population weights, confidence intervals or causal estimates. "
        "Two prior years do not establish a historical distribution.",
        fontsize=9,
    )
    fig.savefig(args.report.with_name("comparison.png"), dpi=180)
    fig.savefig(args.report.with_name("comparison.svg"))
    plt.close(fig)


if __name__ == "__main__":
    main()
