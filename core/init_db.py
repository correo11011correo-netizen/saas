import logging
import os

import psycopg2

# Configuration
DB_URL = os.getenv("DATABASE_URL")
if not DB_URL:
    raise Exception("DATABASE_URL variable not set")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DB_Init")


def run_query(cursor, query, params=None):
    try:
        cursor.execute(query, params)
    except Exception as e:
        logger.error(f"Error executing query: {e}")
        raise e


def init_db():
    max_retries = 3
    for attempt in range(max_retries):
        conn = None
        try:
            conn = psycopg2.connect(DB_URL)
            conn.autocommit = True
            cur = conn.cursor()

            # 1. Create Tenants Table
            run_query(
                cur,
                """
                CREATE TABLE IF NOT EXISTS tenants (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    name VARCHAR(255) NOT NULL,
                    status VARCHAR(50) DEFAULT 'active',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
                """,
            )

            # Add webhook_secret, plan and business_category if they don't exist
            run_query(
                cur,
                """
                DO $$
                BEGIN
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='tenants' AND column_name='webhook_secret') THEN
                        ALTER TABLE tenants ADD COLUMN webhook_secret VARCHAR(255) UNIQUE;
                    END IF;
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='tenants' AND column_name='plan') THEN
                        ALTER TABLE tenants ADD COLUMN plan VARCHAR(50) DEFAULT 'free';
                    END IF;
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='tenants' AND column_name='business_category') THEN
                        ALTER TABLE tenants ADD COLUMN business_category VARCHAR(100) DEFAULT 'general';
                    END IF;
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='whatsapp_sessions' AND column_name='session_data') THEN
                        ALTER TABLE whatsapp_sessions ADD COLUMN session_data JSONB DEFAULT '{}';
                    END IF;
                END $$;
                """,
            )

            # 2. Create Audit Log Table
            run_query(
                cur,
                """
                CREATE TABLE IF NOT EXISTS audit_log (
                    id BIGSERIAL PRIMARY KEY,
                    tenant_id UUID REFERENCES tenants(id),
                    user_id UUID,
                    command VARCHAR(100),
                    params JSONB,
                    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
                """,
            )

            # 2.1 Create Frontend Manifest Table
            run_query(
                cur,
                """
                CREATE TABLE IF NOT EXISTS frontend_manifest (
                    id SERIAL PRIMARY KEY,
                    tenant_id UUID REFERENCES tenants(id),
                    module VARCHAR(100) NOT NULL,
                    version VARCHAR(50) NOT NULL,
                    assets JSONB NOT NULL,
                    active BOOLEAN DEFAULT true,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
                """,
            )

            # --- SDUI: Server-Driven UI Infrastructure ---
            run_query(
                cur,
                """
                CREATE TABLE IF NOT EXISTS ui_components (
                    id VARCHAR(50) PRIMARY KEY, -- e.g., 'BtnPrimary', 'InputText', 'ProductCard'
                    component_type VARCHAR(50) NOT NULL, -- 'button', 'input', 'card', 'list'
                    default_props JSONB DEFAULT '{}'
                );
                """,
            )

            run_query(
                cur,
                """
                CREATE TABLE IF NOT EXISTS ui_themes (
                    tenant_id UUID PRIMARY KEY REFERENCES tenants(id),
                    primary_color VARCHAR(7) DEFAULT '#000000',
                    secondary_color VARCHAR(7) DEFAULT '#FFFFFF',
                    accent_color VARCHAR(7) DEFAULT '#CCCCCC',
                    dark_mode BOOLEAN DEFAULT false,
                    logo_url TEXT
                );
                """,
            )

            run_query(
                cur,
                """
                CREATE TABLE IF NOT EXISTS ui_layouts (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    tenant_id UUID REFERENCES tenants(id),
                    screen_id VARCHAR(50) NOT NULL, -- e.g., 'home', 'checkout', 'stock_manage'
                    layout_json JSONB NOT NULL, -- The tree of components and their props
                    order_index INT DEFAULT 0,
                    is_active BOOLEAN DEFAULT true,
                    UNIQUE (tenant_id, screen_id)
                );
                """,
            )

            # 2.2 Create Bot Profiles Table (The Logical Entity)

            run_query(
                cur,
                """
                CREATE TABLE IF NOT EXISTS bot_profiles (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    tenant_id UUID REFERENCES tenants(id),
                    name VARCHAR(100) NOT NULL,
                    capabilities JSONB DEFAULT '{"can_sell": false, "can_manage_stock": false, "can_process_payments": false}',
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
                """,
            )

            # --- OMNISTAFF: Employee Management System ---
            run_query(
                cur,
                """
                CREATE TABLE IF NOT EXISTS business_definitions (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    tenant_id UUID REFERENCES tenants(id),
                    def_type VARCHAR(50) NOT NULL, -- 'permission', 'goal_type', 'task'
                    def_key VARCHAR(100) NOT NULL, -- e.g., 'limpiar_heladera', 'ventas_mensuales'
                    def_label VARCHAR(100), -- Human readable name: 'Limpiar Heladera'
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE (tenant_id, def_type, def_key)
                );
                """,
            )

            run_query(
                cur,
                """
                CREATE TABLE IF NOT EXISTS available_modules (
                    module_id VARCHAR(100) PRIMARY KEY, -- e.g., 'sales_panel', 'stock_advanced'
                    name VARCHAR(255) NOT NULL,
                    base_plan VARCHAR(50) DEFAULT 'free', -- 'free', 'pro', 'enterprise'
                    is_custom BOOLEAN DEFAULT false,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
                """,
            )

            run_query(
                cur,
                """
                CREATE TABLE IF NOT EXISTS tenant_modules (
                    tenant_id UUID REFERENCES tenants(id),
                    module_id VARCHAR(100) REFERENCES available_modules(module_id),
                    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (tenant_id, module_id)
                );
                """,
            )

            run_query(
                cur,
                """
                CREATE TABLE IF NOT EXISTS employees (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    tenant_id UUID REFERENCES tenants(id),
                    user_id UUID REFERENCES users(id), -- Null if the employee is a Bot
                    bot_profile_id UUID REFERENCES bot_profiles(id), -- Null if the employee is Human
                    name VARCHAR(255) NOT NULL,
                    role VARCHAR(100) NOT NULL,
                    status VARCHAR(50) DEFAULT 'active',
                    type VARCHAR(20) NOT NULL, -- 'human' or 'bot'
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
                """,
            )

            run_query(
                cur,
                """
                CREATE TABLE IF NOT EXISTS employee_permissions (
                    id SERIAL PRIMARY KEY,
                    employee_id UUID REFERENCES employees(id),
                    permission_key VARCHAR(100) NOT NULL, -- e.g., 'can_sell', 'can_restock', 'can_clean'
                    granted BOOLEAN DEFAULT TRUE,
                    UNIQUE (employee_id, permission_key)
                );
                """,
            )

            run_query(
                cur,
                """
                CREATE TABLE IF NOT EXISTS employee_goals (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    employee_id UUID REFERENCES employees(id),
                    goal_type VARCHAR(50) NOT NULL, -- 'sales_volume', 'revenue', 'appointments'
                    target_value DECIMAL(12,2) NOT NULL,
                    current_value DECIMAL(12,2) DEFAULT 0,
                    start_date DATE NOT NULL,
                    end_date DATE NOT NULL,
                    tenant_id UUID REFERENCES tenants(id)
                );
                """,
            )

            # --- SAAS Monetization System ---
            run_query(
                cur,
                """
                CREATE TABLE IF NOT EXISTS saas_plans (
                    plan_id VARCHAR(50) PRIMARY KEY, -- 'free', 'pro', 'enterprise'
                    name VARCHAR(100) NOT NULL,
                    monthly_price DECIMAL(12,2) DEFAULT 0,
                    features JSONB DEFAULT '[]',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
                """,
            )

            run_query(
                cur,
                """
                CREATE TABLE IF NOT EXISTS tenant_subscriptions (
                    tenant_id UUID PRIMARY KEY REFERENCES tenants(id),
                    plan_id VARCHAR(50) REFERENCES saas_plans(plan_id),
                    subscription_status VARCHAR(50) DEFAULT 'active', -- 'active', 'past_due', 'canceled'
                    start_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    end_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    last_payment_date TIMESTAMP WITH TIME ZONE,
                    auto_renew BOOLEAN DEFAULT true
                );
                """,
            )

            # 2.3 Create Bot Assignments Table (The Connection Link)

            run_query(
                cur,
                """
                CREATE TABLE IF NOT EXISTS bot_assignments (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    tenant_id UUID REFERENCES tenants(id),
                    credential_id UUID REFERENCES credentials(id),
                    bot_profile_id UUID REFERENCES bot_profiles(id),
                    is_primary BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE (tenant_id, credential_id)
                );
                """,
            )

            # 3. Update Users Table
            run_query(
                cur,
                """
                CREATE TABLE IF NOT EXISTS users (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    email VARCHAR(255) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    role VARCHAR(50) DEFAULT 'employee'
                );
                """,
            )
            run_query(
                cur,
                """
                DO $$
                BEGIN
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='users' AND column_name='tenant_id') THEN
                        ALTER TABLE users ADD COLUMN tenant_id UUID REFERENCES tenants(id);
                        CREATE INDEX idx_users_tenant ON users(tenant_id);
                    END IF;
                END $$;
                """,
            )

            # --- CRM: Customer Management ---
            run_query(
                cur,
                """
                CREATE TABLE IF NOT EXISTS customers (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    tenant_id UUID REFERENCES tenants(id),
                    phone_number VARCHAR(50) NOT NULL,
                    full_name VARCHAR(255),
                    email VARCHAR(255),
                    metadata JSONB DEFAULT '{}',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE (tenant_id, phone_number)
                );
                """,
            )

            # 4. Business Tables - Multi-tenancy adaptation
            business_schemas = {
                "sales": [
                    "cliente VARCHAR(255)",
                    "customer_id UUID REFERENCES customers(id)",
                    "total DECIMAL(12,2)",
                    "metodo_pago VARCHAR(50)",
                    "paga_con DECIMAL(12,2)",
                    "vuelto DECIMAL(12,2)",
                ],
                "sale_items": [
                    "sale_id UUID",
                    "product_code VARCHAR(100)",
                    "quantity INT",
                    "price DECIMAL(12,2)",
                    "subtotal DECIMAL(12,2)",
                ],
                "products": [
                    "code VARCHAR(100)",
                    "name VARCHAR(255)",
                    "price DECIMAL(12,2)",
                    "quantity INT",
                    "category VARCHAR(100)",
                    "is_weight BOOLEAN",
                ],
                "stock_movements": [
                    "product_code VARCHAR(100)",
                    "quantity INT",
                    "reason VARCHAR(255)",
                    "user_id UUID",
                ],
                "cash_box": [
                    "abierta BOOLEAN DEFAULT false",
                    "efectivo_inicial DECIMAL(12,2) DEFAULT 0",
                    "ventas_efectivo DECIMAL(12,2) DEFAULT 0",
                    "ventas_digital DECIMAL(12,2) DEFAULT 0",
                    "hora_apertura TIMESTAMP WITH TIME ZONE",
                ],
                "aliases": [
                    "nombre VARCHAR(100)",
                    "limite DECIMAL(12,2)",
                    "acumulado DECIMAL(12,2)",
                ],
                "whatsapp_conversations": [
                    "phone_number VARCHAR(50)",
                    "sender_type VARCHAR(50)",
                    "message TEXT",
                    "message_type VARCHAR(50)",
                    "current_node_id UUID",
                    "bot_profile_id UUID REFERENCES bot_profiles(id)",
                    "is_bot_active BOOLEAN DEFAULT TRUE",
                    "created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP",
                    "status VARCHAR(20) DEFAULT 'sent'",
                ],
                "whatsapp_sessions": [
                    "phone_number VARCHAR(50)",
                    "bot_profile_id UUID REFERENCES bot_profiles(id)",
                    "is_bot_active BOOLEAN DEFAULT TRUE",
                    "current_node_id UUID",
                    "last_interaction TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP",
                ],
                "whatsapp_menus": [
                    "menu_name VARCHAR(100)",
                    "prompt TEXT",
                    "options JSONB",
                ],
                "bot_nodes": [
                    "name VARCHAR(100)",
                    "bot_profile_id UUID REFERENCES bot_profiles(id)",
                    "prompt TEXT",
                ],
                "bot_options": [
                    "node_id UUID",
                    "bot_profile_id UUID REFERENCES bot_profiles(id)",
                    "label VARCHAR(100)",
                    "next_node_id UUID",
                    "action VARCHAR(100)",
                ],
                "bot_messages": [
                    "conversation_id UUID",
                    "sender VARCHAR(50)",
                    "message TEXT",
                ],
                "bot_settings": [
                    "bot_profile_id UUID REFERENCES bot_profiles(id)",
                    "bot_name VARCHAR(100)",
                    "welcome_message TEXT",
                    "farewell_message TEXT",
                    "handoff_message TEXT",
                    "support_email VARCHAR(255)",
                    "is_global_active BOOLEAN DEFAULT TRUE",
                    "updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP",
                ],
                "sales_orders": [
                    "total DECIMAL(12,2)",
                    "payment_status VARCHAR(50)",
                    "payment_link TEXT",
                    "metadata JSONB",
                    "client_request_id UUID",
                ],
                "system_settings": ["key VARCHAR(100)", "value TEXT"],
                "user_permissions": ["user_id UUID", "permission_key VARCHAR(100)"],
                "credentials": [
                    "service_name VARCHAR(100)",
                    "account_alias VARCHAR(100)",
                    "api_key TEXT",
                    "secret TEXT",
                    "metadata JSONB",
                ],
            }

            for table, columns in business_schemas.items():
                run_query(
                    cur,
                    f"CREATE TABLE IF NOT EXISTS {table} (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id UUID REFERENCES tenants(id));",
                )

                for col in columns:
                    col_name = col.split(" ")[0]
                    run_query(
                        cur,
                        f"""
                        DO $$
                        BEGIN
                            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='{table}' AND column_name='{col_name}') THEN
                                ALTER TABLE {table} ADD COLUMN {col};
                            END IF;
                        END $$;
                        """,
                    )

                run_query(
                    cur,
                    f"""
                    CREATE INDEX IF NOT EXISTS idx_{table}_tenant ON {table}(tenant_id);
                    """,
                )

            # Constraints
            run_query(
                cur,
                """
                DO $$
                BEGIN
                    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'unique_whatsapp_session_per_tenant') THEN
                        ALTER TABLE whatsapp_sessions ADD CONSTRAINT unique_whatsapp_session_per_tenant UNIQUE (tenant_id, phone_number);
                    END IF;
                END $$;
                """,
            )

            run_query(
                cur,
                """
                DO $$
                BEGIN
                    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'unique_bot_settings_per_profile') THEN
                        ALTER TABLE bot_settings ADD CONSTRAINT unique_bot_settings_per_profile UNIQUE (tenant_id, bot_profile_id);
                    END IF;
                END $$;
                """,
            )

            run_query(
                cur,
                """
                DO $$
                BEGIN
                    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'unique_bot_node_per_profile') THEN
                        ALTER TABLE bot_nodes ADD CONSTRAINT unique_bot_node_per_profile UNIQUE (tenant_id, bot_profile_id, name);
                    END IF;
                END $$;
                """,
            )

            run_query(
                cur,
                """
                DO $$
                BEGIN
                    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'unique_product_per_tenant') THEN
                        ALTER TABLE products ADD CONSTRAINT unique_product_per_tenant UNIQUE (code, tenant_id);
                    END IF;
                END $$;
                """,
            )

            run_query(
                cur,
                """
                DO $$
                BEGIN
                    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'unique_account_per_service') THEN
                        ALTER TABLE credentials DROP CONSTRAINT unique_account_per_service;
                    END IF;
                    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'unique_account_per_service') THEN
                        ALTER TABLE credentials ADD CONSTRAINT unique_account_per_service UNIQUE (tenant_id, service_name, account_alias);
                    END IF;
                END $$;
                """,
            )

            logger.info("Database infrastructure initialized successfully.")
            return

        except Exception as e:
            logger.error(f"Initialization attempt {attempt + 1} failed: {e}")
            if attempt == max_retries - 1:
                raise e
            import time

            time.sleep(2)
        finally:
            if conn:
                conn.close()


if __name__ == "__main__":
    init_db()
