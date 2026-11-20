# Historical ENOE Q2–Q3 sample transitions (issue #67)

The fixed 2023–2025 comparison does not show an exceptional positive 2025
informal-to-formal transition rate among the passenger-driver screen. Delivery
occupations show lower forward and higher reverse transition rates. These are
descriptive linked-sample findings, not causal estimates or significance tests.

## Sources and comparability

`enoe_history_sources.json` locks six original INEGI ENOE ZIP releases, their URLs,
SHA-256 hashes, exact table headers, member and dictionary hashes, row counts,
selected catalogue meanings and independent national activity reference totals.
The four 2023/2024 archives were retrieved on 2026-11-20. Originals and generated
artifacts remain outside Git. No historical database ingestion is performed.

All six source totals reconcile independently. Historical Q2 references are
INEGI bulletins 490/23 and 504/24; Q3 references for both 2023 and 2024 come from
the comparison table in bulletin 695/24. Exact URLs and totals are in the source
contracts. The 2025 releases retain their reviewed national references.

Selected meanings of `p3`, `p4a`, `emp_ppal`, `c_res`, `n_ent`, `clase1` and
`clase2` agree across the six releases. Entity is `ent` through 2025 Q2 and
`cve_ent` in 2025 Q3; normalization is explicit. Headers are validated separately
for each release. Historical `tipo=1` is labelled `Entrevista cara a cara`, while
the 2025 catalogue uses `ENOE`; only code 1 enters supported pairs in every year.
This restriction excludes telephone records and is not a claim that survey-mode
composition is constant.

## Fixed method

Apply the [linkage audit](enoe-linkage-audit.md) unchanged to Q2–Q3 in each year:
unique reduced person keys, interview advancement, stable dwelling/design
identifiers, sex, age and available birth-date consistency. Scheduled fifth-
interview exits are separated from unmatched continuing cases. The same eligible
universe and baseline occupational screens are used throughout; follow-up
occupation is unrestricted. Passenger is `p3=8342`; delivery is `8344`, `9321`,
`9722` or `9723`. Narrow passenger additionally requires `p4a=4850`; broad
transport/delivery also includes `8341`. Screens include nonplatform work and
can overlap. The all-eligible sample is context, not an untreated control group.

Forward rates divide informal-to-formal events by all linked baseline informal
people. Reverse rates use all linked baseline formal people. Follow-up
nonemployment and unknown formality remain in the relevant denominators. The
released `emp_ppal` classification concerns the principal job and is not a direct
measure of new platform IMSS affiliation. No national expansion is performed.

For each direction, contrasts compare 2025 with each earlier year and with the
arithmetic mean of the two earlier rates, giving each year equal weight rather
than pooling persons. A value outside two prior observations is only descriptive;
two years do not establish a historical distribution or prediction interval.

## Observed results

| Baseline screen | 2023 informal→formal | 2024 | 2025 | 2025 minus prior mean (pp) |
|---|---:|---:|---:|---:|
| All eligible | 13.12% | 12.63% | 12.17% | -0.71 |
| Passenger | 16.71% | 17.83% | 17.24% | -0.02 |
| Delivery | 15.05% | 11.96% | 10.68% | -2.83 |
| Narrow passenger | 16.52% | 17.42% | 17.06% | +0.09 |
| Broad transport/delivery | 18.24% | 17.65% | 16.99% | -0.95 |

Passenger forward events number 341/2,041, 342/1,918 and 348/2,018. Delivery
events number 96/638, 89/744 and 82/768. Passenger reverse rates are 31.30%,
29.41% and 30.70%; delivery reverse rates are 22.19%, 19.81% and 29.21%
(69/311, 61/308 and 85/291). These directional rates have different denominators
and must not be subtracted to estimate a net population flow.

Retention among continuing baseline passenger cases declines from 91.93% to
91.24% to 90.16%; delivery retention is 90.04%, 91.08% and 89.22%. Sample
composition also varies: women comprise 6.85%, 8.84% and 9.54% of linked delivery
cases; ages 15–29 comprise 41.52%, 45.53% and 42.78%. These are diagnostics, not
evidence that selection is ignorable. Full sex/age/position compositions and
baseline-state-specific linkage statuses are retained in the JSON output.

Requiring complete consistent birth dates yields passenger forward rates of
16.57%, 17.51% and 16.75%, and delivery rates of 14.88%, 11.72% and 10.00%.
Delivery reverse rates remain higher in 2025 (22.15%, 19.23%, 28.79%). Thus the
qualitative pattern survives this stricter linkage sensitivity.

This exercise does not establish absence of a reform effect. Occupational
contamination, panel attrition, changing composition, principal-job measurement
and survey timing can obscure changes in platform affiliation. Longitudinal
weights and survey precision remain unvalidated, including the unresolved
variance-design work in issue #42. There are no p-values, confidence intervals,
claims of statistical anomalies, or estimates of the 1.2 million IMSS additions.

## Reproduction and checks

```sh
uv run --locked python -m platform_work_reform.enoe_history \
  --output-dir artifacts/enoe-historical-transitions
uv run --locked python scripts/plot_enoe_history.py \
  artifacts/enoe-historical-transitions/comparison.json
```

The CLI fails on source/hash/header/key/catalogue mismatches or national total
disagreement. It reproduces the five reviewed 2025 event/denominator counts
before accepting the historical comparison. The completed six-source run passed
these gates. Outputs are aggregate `comparison.json`, `.csv`, `.md`, `.png` and
`.svg`; the JSON retains complete state matrices, retention, source evidence and
birth-date sensitivity. No person-level outputs are written.

Focused tests cover comparison arithmetic, missing values, fixed year/screen
coverage, 2025 parity failures, catalogue contracts and historical header/key
validation. The plotting output was rendered and visually inspected.
