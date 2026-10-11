"""append-only decisions, approvals, audit events and receipts

Decisions, signatures, audit events and idempotency receipts are immutable history. The application
only ever inserts them; this trigger makes an UPDATE impossible even for a buggy or hostile caller.
(Rows disappear only when a whole discarded staging container is removed.)

Revision ID: 0006
Revises: 0005
"""
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

TABLES = ("review_decisions", "exception_decisions", "plan_approvals", "plan_dispositions", "publication_decisions", "audit_events",
          "command_receipts", "task_events", "concern_events", "encounter_decisions")


def upgrade() -> None:
    op.execute("""
        CREATE OR REPLACE FUNCTION geevi_append_only() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'append-only table %: recorded history cannot be modified', TG_TABLE_NAME USING ERRCODE = 'restrict_violation';
        END;
        $$ LANGUAGE plpgsql;
    """)
    for table in TABLES:
        op.execute(f"CREATE TRIGGER {table}_append_only BEFORE UPDATE ON {table} FOR EACH ROW EXECUTE FUNCTION geevi_append_only()")
    op.execute("""
        CREATE OR REPLACE FUNCTION geevi_blob_immutable() RETURNS trigger AS $$
        BEGIN
            IF NEW.sha256 IS DISTINCT FROM OLD.sha256 OR NEW.data IS DISTINCT FROM OLD.data OR NEW.length IS DISTINCT FROM OLD.length THEN
                RAISE EXCEPTION 'source_blobs are immutable content-addressed originals' USING ERRCODE = 'restrict_violation';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("CREATE TRIGGER source_blobs_immutable BEFORE UPDATE ON source_blobs FOR EACH ROW EXECUTE FUNCTION geevi_blob_immutable()")


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS source_blobs_immutable ON source_blobs")
    for table in TABLES:
        op.execute(f"DROP TRIGGER IF EXISTS {table}_append_only ON {table}")
    op.execute("DROP FUNCTION IF EXISTS geevi_blob_immutable()")
    op.execute("DROP FUNCTION IF EXISTS geevi_append_only()")
