"""Create versioned IMSS staging tables."""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE staging.imss_load (
          run_id uuid PRIMARY KEY,
          source_file_id uuid NOT NULL,
          reference_period date NOT NULL,
          layout_version text NOT NULL CHECK (layout_version IN ('legacy-v1', 'platform-v1')),
          row_count bigint NOT NULL CHECK (row_count > 0),
          FOREIGN KEY (run_id, source_file_id) REFERENCES meta.ingestion_run(id, source_file_id),
          UNIQUE (source_file_id, reference_period)
        );
        CREATE TABLE staging.imss_row (
          run_id uuid NOT NULL,
          row_number bigint NOT NULL,
          raw_fields text[] NOT NULL CHECK (cardinality(raw_fields) = 30)
        );
    """)


def downgrade() -> None:
    op.execute("DROP TABLE staging.imss_row; DROP TABLE staging.imss_load;")
