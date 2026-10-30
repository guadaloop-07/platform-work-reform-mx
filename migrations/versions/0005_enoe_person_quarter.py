"""Expose a source-faithful ENOE pilot person-quarter foundation."""

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE SCHEMA IF NOT EXISTS enoe;
        CREATE VIEW enoe.person_quarter_pilot AS
        SELECT l.run_id, l.source_file_id, l.reference_period, l.layout_version,
               s.source_key, s.row_number AS sdem_row_number,
               s.raw_fields AS sdem_raw_fields,
               c1.row_number AS coe1_row_number, c1.raw_fields AS coe1_raw_fields,
               c2.row_number AS coe2_row_number, c2.raw_fields AS coe2_raw_fields
        FROM staging.enoe_load l
        JOIN meta.ingestion_run r ON r.id = l.run_id AND r.status = 'succeeded'
        JOIN staging.enoe_row s ON s.run_id = l.run_id AND s.table_name = 'SDEM'
        LEFT JOIN staging.enoe_row c1 ON c1.run_id = s.run_id
          AND c1.table_name = 'COE1' AND c1.source_key = s.source_key
        LEFT JOIN staging.enoe_row c2 ON c2.run_id = s.run_id
          AND c2.table_name = 'COE2' AND c2.source_key = s.source_key
        WHERE l.reference_period = DATE '2025-07-01'
          AND l.layout_version = 'enoe-2025q3-v1'
    """)


def downgrade() -> None:
    op.execute("DROP VIEW enoe.person_quarter_pilot")
