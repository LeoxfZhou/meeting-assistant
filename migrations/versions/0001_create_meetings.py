"""Create meetings; no extraction or task tables."""
from alembic import op
import sqlalchemy as sa

revision = "0001_create_meetings"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "meetings",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("source_type", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), server_default="ready", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("source_type IN ('pasted_text', 'txt', 'markdown')", name="ck_meetings_source_type"),
        sa.CheckConstraint("status = 'ready'", name="ck_meetings_status"),
        sa.CheckConstraint("length(trim(title)) > 0", name="ck_meetings_title"),
        sa.CheckConstraint("length(trim(content)) > 0", name="ck_meetings_content"),
    )


def downgrade() -> None:
    op.drop_table("meetings")
