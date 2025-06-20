"""rename devops role to ops

Revision ID: b1c2d3e4f5g6
Revises: a1b2c3d4e5f6
Create Date: 2025-01-28 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'b1c2d3e4f5g6'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Rename devops role to ops"""
    # Update existing devops role values to ops
    op.execute("UPDATE users SET role = 'ops' WHERE role = 'devops'")
    
    # Update the enum type (PostgreSQL specific)
    # Note: This is a simplified approach. In production, you might need
    # more complex enum migration handling depending on your database
    try:
        op.execute("ALTER TYPE role ADD VALUE 'ops'")
    except Exception:
        # Value might already exist, ignore the error
        pass


def downgrade() -> None:
    """Revert ops role back to devops"""
    # Update existing ops role values back to devops
    op.execute("UPDATE users SET role = 'devops' WHERE role = 'ops'") 