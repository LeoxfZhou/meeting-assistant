"""Human-reviewed candidates and idempotent tasks."""
from alembic import op
import sqlalchemy as sa

revision = '0003_actions_tasks'
down_revision = '0002_auth'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('action_items',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('meeting_id', sa.Uuid(), sa.ForeignKey('meetings.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('task', sa.String(1000), nullable=False),
        sa.Column('assignee_name', sa.String(100)),
        sa.Column('assignee_user_id', sa.Uuid(), sa.ForeignKey('users.id', ondelete='RESTRICT')),
        sa.Column('due_date_text', sa.String(200)),
        sa.Column('evidence', sa.Text(), nullable=False),
        sa.Column('status', sa.String(20), server_default='pending', nullable=False),
        sa.Column('revision', sa.Integer(), server_default='1', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status IN ('pending','confirmed','rejected')", name='ck_action_items_status'))
    op.create_index('ix_action_items_meeting_id', 'action_items', ['meeting_id'])
    op.create_table('tasks',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('source_action_item_id', sa.Uuid(), sa.ForeignKey('action_items.id', ondelete='RESTRICT'), nullable=False, unique=True),
        sa.Column('source_meeting_id', sa.Uuid(), sa.ForeignKey('meetings.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('title', sa.String(1000), nullable=False),
        sa.Column('assignee_name', sa.String(100)),
        sa.Column('assignee_user_id', sa.Uuid(), sa.ForeignKey('users.id', ondelete='RESTRICT')),
        sa.Column('due_date_text', sa.String(200)),
        sa.Column('due_date', sa.DateTime(timezone=True)),
        sa.Column('status', sa.String(20), server_default='todo', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status IN ('todo','in_progress','done')", name='ck_tasks_status'))
    op.create_index('ix_tasks_source_meeting_id', 'tasks', ['source_meeting_id'])
    op.create_index('ix_tasks_assignee_user_id', 'tasks', ['assignee_user_id'])


def downgrade():
    op.drop_table('tasks')
    op.drop_table('action_items')
