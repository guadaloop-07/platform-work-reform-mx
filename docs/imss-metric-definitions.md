# IMSS affiliated job counts

For this project, use **`ta`** in `imss.monthly_cells` when counting IMSS
affiliated jobs (puestos de trabajo afiliados), also described by IMSS as
insured jobs or insured persons associated with a job. The unit is an
affiliated job as defined by IMSS; do not label the result as a count of
distinct individuals.

Do not substitute **`asegurados`** for `ta`: the official guide defines
`asegurados` as total insured persons, a broader measure. The separate
`no_trabajadores` field refers to insured persons without an associated job.
Retain these original field names and choose a different measure only when the
research question explicitly calls for its corresponding population.

The source is the IMSS [Guía del usuario datos abiertos, asegurados](https://datos.imss.gob.mx/sites/default/files/Guia_usuario_datos_abiertos_asegurados.pdf)
and [Glosario de datos abiertos, asegurados](https://datos.imss.gob.mx/sites/default/files/glosario_datos_abiertos_asegurados_.pdf).
Use the definitions applicable to each source version and document any change.

The view contains aggregate cells and one selected source version per month.
When summing `ta`, specify the reference month, population and dimensions, and
ensure the selected cells do not overlap. Do not add monthly snapshots to
report a count of unique jobs or people over a longer period. Numeric blanks
and `NA` are represented as SQL `NULL` in the view; document missingness and do
not silently interpret it as zero. Historical source layouts without `ptpd`
retain it as `NULL`, so absence of `ptpd` does not mean absence of platform
work. These aggregate records do not support individual IMSS–ENOE linkage.
