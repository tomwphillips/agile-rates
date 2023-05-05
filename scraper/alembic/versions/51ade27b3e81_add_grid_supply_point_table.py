"""Add grid supply point table

Revision ID: 51ade27b3e81
Revises: 1035d91e8e10
Create Date: 2023-05-05 11:56:54.230855

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "51ade27b3e81"
down_revision = "1035d91e8e10"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "grid_supply_points",
        sa.Column("group_id", sa.String(), nullable=False),
        sa.Column("group_description", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("group_id"),
        sa.UniqueConstraint("group_id", "group_description"),
    )

    op.get_bind().execute(
        sa.text(
            """
    insert into grid_supply_points (group_id, group_description) values
        ('A', 'Eastern'),
        ('B', 'East Midlands'),
        ('C', 'London'),
        ('D', 'Merseyside and North Wales'),
        ('E', 'Midlands'),
        ('F', 'Northern'),
        ('G', 'North Western'),
        ('H', 'Southern'),
        ('J', 'South Eastern'),
        ('K', 'South Wales'),
        ('L', 'South Western'),
        ('M', 'Yorkshire'),
        ('N', 'South of Scotland'),
        ('P', 'North of Scotland');
    """
        )
    )


def downgrade() -> None:
    op.drop_table("grid_supply_points")
