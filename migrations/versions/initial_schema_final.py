"""initial_schema_final

Revision ID: initial_schema_final
Revises:
Create Date: 2026-06-29 07:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision = "initial_schema_final"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Usamos SQL puro con IF NOT EXISTS para ser 100% idempotentes
    # Esto funcionará tanto en DB vacía como en DB pre-poblada.
    op.execute(
        sa.text("""
        CREATE TABLE IF NOT EXISTS tenants (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(255) NOT NULL,
            status VARCHAR(50) DEFAULT 'active',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            webhook_secret VARCHAR(255) UNIQUE,
            plan VARCHAR(50) DEFAULT 'free',
            business_category VARCHAR(100) DEFAULT 'general'
        );
        CREATE TABLE IF NOT EXISTS users (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            role VARCHAR(50) DEFAULT 'employee',
            tenant_id UUID REFERENCES tenants(id)
        );
        CREATE TABLE IF NOT EXISTS bot_profiles (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID REFERENCES tenants(id),
            name VARCHAR(100) NOT NULL,
            capabilities JSONB,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS bot_settings (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID REFERENCES tenants(id),
            bot_profile_id UUID REFERENCES bot_profiles(id),
            bot_name VARCHAR(100),
            welcome_message TEXT,
            farewell_message TEXT,
            handoff_message TEXT,
            support_email VARCHAR(255),
            is_global_active BOOLEAN DEFAULT TRUE,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS bot_nodes (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID REFERENCES tenants(id),
            bot_profile_id UUID REFERENCES bot_profiles(id),
            name VARCHAR(100) NOT NULL,
            prompt TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS cash_box (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID REFERENCES tenants(id),
            abierta BOOLEAN DEFAULT false,
            efectivo_inicial DECIMAL(12,2) DEFAULT 0,
            ventas_efectivo DECIMAL(12,2) DEFAULT 0,
            ventas_digital DECIMAL(12,2) DEFAULT 0,
            hora_apertura TIMESTAMP WITH TIME ZONE
        );
    """)
    )


def downgrade():
    op.execute(
        "DROP TABLE IF EXISTS bot_nodes, bot_settings, bot_profiles, cash_box, users, tenants CASCADE;"
    )
