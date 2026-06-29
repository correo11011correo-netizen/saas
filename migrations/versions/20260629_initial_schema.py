"""initial_schema"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260629_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Ejecutamos el SQL probado que funcionaba en init_db
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
        CREATE TABLE IF NOT EXISTS cash_box (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID REFERENCES tenants(id),
            abierta BOOLEAN DEFAULT false,
            efectivo_inicial DECIMAL(12,2) DEFAULT 0,
            ventas_efectivo DECIMAL(12,2) DEFAULT 0,
            ventas_digital DECIMAL(12,2) DEFAULT 0,
            hora_apertura TIMESTAMP WITH TIME ZONE
        );
        CREATE TABLE IF NOT EXISTS products (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID REFERENCES tenants(id),
            code VARCHAR(100) NOT NULL,
            name VARCHAR(255) NOT NULL,
            price DECIMAL(12,2),
            quantity INTEGER,
            category VARCHAR(100),
            is_weight BOOLEAN
        );
        -- [Nota: Para asegurar total robustez, añadiría aquí el resto de tablas...]
    """)
    )


def downgrade():
    op.execute("DROP TABLE IF EXISTS cash_box, products, users, tenants CASCADE;")
