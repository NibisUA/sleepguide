"""Optional daily screen time category breakdown.

Revision ID: 0011
Revises: 0010
"""

import sqlalchemy as sa
from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None

CATEGORIES = ("social_minutes", "entertainment_minutes", "games_minutes")


def upgrade():
    for name in CATEGORIES:
        op.add_column("screen_time_daily", sa.Column(name, sa.Integer(), nullable=True))
    op.create_check_constraint(
        "categories_valid",
        "screen_time_daily",
        "(social_minutes IS NULL OR social_minutes BETWEEN 0 AND 1440) AND "
        "(entertainment_minutes IS NULL OR entertainment_minutes BETWEEN 0 AND 1440) AND "
        "(games_minutes IS NULL OR games_minutes BETWEEN 0 AND 1440) AND "
        "COALESCE(social_minutes,0) + COALESCE(entertainment_minutes,0) + "
        "COALESCE(games_minutes,0) <= total_minutes",
    )


def downgrade():
    op.drop_constraint("categories_valid", "screen_time_daily", type_="check")
    for name in reversed(CATEGORIES):
        op.drop_column("screen_time_daily", name)
