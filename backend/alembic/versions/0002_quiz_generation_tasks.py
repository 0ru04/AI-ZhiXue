"""Create persisted quiz generation tasks."""

from alembic import op
import sqlalchemy as sa


revision = "0002_quiz_generation_tasks"
down_revision = "0001_user_system"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "quiz_generation_tasks",
        sa.Column("task_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=True),
        sa.Column("task_type", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("request_json", sa.JSON(), nullable=False),
        sa.Column("result_json", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("task_id"),
        mysql_charset="utf8mb4",
        mysql_engine="InnoDB",
    )
    op.create_index(
        "ix_quiz_generation_tasks_status_updated",
        "quiz_generation_tasks",
        ["status", "updated_at"],
    )
    op.create_index(
        "ix_quiz_generation_tasks_user_created",
        "quiz_generation_tasks",
        ["user_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_quiz_generation_tasks_user_created",
        table_name="quiz_generation_tasks",
    )
    op.drop_index(
        "ix_quiz_generation_tasks_status_updated",
        table_name="quiz_generation_tasks",
    )
    op.drop_table("quiz_generation_tasks")
