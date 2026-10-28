"""Select one reconciled IMSS source version per month."""

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

DIMENSIONS = (
    "cve_delegacion",
    "cve_subdelegacion",
    "cve_entidad",
    "cve_municipio",
    "ptpd",
    "sector_economico_1",
    "sector_economico_2",
    "sector_economico_4",
    "tamaño_patron",
    "sexo",
    "rango_edad",
    "rango_salarial",
    "rango_uma",
)
METRICS = (
    "asegurados",
    "no_trabajadores",
    "ta",
    "teu",
    "tec",
    "tpu",
    "tpc",
    "ta_sal",
    "teu_sal",
    "tec_sal",
    "tpu_sal",
    "tpc_sal",
    "masa_sal_ta",
    "masa_sal_teu",
    "masa_sal_tec",
    "masa_sal_tpu",
    "masa_sal_tpc",
)


def upgrade() -> None:
    op.execute("CREATE INDEX imss_row_run_id ON staging.imss_row (run_id)")
    op.execute("ALTER TABLE staging.imss_load ADD UNIQUE (run_id, reference_period)")
    op.execute("""
        CREATE TABLE imss.selected_month (
          reference_period date PRIMARY KEY,
          run_id uuid NOT NULL UNIQUE,
          selected_at timestamptz NOT NULL DEFAULT now(),
          FOREIGN KEY (run_id, reference_period)
            REFERENCES staging.imss_load (run_id, reference_period)
        )
    """)
    dims = [f'r.raw_fields[{i}] AS "{name}"' for i, name in enumerate(DIMENSIONS, 1)]
    metrics = [
        f"NULLIF(NULLIF(r.raw_fields[{i}], ''), 'NA')::numeric AS \"{name}\""
        for i, name in enumerate(METRICS, 14)
    ]
    columns = ", ".join(dims + metrics)
    op.execute(f"""
        CREATE VIEW imss.monthly_cells AS
        SELECT s.reference_period, l.source_file_id, r.run_id, r.row_number, {columns}
        FROM imss.selected_month s
        JOIN staging.imss_load l ON l.run_id=s.run_id
        JOIN staging.imss_row r ON r.run_id=s.run_id
    """)


def downgrade() -> None:
    op.execute("DROP VIEW imss.monthly_cells; DROP TABLE imss.selected_month")
    op.execute(
        "ALTER TABLE staging.imss_load DROP CONSTRAINT imss_load_run_id_reference_period_key"
    )
    op.execute("DROP INDEX staging.imss_row_run_id")
