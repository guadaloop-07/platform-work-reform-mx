"""Unweighted principal-employment transitions; no population or precision estimator."""

import csv
from collections import Counter, defaultdict

STATES = (
    "informal",
    "formal",
    "unemployed",
    "inactive",
    "formality_blank",
    "formality_not_applicable",
)


def employment_state(row):
    if not row["eligible"]:
        return "outside_universe"
    activity = row["clase2"]
    if activity == "2":
        return "unemployed"
    if activity in {"3", "4"}:
        return "inactive"
    if activity != "1":
        raise ValueError("Unsupported eligible activity")
    states = {
        "1": "informal",
        "2": "formal",
        "": "formality_blank",
        "0": "formality_not_applicable",
    }
    if row["emp_ppal"] not in states:
        raise ValueError("Invalid occupied emp_ppal")
    return states[row["emp_ppal"]]


def summarize(cells):
    def row_total(state):
        return sum(n for (a, _), n in cells.items() if a == state)

    informal, formal = row_total("informal"), row_total("formal")
    forward, reverse = cells[("informal", "formal")], cells[("formal", "informal")]
    return {
        "linked_n": sum(cells.values()),
        "linked_baseline_informal_n": informal,
        "linked_baseline_formal_n": formal,
        "informal_to_formal_n": forward,
        "formal_to_informal_n": reverse,
        "informal_to_formal_percent": 100 * forward / informal if informal else None,
        "formal_to_informal_percent": 100 * reverse / formal if formal else None,
        "informal_to_nonemployment_n": cells[("informal", "unemployed")]
        + cells[("informal", "inactive")],
    }


class TransitionAudit:
    def __init__(self, names):
        self.cells = {n: Counter() for n in names}
        self.full_birth_cells = {n: Counter() for n in names}
        self.retention = {n: Counter() for n in names}
        self.design = {n: defaultdict(Counter) for n in names}
        self.missing_design = {n: Counter() for n in names}

    def add_baseline(self, row, names, status):
        state = employment_state(row)
        for name in names:
            self.retention[name][(state, status)] += 1

    def add_pair(self, first, second, names, comparable_birth_components):
        cell = (employment_state(first), employment_state(second))
        if "outside_universe" in cell:
            raise ValueError("Transition pairs must be eligible at both endpoints")
        design = tuple(first.get(k, "") for k in ("entity", "est_d_tri", "upm"))
        for name in names:
            self.cells[name][cell] += 1
            if comparable_birth_components == 3:
                self.full_birth_cells[name][cell] += 1
            if all(design):
                self.design[name][cell][design] += 1
            else:
                self.missing_design[name][cell] += 1

    def report(self):
        groups = {}
        for name, cells in self.cells.items():
            matrix = []
            for a in STATES:
                for b in STATES:
                    cell = (a, b)
                    design = self.design[name][cell]
                    matrix.append(
                        {
                            "baseline_state": a,
                            "followup_state": b,
                            "sample_n": cells[cell],
                            "full_birth_sample_n": self.full_birth_cells[name][cell],
                            "baseline_strata_with_events": len({key[:2] for key in design}),
                            "baseline_upms_with_events": len(design),
                            "largest_upm_event_n": max(design.values(), default=0),
                            "missing_baseline_design_n": self.missing_design[name][cell],
                        }
                    )
            groups[name] = {
                "summary": summarize(cells),
                "full_birth_sensitivity": summarize(self.full_birth_cells[name]),
                "matrix": matrix,
                "baseline_retention": [
                    {"baseline_state": state, "linkage_status": status, "sample_n": n}
                    for (state, status), n in sorted(self.retention[name].items())
                ],
            }
        return {
            "weighted": False,
            "national_estimates_validated": False,
            "precision_validated": False,
            "denominator": (
                "Linked baseline state, including follow-up nonemployment and unknown formality."
            ),
            "design_support_note": (
                "Event UPM/stratum counts are descriptive support only, "
                "not design degrees of freedom, SEs or validated effective sample sizes."
            ),
            "groups": groups,
        }


def write_transitions(output, report):
    groups = report["sample_transitions"]["groups"]
    rows = [{"screen": name, **row} for name, g in groups.items() for row in g["matrix"]]
    with (output / "transitions.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    lines = [
        "# ENOE 2025 Q2–Q3 sample transitions",
        "",
        "Consistency-supported eligible TIPO=1 pairs. Released principal-job emp_ppal. "
        "Counts and rates are unweighted sample descriptions, not national estimates.",
        "",
        "| Baseline screen | Linked pairs | Informal in Q2 | Informal to formal | "
        "% of linked informal | "
        "Formal in Q2 | Formal to informal | % of linked formal |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for name, g in groups.items():
        s = g["summary"]
        rates = [
            "NA" if s[k] is None else f"{s[k]:.2f}"
            for k in ("informal_to_formal_percent", "formal_to_informal_percent")
        ]
        lines.append(
            f"| {name} | {s['linked_n']:,} | {s['linked_baseline_informal_n']:,} | "
            f"{s['informal_to_formal_n']:,} | {rates[0]} | {s['linked_baseline_formal_n']:,} | "
            f"{s['formal_to_informal_n']:,} | {rates[1]} |"
        )
    lines += [
        "",
        "Follow-up unemployment/inactivity and blank/not-applicable formality remain explicit "
        "in transitions.csv and matrices in linkage.json; "
        "occupation continuity is not required. "
        "Full-birth-date sensitivity and baseline-state retention are in linkage.json. "
        "Event UPM/stratum counts do not validate precision. No longitudinal weights, national "
        "totals, confidence intervals, p-values, platform identifiers "
        "or causal effects are supplied.",
        "",
    ]
    (output / "transitions.md").write_text("\n".join(lines))
