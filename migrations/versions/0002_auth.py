"""Users and meeting ownership; keep legacy meetings owner-only."""
from alembic import op
import sqlalchemy as sa

revision = "0002_auth"
down_revision = "0001_create_meetings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("users",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("is_owner", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("email"))
    op.add_column("meetings", sa.Column("creator_user_id", sa.Uuid(), nullable=True))
    op.create_foreign_key("fk_meetings_creator_user_id", "meetings", "users", ["creator_user_id"], ["id"], ondelete="RESTRICT")
    op.create_index("ix_meetings_creator_user_id", "meetings", ["creator_user_id"])


def downgrade() -> None:
    op.drop_index("ix_meetings_creator_user_id", "meetings")
    op.drop_constraint("fk_meetings_creator_user_id", "meetings", type_="foreignkey")
    op.drop_column("meetings", "creator_user_id")
    op.drop_table("users")
