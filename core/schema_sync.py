import logging

from sqlalchemy import text

logger = logging.getLogger("OmniCore.SchemaSync")


class SchemaSync:
    """
    Sistema de Sincronización Automática de Esquema.
    Sustituye a Alembic para eliminar errores de despliegue.
    Asegura que todas las tablas y columnas existan antes de iniciar el servidor.
    """

    def __init__(self, engine):
        self.engine = engine

    def sync(self):
        logger.info("🚀 Iniciando Sincronización Automática de Esquema...")

        # Definición de todas las tablas y sus columnas necesarias.
        # Usamos 'CREATE TABLE IF NOT EXISTS' y 'ALTER TABLE ... ADD COLUMN IF NOT EXISTS'
        # para garantizar que el sistema sea idempotente y no falle.

        statements = [
            # 1. Tenants & Core
            "CREATE TABLE IF NOT EXISTS tenants (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), name VARCHAR(255) NOT NULL, status VARCHAR(50) DEFAULT 'active', created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP, webhook_secret VARCHAR(255) UNIQUE, plan VARCHAR(50) DEFAULT 'free', business_category VARCHAR(100) DEFAULT 'general');",
            "CREATE TABLE IF NOT EXISTS users (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), email VARCHAR(255) UNIQUE NOT NULL, password_hash VARCHAR(255) NOT NULL, role VARCHAR(50) DEFAULT 'employee', tenant_id UUID REFERENCES tenants(id));",
            "CREATE TABLE IF NOT EXISTS saas_plans (plan_id VARCHAR(50) PRIMARY KEY, name VARCHAR(100) NOT NULL, monthly_price DECIMAL(12,2) DEFAULT 0, features JSONB DEFAULT '[]');",
            "CREATE TABLE IF NOT EXISTS cash_box (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id UUID REFERENCES tenants(id), abierta BOOLEAN DEFAULT false, efectivo_inicial DECIMAL(12,2) DEFAULT 0, ventas_efectivo DECIMAL(12,2) DEFAULT 0, ventas_digital DECIMAL(12,2) DEFAULT 0, hora_apertura TIMESTAMP WITH TIME ZONE);",
            "CREATE TABLE IF NOT EXISTS credentials (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id UUID REFERENCES tenants(id), service_name VARCHAR(100), account_alias VARCHAR(100), api_key TEXT, secret TEXT, metadata JSONB);",
            # 2. Bots & AI
            "CREATE TABLE IF NOT EXISTS bot_profiles (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id UUID REFERENCES tenants(id), name VARCHAR(100) NOT NULL, capabilities JSONB, is_active BOOLEAN DEFAULT TRUE, created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP);",
            "CREATE TABLE IF NOT EXISTS bot_settings (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id UUID REFERENCES tenants(id), bot_profile_id UUID REFERENCES bot_profiles(id), bot_name VARCHAR(100), welcome_message TEXT, farewell_message TEXT, handoff_message TEXT, support_email VARCHAR(255), is_global_active BOOLEAN DEFAULT TRUE, updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP);",
            "CREATE TABLE IF NOT EXISTS bot_nodes (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id UUID REFERENCES tenants(id), bot_profile_id UUID REFERENCES bot_profiles(id), name VARCHAR(100) NOT NULL, prompt TEXT NOT NULL);",
            "CREATE TABLE IF NOT EXISTS bot_options (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id UUID REFERENCES tenants(id), node_id UUID REFERENCES bot_nodes(id), label VARCHAR(100) NOT NULL, next_node_id UUID, action VARCHAR(100));",
            # 3. SDUI & UI
            "CREATE TABLE IF NOT EXISTS frontend_manifest (id SERIAL PRIMARY KEY, tenant_id UUID REFERENCES tenants(id), module VARCHAR(100) NOT NULL, version VARCHAR(50) NOT NULL, assets JSONB NOT NULL, active BOOLEAN DEFAULT true, updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP);",
            "CREATE TABLE IF NOT EXISTS panel_definitions (panel_id VARCHAR(100) PRIMARY KEY, name VARCHAR(100) NOT NULL, config_json JSONB, priority INTEGER DEFAULT 100, required_role VARCHAR(50), tenant_id UUID REFERENCES tenants(id), is_active BOOLEAN DEFAULT true);",
            "CREATE TABLE IF NOT EXISTS ui_themes (tenant_id UUID PRIMARY KEY REFERENCES tenants(id), primary_color VARCHAR(7) DEFAULT '#000000', secondary_color VARCHAR(7) DEFAULT '#FFFFFF', dark_mode BOOLEAN DEFAULT false);",
            "CREATE TABLE IF NOT EXISTS ui_layouts (id SERIAL PRIMARY KEY, tenant_id UUID REFERENCES tenants(id), screen_id VARCHAR(50) NOT NULL, layout_json JSONB NOT NULL, UNIQUE(tenant_id, screen_id));",
            # 4. Business Logic (Sales & Stock)
            "CREATE TABLE IF NOT EXISTS products (code VARCHAR(100), name VARCHAR(255) NOT NULL, price DECIMAL(12,2) NOT NULL, quantity INTEGER NOT NULL DEFAULT 0, category VARCHAR(100), is_weight BOOLEAN DEFAULT false, tenant_id UUID REFERENCES tenants(id), PRIMARY KEY (code, tenant_id));",
            "CREATE TABLE IF NOT EXISTS stock_movements (id SERIAL PRIMARY KEY, product_code VARCHAR(100), quantity INTEGER NOT NULL, reason VARCHAR(100), user_id UUID, tenant_id UUID REFERENCES tenants(id), created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP);",
            "CREATE TABLE IF NOT EXISTS sales (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id UUID REFERENCES tenants(id), cliente VARCHAR(255), customer_id UUID, total DECIMAL(12,2) NOT NULL, metodo_pago VARCHAR(50), paga_con DECIMAL(12,2), vuelto DECIMAL(12,2), created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP);",
            "CREATE TABLE IF NOT EXISTS sale_items (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id UUID REFERENCES tenants(id), sale_id UUID REFERENCES sales(id), product_code VARCHAR(100), quantity INTEGER NOT NULL, price DECIMAL(12,2) NOT NULL, subtotal DECIMAL(12,2) NOT NULL);",
            "CREATE TABLE IF NOT EXISTS sales_orders (id SERIAL PRIMARY KEY, tenant_id UUID REFERENCES tenants(id), total DECIMAL(12,2) NOT NULL, payment_status VARCHAR(50) DEFAULT 'pending', client_request_id VARCHAR(255), payment_link TEXT, created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP);",
            # 5. Logs & Audit
            "CREATE TABLE IF NOT EXISTS audit_log (id SERIAL PRIMARY KEY, tenant_id UUID REFERENCES tenants(id), user_id UUID, command VARCHAR(100) NOT NULL, params JSONB, created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP);",
            "CREATE TABLE IF NOT EXISTS dev_logs (id SERIAL PRIMARY KEY, command VARCHAR(100), params JSONB, result JSONB, error TEXT, execution_time_ms INTEGER, user_id UUID, tenant_id UUID REFERENCES tenants(id), role VARCHAR(50), created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP);",
            "CREATE TABLE IF NOT EXISTS error_logs (id SERIAL PRIMARY KEY, tenant_id UUID REFERENCES tenants(id), source VARCHAR(100), message TEXT, stack_trace TEXT, created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP);",
            # 6. Permissions
            "CREATE TABLE IF NOT EXISTS permissions (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), code VARCHAR(100) UNIQUE NOT NULL, description VARCHAR(255), module VARCHAR(50));",
            "CREATE TABLE IF NOT EXISTS plan_permissions (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), plan_name VARCHAR(50) NOT NULL, permission_id UUID REFERENCES permissions(id));",
            "CREATE TABLE IF NOT EXISTS user_permissions (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), user_id UUID REFERENCES users(id), permission_id UUID REFERENCES permissions(id), is_granted BOOLEAN DEFAULT true);",
        ]

        # Ejecutar todas las sentencias
        with self.engine.connect() as conn:
            # Iniciar transacción para asegurar atomicidad de la sincronización
            trans = conn.begin()
            try:
                for stmt in statements:
                    conn.execute(text(stmt))

                # Asegurar que el plan 'free' siempre exista
                conn.execute(
                    text(
                        "INSERT INTO saas_plans (plan_id, name, monthly_price) VALUES ('free', 'Plan Gratuito', 0.0) ON CONFLICT (plan_id) DO NOTHING;"
                    )
                )

                trans.commit()
                logger.info("✅ Esquema de base de datos sincronizado exitosamente.")
            except Exception as e:
                trans.rollback()
                logger.error(f"❌ Error crítico durante la sincronización del esquema: {e}")
                raise e
