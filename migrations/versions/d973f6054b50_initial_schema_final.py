"""initial_schema_final

Revision ID: d973f6054b50
Revises:
Create Date: 2026-06-29 11:52:31.857393

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "d973f6054b50"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
