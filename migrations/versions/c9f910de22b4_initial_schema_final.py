"""initial_schema_final

Revision ID: c9f910de22b4
Revises:
Create Date: 2026-06-29 10:30:25.924912

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c9f910de22b4"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Creamos las tablas una por una con SQL puro para garantizar idempotencia
    op.execute(
        sa.text(
            "CREATE TABLE IF NOT EXISTS tenants (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), name VARCHAR(255) NOT NULL, status VARCHAR(50) DEFAULT 'active', created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP, webhook_secret VARCHAR(255) UNIQUE, plan VARCHAR(50) DEFAULT 'free', business_category VARCHAR(100) DEFAULT 'general');"
        )
    )
    op.execute(
        sa.text(
            "CREATE TABLE IF NOT EXISTS saas_plans (plan_id VARCHAR(50) PRIMARY KEY, name VARCHAR(100) NOT NULL, monthly_price DECIMAL(12,2) DEFAULT 0, features JSONB DEFAULT '[]');"
        )
    )
    op.execute(
        sa.text(
            "CREATE TABLE IF NOT EXISTS users (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), email VARCHAR(255) UNIQUE NOT NULL, password_hash VARCHAR(255) NOT NULL, role VARCHAR(50) DEFAULT 'employee', tenant_id UUID REFERENCES tenants(id));"
        )
    )
    op.execute(
        sa.text(
            "CREATE TABLE IF NOT EXISTS bot_profiles (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id UUID REFERENCES tenants(id), name VARCHAR(100) NOT NULL, capabilities JSONB, is_active BOOLEAN DEFAULT TRUE, created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP);"
        )
    )
    op.execute(
        sa.text(
            "CREATE TABLE IF NOT EXISTS bot_settings (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id UUID REFERENCES tenants(id), bot_profile_id UUID REFERENCES bot_profiles(id), bot_name VARCHAR(100), welcome_message TEXT, farewell_message TEXT, handoff_message TEXT, support_email VARCHAR(255), is_global_active BOOLEAN DEFAULT TRUE, updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP);"
        )
    )
    op.execute(
        sa.text(
            "CREATE TABLE IF NOT EXISTS bot_nodes (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id UUID REFERENCES tenants(id), bot_profile_id UUID REFERENCES bot_profiles(id), name VARCHAR(100) NOT NULL, prompt TEXT NOT NULL);"
        )
    )
    op.execute(
        sa.text(
            "CREATE TABLE IF NOT EXISTS cash_box (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id UUID REFERENCES tenants(id), abierta BOOLEAN DEFAULT false, efectivo_inicial DECIMAL(12,2) DEFAULT 0, ventas_efectivo DECIMAL(12,2) DEFAULT 0, ventas_digital DECIMAL(12,2) DEFAULT 0, hora_apertura TIMESTAMP WITH TIME ZONE);"
        )
    )
    op.execute(
        sa.text(
            "CREATE TABLE IF NOT EXISTS frontend_manifest (id SERIAL PRIMARY KEY, tenant_id UUID REFERENCES tenants(id), module VARCHAR(100) NOT NULL, version VARCHAR(50) NOT NULL, assets JSONB NOT NULL, active BOOLEAN DEFAULT true, updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP);"
        )
    )

    # Seed saas_plans
    op.execute(
        sa.text(
            "INSERT INTO saas_plans (plan_id, name, monthly_price, features) VALUES ('free', 'Plan Gratuito', 0.0, '[]') ON CONFLICT DO NOTHING;"
        )
    )
    op.execute(
        sa.text(
            "INSERT INTO saas_plans (plan_id, name, monthly_price, features) VALUES ('pro', 'Plan Profesional', 29.99, '[]') ON CONFLICT DO NOTHING;"
        )
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        "DROP TABLE IF EXISTS frontend_manifest, cash_box, bot_nodes, bot_settings, bot_profiles, users, saas_plans, tenants CASCADE;"
    )
