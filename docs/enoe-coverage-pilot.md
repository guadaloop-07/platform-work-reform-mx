# National ENOE occupational-screen coverage pilot

Issue #63. Current version `enoe-coverage-pilot-v2`. This is a descriptive repeated-cross-section
pilot, not an effect estimator, platform prevalence estimate, individual transition
study or IMSS–ENOE linkage. It implements the measurement subset feasible before
issue #42 resolves precision. No confidence intervals, p-values or significance
claims are emitted. No automatic comparison/control population is selected.

## Frozen population and screens

Use the reviewed national occupied population, ages 15–98, including documented
unspecified adult age code 98, positive integer `fac_tri`, completed resident
interviews and valid activity pairs under the existing preparation contract.
Use the release-specific interview code (`00` for 2025 Q4). Select exactly one
explicit reviewed run and unchanged original archive for each of 2025 Q2/Q3/Q4
and 2026 Q2. The manifest is local and ignored, never an implicit latest run.

The rules below are fixed from catalogue evidence in issue #61 / PR #62, before
examining coverage outcomes. That PR remains a separate review dependency; this
implementation does not merge it or import its unmerged module. The CLI checks
original archive hashes, headers, exact person keys, row counts, source catalogue
membership for occupied `p3`, `p4a`, `p6d`, `emp_ppal`, and national reconciliation against
existing prepared runs. Selected catalogue hashes accompany each result.
The CLI directly reads original selected fields; it does not independently
fingerprint their staged values (the separate #61 audit does).

| Screen | Rule | Interpretation |
|---|---|---|
| Passenger | `p3=8342` | Includes bus, van, taxi and car passenger drivers, not just apps. |
| Delivery | `p3` in 8344, 9321, 9722, 9723 | Motorcycle, bicycle and pedestrian delivery-related occupations; includes nonplatform work. |
| Narrow passenger sensitivity | `p3=8342` and `p4a=4850` | Land passenger transport; still not an app identifier. |
| Broad sensitivity | Passenger/delivery union plus `p3=8341` | Includes freight drivers; scope sensitivity, not an upper bound. |

Screens overlap and must not be summed. A delivery activity restriction is not
imposed: delivery can be classified in restaurants or commerce. Neither health
access nor employment position defines screen membership. Unknown/blank occupations
and absent COE1 have explicit occupied-population flow counts and weights. Other
occupations are excluded from screens, not assigned to a causal control group.
Principal-job screens miss secondary platform work. Foreign-work observations
are retained and counted; no full secondary-work or routing reconstruction is
claimed. The 2026 instrument/routing evidence remains incomplete.

## Outcomes, denominators and composition

The numerator is `p6d=1`, reported IMSS medical access through the principal job.
It does not establish administrative registration, complete insurance benefits,
utilization, prior informality or platform-specific coverage. Values 2–6 are known
non-IMSS responses; 9 is unknown, blank is routing unresolved and absent COE2 is
separate. Invalid nonblank medical codes fail. Unknown values never become code 6.

`imss_percent_all` divides the weighted numerator by all screen members: this is
the share reporting IMSS access, not an assumption that every unknown lacks it.
`imss_percent_known` restricts the denominator to codes 1–6 as a response-sensitivity
analysis; missingness selection may bias it. Empty denominators return NULL,
not zero. JSON retains weighted and sample state counts, foreign-work counts,
and weighted composition by sex, age band, original `anios_esc`, `pos_ocu`, `t_tra`.
Original codes and unspecified states are retained; these descriptors are not
newly validated reconstructions. Compare distributions before interpreting change.

The original same-quarter contrast is 2026 Q2 minus 2025 Q2, in percentage points. Intermediate
2025 Q3/Q4 points are displayed; 2026 Q1 is unavailable, not interpolated as data.
The baseline follows the reform announcement and partially overlaps legal
implementation. One baseline cannot establish pre-trends; season matching does
not identify causality. Repeated cross-sections do not identify individual changes.

## Reproduction

With the configured local database and reviewed original archives available:

```bash
uv run --locked python -m platform_work_reform.enoe_coverage_pilot \
  artifacts/enoe-quarter-manifest.json --output-dir artifacts/enoe-coverage-pilot
uv run --locked python scripts/plot_enoe_coverage_pilot.py \
  artifacts/enoe-coverage-pilot/coverage.json
```

The command writes aggregate JSON/CSV only after all periods reconcile. Plotting
uses locked development dependencies and writes PNG/SVG alongside the report.
Outputs and originals remain outside Git. Every period retains archive/run/hash
provenance. Latin-1 is only reversible byte transport before strict ASCII checks
on selected codes; no free-text decoding or source repair is performed.

Before inferential release, resolve #42's variance population/singleton rules,
validate target-domain precision, and account for rotating-panel covariance in
cross-quarter changes. Do not assume independent quarterly samples. Expanding
pre-announcement periods, validating instruments and defining a substantively
credible comparison are separate tasks before causal evaluation. The confidential
longitudinal study remains the proposed EconLab collaboration.

## Original v1 local operational results (2026-11-19)

All four original archives passed before/after hash checks and national
source/preparation count and weight reconciliation. Original selected catalogue
keys were checked separately. These empirical executions are distinct from the
synthetic behavior tests. The weighted occupied-population totals are 59,440,760;
59,533,449; 59,785,854; and 60,040,094 respectively. Unspecified/blank occupation
counts were 251, 255, 236 and 170; no occupied COE1 was absent in these runs.

| Screen | 2025 Q2 sample | 2026 Q2 sample | 2025 Q2 reporting IMSS (%) | 2026 Q2 reporting IMSS (%) | Change (pp) |
|---|---:|---:|---:|---:|---:|
| Passenger | 4,344 | 4,377 | 14.49 | 13.88 | -0.60 |
| Delivery | 1,633 | 1,616 | 16.73 | 14.78 | -1.95 |
| Narrow passenger | 3,962 | 3,984 | 10.72 | 10.46 | -0.26 |
| Broad including freight | 10,075 | 10,034 | 32.58 | 32.28 | -0.31 |

Rates use the full screen denominator. Restricting to known medical responses
produces changes of -0.59, -1.99, -0.24 and -0.42 percentage points respectively.
These are descriptive changes, not significant decreases or negative reform
effects. No platform-specific effect or absence of effect follows from them.

Composition also changes: the weighted own-account share in the passenger
screen rises from 30.60% to 36.55%; the female share in the delivery screen rises
from 8.30% to 9.81%. These unadjusted descriptors do not establish individual
transitions or causal composition effects. They reinforce the need to inspect
population definitions and composition before interpreting coverage differences.

Outputs are ignored at `artifacts/enoe-coverage-pilot/coverage.json`,
`coverage.csv`, `coverage.png` and `coverage.svg`. The PNG was inspected for
labels, clipping, period spacing and agreement with JSON/CSV. The figure uses
a zero baseline and 0–25% range, and marks only the two core occupational screens.

Validation: `just check` passed 122 unit tests; `just db-test` passed 32 isolated
integration tests, with one optional original-source check skipped. Twelve new
synthetic tests cover screen definitions, missingness, denominators, weights,
period-specific universe handling and rejected duplicate manifests. No new
migration or database mutation was introduced.

## Immediate 2025 Q2–Q3 extension

Version 2 adds the short-window diagnostic requested separately from the original
same-quarter comparison. It uses the same fixed occupational screens, population,
weights, provenance and read-only source/preparation gates. No outcome-dependent
screen selection is performed. It uses released `emp_ppal`, not a reconstructed
informality algorithm: code 1 is informal principal employment, 2 formal, 0 not
applicable and blank unresolved. Nonblank values must belong to the actual source
catalogue, and other codes fail. Every group's formality partition is retained in
sample and weighted counts; the corresponding medical-access partition is separate.
IMSS access is not used to overwrite the released formality classification.

The immediate table reports total occupied people, formal employment, informal
employment and reported principal-job IMSS access for 2025 Q2 and Q3. For each
measure it retains unweighted sample counts, weighted counts, count changes,
shares of all screen members and percentage-point changes. Missing/not-applicable
formality states have their own exported rows and remain in denominators.
IMSS access overlaps employment categories and must not be added to them.
A growing covered count can coexist with a declining coverage share.

```bash
uv run --locked python -m platform_work_reform.enoe_coverage_pilot \
  artifacts/enoe-quarter-manifest.json --window immediate \
  --output-dir artifacts/enoe-immediate-pilot
uv run --locked python scripts/plot_enoe_coverage_pilot.py \
  artifacts/enoe-immediate-pilot/coverage.json --immediate
```

The immediate window accepts a manifest with exactly Q2/Q3 2025, or the existing
four-quarter manifest and explicitly selects those two entries. Missing periods,
duplicate periods or run IDs and unsupported extra periods fail before data access.
The default `--window all` preserves the four-quarter workflow and additionally
computes the immediate contrast. Each invocation emits a new versioned JSON;
prior v1 artifacts are not silently treated as v2.

Outputs `immediate.csv` and `immediate.md` contain the changes and readable table;
`coverage.json` retains full provenance, formality and medical partitions,
composition and flow counts. The original `coverage.csv` keeps its existing
coverage columns. The plot option renders immediate PNG/SVG count and share
changes for the two core screens. Generated files stay ignored.

A formal increase with an informal decrease and relatively stable occupation
is compatible with a formalization signal, but does not identify a reform effect
or individual transitions. The short comparison has no seasonal correction,
2024 benchmark, credible control population or validated survey precision.
Q2 is not wholly unexposed; no universal stability threshold is invented.
No hypothesis test or automated declaration of success is generated. Expanding
to 2024 and resolving #42 require subsequent work regardless of the sign observed.

### Immediate-window empirical execution (2026-11-19)

Both original 2025 archives passed before/after hash, catalogue-membership and
national source/preparation reconciliation. The eight group/quarter formality
partitions reconcile in sample and weighted counts. No blank or not-applicable
`emp_ppal` was observed within these screens. This statement is restricted to
these sources and populations. No individual transition is inferred.

| Screen | Occupied change | Formal change | Informal change | IMSS access change | Formal share change (pp) | IMSS share change (pp) |
|---|---:|---:|---:|---:|---:|---:|
| Passenger | -14,923 | +19,663 | -34,586 | -7,016 | +1.72 | -0.35 |
| Delivery | +40,500 | -4,125 | +44,625 | -71 | -2.98 | -1.34 |
| Narrow passenger | +9,968 | +37,874 | -27,906 | +12,176 | +2.73 | +0.85 |
| Broad including freight | -7,310 | +4,003 | -11,313 | -25,983 | +0.22 | -0.75 |

The narrow passenger screen has a descriptive pattern compatible with more formal
principal employment and reported IMSS access. It is not robust across the other
screens: the core passenger group has rising formality but declining IMSS access;
delivery has rising informal employment and almost unchanged IMSS-access counts.
In delivery, the declining IMSS share partly reflects expansion of the denominator.
No classification is selected after viewing these outcomes. The narrow screen is
an existing sensitivity scenario, not a newly identified platform population.
Seasonality, sample composition and sampling variability remain unresolved; no
causal or statistically significant formalization effect is established.

The formal/informal classification and IMSS medical access measure distinct
concepts, so their changes need not coincide. These results do not reconcile the
million-plus administrative registrations with unique people or new full coverage.
The proposed seasonal benchmark using 2024 is not implemented in this minimal
step; it requires separate reviewed inputs and remains a next design task.

The readable complete table is ignored at
`artifacts/enoe-immediate-pilot/immediate.md`, with matching CSV and JSON.
The final `immediate.png` was visually checked against those values. Validation:
`just check` passed 127 unit tests and shared hooks; `just db-test` passed 32
isolated integration tests, with one optional original-source check skipped.
Five additional tests cover formality partitioning, distinct medical/formality
classification, growing counts with declining shares, short manifests and empty
denominators. No migration or database write was added.
