"""add agent_ids to users

Revision ID: a1b2c3d4e5f6
Revises: 3b772ba5c9f9
Create Date: 2025-01-28 10:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "3b772ba5c9f9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add agent_ids column to users table
    op.add_column(
        "users", 
        sa.Column("agent_ids", postgresql.JSON(astext_type=sa.Text()), nullable=True)
    )
    # Set default empty array for existing users
    op.execute("UPDATE users SET agent_ids = '[]' WHERE agent_ids IS NULL")
    # Make the column non-nullable
    op.alter_column("users", "agent_ids", nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Remove agent_ids column from users table
    op.drop_column("users", "agent_ids") 