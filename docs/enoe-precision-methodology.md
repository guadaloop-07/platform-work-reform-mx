# ENOE precision: verified formulas and outstanding design decisions

This note advances issue #42. The calculation kernel is tested on synthetic
supported designs; national ENOE 2025 Q3 precision remains unvalidated. No
production confidence interval is released by this change.

## Sources and confidence-interval finding

INEGI, *Cómo se hace la ENOE. Métodos y procedimientos* (2023),
[section 3.9, PDF pages 64–65, printed pages 56–57](https://www.inegi.org.mx/contenidos/productos/prod_serv/contenidos/espanol/bvinegi/productos/nueva_estruc/889463909743.pdf#page=64),
specifies ultimate-cluster variance, Taylor linearization for ratios, and a
normal-quantile confidence interval. For weighted UPM totals x and y, within
entity e and stratum h, write k for the number of UPMs and bars for their means:

```text
V(total X) = sum_eh [k/(k-1) * sum_i (x_ehi - mean_eh(x))^2]
R = X/Y
V(R) = sum_eh [k/(k-1) * sum_i
              ((x_ehi - mean_eh(x)) - R*(y_ehi - mean_eh(y)))^2] / Y^2
SE = sqrt(V)
CV = SE / estimate
CI = estimate +/- z_(1-alpha/2) * SE; confidence = 1-alpha
```

The cited interval uses z, not a Student-t critical value. The displayed formula
leaves alpha symbolic: it does not by itself establish a 90% or 95% default for
2025 Q3. At k=1 the variance formula is undefined, including when the centered
contribution is zero. Section 3.9 does not supply a singleton-stratum policy.

Reviewed copy SHA-256:
`a6d32efec3c69b3955803f50f78c18ffbb62b84048194bd08dd4ede98d51ca46`.
The relevant formula pages were visually inspected on 2026-11-04. This digest
identifies the downloaded copy; it is not an independently published checksum.

## Quarterly field mapping and historical collapse precedent

The [2025 data structure, SDEM table, printed page 15](https://www.inegi.org.mx/contenidos/programas/enoe/15ymas/doc/enoe_325_fd_c_bas_amp.pdf#page=16)
labels `EST_D_TRI` as the quarterly design stratum and `UPM` as the primary
sampling unit. The released CSV uses lowercase names and `cve_ent`. The pilot
therefore audits `(cve_ent, est_d_tri)` and nested `upm`, preserving raw code
strings. These labels support the mapping, but do not establish whether a
separate variance pseudo-stratum mapping is required for the 23 singleton cases.

INEGI, *Encuesta Nacional de Ocupación y Empleo. Nueva edición. ENOE N.
Diseño muestral* (2021),
[section 6.1, PDF page 5, printed page 2](https://www.inegi.org.mx/contenidos/programas/enoe/15ymas/doc/enoe_n_diseno_muestral.pdf#page=5),
describes collapsing strata into pseudo-strata and adjusting expansion factors
in the pandemic-era subsample. This is a historical precedent, not evidence of
the operational 2025 Q3 variance mapping. Do not reconstruct pseudo-strata by
numeric code proximity, or apply another adjustment to published `fac_tri`,
without period-specific support. The reviewed historical copy has SHA-256
`42eaa300fcbd4bec98c2a38f3edb5912bcc2208fe69a54a0c1103b75a85dbd09`.

## Public-source investigation: current collapse evidence

The public-source review on 2026-11-04 found evidence beyond the 2021
pandemic-era precedent. The
[ENOE 2025 RNM metadata, Muestreo / Factores de expansión](https://www.inegi.org.mx/rnm/index.php/catalog/1121),
explicitly includes stratum collapse among expansion-factor adjustments,
alongside nonresponse and population adjustment. Therefore, it would be
incorrect to describe collapse as documented only for ENOEN 2021. This statement
does not identify which strata were collapsed in 2025 Q3, supply a crosswalk,
or specify a singleton variance policy. Weight adjustment and variance-stratum
assignment are separate implementation questions.

The same metadata describes a Census-2020-based master frame, while the 2023
methods document section 3.2, printed pages 42–43, describes the 2012 master
sample based on Census 2010. This documentary difference requires version
reconciliation; it does not establish the date or implementation of a frame
transition in our reviewed archive, or explain the observed singleton strata.

The [SDEMT325 EST_D_TRI variable record](https://www.inegi.org.mx/rnm/index.php/catalog/1121/variable/F47/V5875?name=EST_D_TRI)
defines the quarterly design-stratum number for sampled dwellings. The
[UPM record](https://www.inegi.org.mx/rnm/index.php/catalog/1121/variable/F47/V5883?name=UPM)
defines geographic primary sampling units. Neither inspected record supplies a
variance pseudo-stratum correspondence or a singleton exception.

The 2025 [related-materials catalog](https://www.inegi.org.mx/rnm/index.php/catalog/1121/related-materials)
links an older *Cómo se hace la ENOE* edition, UPC 702825190613. Its
[2020 section 3.8, printed pages 47–48 / PDF pages 56–57](https://www.inegi.org.mx/contenidos/productos/prod_serv/contenidos/espanol/bvinegi/productos/nueva_estruc/702825190613.pdf#page=56)
describes nonresponse and population-projection adjustment. Its section 3.11,
printed page 54 / PDF page 63, repeats the ultimate-cluster variance structure
with k/(k-1), without resolving k=1. The downloaded 2020 copy has SHA-256
`abfb9998797e4f0ff4a14a692c47a7a631b0ad08e03c101fa952f40c5148f908`.
The relevant formula pages were visually inspected. A metadata link to this
older edition does not settle current operational details.

The review covered the 2023 statistical-design chapter and production sections,
2020 adjustment/variance sections, 2021 ENOEN design, 2025 RNM sampling and
processing metadata, related materials and SDEMT325 variable definitions.
Targeted searches on INEGI for collapse, pseudo-strata, singleton UPMs and
variance code did not locate an executable 2025 Q3 mapping or correction in
these materials. This is a bounded search result, not proof that no public
file exists. Methods documented for other INEGI surveys or municipality-level
small-area models do not establish an ENOE national variance policy.

The next empirical check should characterize the singleton strata using
publicly documented dimensions and evaluate justified sensitivity scenarios
against official SEs. Agreement with a reference alone cannot identify an
unpublished mapping. Preserve published `fac_tri`; do not apply a second
collapse/weight adjustment or claim official replication on this evidence.

## Implemented calculation contract

`platform_work_reform.survey_variance` accepts already weighted totals for every
UPM in an explicitly supplied design, including zeros outside a domain. It does
not select a frame, derive weights, assign domain membership or validate that
the caller supplied every sampled UPM. Do not filter UPMs solely because they
lack domain members. Independent strata are summed within entity nesting.

The kernel rejects duplicate or missing nested UPM keys, empty support,
nonfinite values, singleton strata, negative denominator totals, nonpositive
ratio denominators and numerical overflow. It has no collapse, certainty,
centering or singleton-dropping option. A singleton with all-zero outcomes also
fails; zero outcomes do not justify a variance policy.

`normal_summary` requires an explicit confidence fraction in (0, 1). It returns
the estimate, variance, standard error, CV fraction, normal critical value and
unrounded interval bounds. An optional `critical_decimals` argument explicitly
rounds the normal critical value; its default is no rounding. Both used and
unrounded critical values are retained. CV is undefined here for nonpositive estimates and is
returned as `None`. Intervals are not clipped to zero or to probability bounds.
Multiplying a ratio by 100 requires multiplying its SE by 100 and variance by
10,000. The kernel does not compute DEFF, finite-population corrections or
Student-t intervals. No variance degrees of freedom are silently used to
replace the documented normal critical value.

Tests include manually calculated two-stratum totals and ratios, zero-domain
UPMs, known 90% and 95% normal quantiles, percentage scaling, and an independent
exact-rational pairwise identity for strata with more than two UPMs:

```text
k/(k-1) * sum_i (z_i-mean(z))^2
  = sum_(i<j) (z_i-z_j)^2 / (k-1)
```

This checks implementation arithmetic, not agreement with official national
precision. A trusted independent survey package or official published precision
comparison is still required for the real pilot.

## Verified 2025 Q3 reference interval convention

The [official precision workbook](https://www.inegi.org.mx/rnm/index.php/catalog/1121/download/36732),
reviewed on 2026-11-04, identifies ENOE, 2025, quarter III and version
`Definitivo`. In sheet `INDICADORES`, `S1` is `Niv_Conf`; `S2:S5` are 90.
Rows 2–5 cover the national 15-plus population total, PEA total, unemployed total
and unemployment rate. They do not include all the pilot's indicators.

The serialized reference copy has SHA-256
`d61aa638cde782555f77ce2ed55cd073a7d49b59a23bec4a46caa0a40095e099`.
It remains outside Git and is never edited or re-exported.

| INDICADORES row | Reference estimate (P) | Standard error (R) | Confidence percent (S) |
|---|---:|---:|---:|
| 2: population 15-plus | 103,068,355 | 451,490.91620239 | 90 |
| 3: PEA | 61,303,255 | 306,550.707406891 | 90 |
| 4: unemployed | 1,769,806 | 42,307.9080948901 | 90 |
| 5: unemployment rate, percentage points | 2.887 | 0.06750613 | 90 |

For these four rows, the published bounds (`T:U`) are consistent with a
multiplier of **1.645**, rather than the full normal quantile
1.6448536269514722. This rounding convention is inferred from the published
arithmetic, not stated as a universal INEGI rule. Request `confidence=0.90` and
`critical_decimals=3` to reproduce that convention. Using the full normal
quantile can cause small differences in bounds even with the correct SE.

```bash
uv run --locked python -m platform_work_reform.enoe_precision_reference \
  /path/to/reviewed-2025q3-precision.xlsx
```

The reference verifier checks the exact workbook hash, headers, national domain,
period, variable and confidence-level cells. It compares bounds calculated from
the **published** estimates and SEs against published bounds, allowing 0.000001
person for totals and 0.0000005 percentage point for the six-decimal rate
bounds. All four rows pass. These tolerances address the reference's serialized
precision and floating-point arithmetic; future comparisons with computed SEs
must separately account for the published input precision.

This verifies interval arithmetic only: it does not reproduce these SEs from
microdata or validate our sampling variance. The workbook CV is expressed in
percent, while the kernel returns a fraction. Published rate inputs are rounded,
so the helper reports CV without claiming an independent CV reconciliation.

## Original-source support verification

```bash
uv run --locked python -m platform_work_reform.enoe_source_support \
  data/enoe/official/2025q3/enoe-2025q3-official.zip \
  --run-id fe197954-1c2d-4880-8bf5-16b2fa432905
```

Without `--run-id`, only the original archive is examined. The verifier checks
the reviewed archive hash before and after reading, VIV/HOG/SDEM member hashes,
ordered headers, row widths, row counts and design keys. It compares nested UPM
support across source tables. Only aggregates and hashes are emitted.

With a run, it additionally requires the reviewed successful staged load and
compares SDEM group diagnostics, weighted totals and a SHA-256 fingerprint of
the ordered selected fields. The v2 staged audit orders by original SDEM row
number. Each fingerprint record is a JSON array of the ASCII, whitespace-trimmed
logical values in `enoe_design_support.FIELDS` order, followed by a newline.
This verifies those selected fields and their order, not every staged byte,
free-text field or sampling-frame record. Source bytes remain unchanged.

The 2026-11-04 run above verified source/staged agreement, including fingerprint
`66cdcba72334c3bbc0d69fef58b3717e81fdd997a4b2ba3ce1bd9db81f7971e2`.
The source archive SHA-256 is recorded in the
[original source audit](enoe-2025q3-source-audit.md).

| Original source table | Records | Entity/stratum combinations | Nested UPMs | Single-UPM strata |
|---|---:|---:|---:|---:|
| VIV | 150,405 | 745 | 21,252 | 24 |
| HOG | 151,354 | 745 | 21,252 | 24 |
| SDEM | 422,306 | 744 | 21,203 | 23 |

VIV and HOG each contain 49 nested UPMs and one stratum absent from SDEM.
None of the 23 SDEM singleton strata gains another UPM in either parent table.
Thus missing SDEM members alone do not explain those 23 cases. Matching source
and staged selected-field fingerprints also rules out a change to those values
or their order during staging for this reviewed run. It does not identify the
official variance pseudo-strata or justify treating absent UPMs as zero-response
clusters for variance estimation.

## Remaining gates for issue #42

1. Establish the period-specific variance population and any official
   pseudo-stratum mapping or singleton treatment; obtain a methodological
   clarification if the published documentation is insufficient. No external
   inquiry has been sent by this implementation.
2. Use the verified 90%/1.645 convention for the four references above. Establish
   the applicable reference and convention separately for any additional
   indicator; do not make 95% a hidden default or generalize from four rows.
3. Reproduce official estimates, SEs, CVs and intervals with tolerances based on
   published rounding, and document discrepancies. Cross-check independently.
4. Validate target-domain precision before IMSS–ENOE comparison. National
   arithmetic agreement does not establish precision for platform-related groups.

The remaining clarification should ask which public variance-stratum mapping
applies to `est_d_tri` in the 2025 Q3 CSV, how single-UPM strata are treated,
and how UPMs present only in VIV/HOG enter the variance population. Include the
reviewed source version and aggregate support counts above, not person records.
Do not assume the 2021 weight-adjustment procedure answers these questions.
