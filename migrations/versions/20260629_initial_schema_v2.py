"""initial_schema_v2

Revision ID: 20260629_initial_schema_v2
Revises:
Create Date: 2026-06-29 06:15:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260629_initial_schema_v2"
down_revision = "20260629_initial_schema"  # Referenciamos la anterior para actualizar
branch_labels = None
depends_on = None


def upgrade():
    # Creamos las tablas faltantes que causaban errores
    op.create_table(
        "bot_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("capabilities", postgresql.JSONB),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "bot_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False
        ),
        sa.Column(
            "bot_profile_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("bot_profiles.id")
        ),
        sa.Column("bot_name", sa.String(100)),
        sa.Column("welcome_message", sa.Text),
        sa.Column("farewell_message", sa.Text),
        sa.Column("handoff_message", sa.Text),
        sa.Column("support_email", sa.String(255)),
        sa.Column("is_global_active", sa.Boolean, default=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "bot_nodes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False
        ),
        sa.Column(
            "bot_profile_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("bot_profiles.id"),
            nullable=False,
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("prompt", sa.Text, nullable=False),
    )

    op.create_table(
        "bot_options",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False
        ),
        sa.Column(
            "node_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("bot_nodes.id"), nullable=False
        ),
        sa.Column("label", sa.String(100), nullable=False),
        sa.Column("action", sa.String(100)),
    )


def downgrade():
    op.drop_table("bot_options")
    op.drop_table("bot_nodes")
    op.drop_table("bot_settings")
    op.drop_table("bot_profiles")
