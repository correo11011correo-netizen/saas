import psycopg2
from psycopg2 import sql
import logging
import os

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

            # Add webhook_secret and plan if they don't exist
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

            # 3. Update Users Table
            # Create table if not exists to avoid errors during init
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
            # Add tenant_id if it doesn't exist
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

            # 4. Business Tables - Multi-tenancy adaptation
            # Mapping of tables to their required columns
            business_schemas = {
                "sales": [
                    "cliente VARCHAR(255)",
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
                    "account_alias VARCHAR(100)",
                    "is_bot_active BOOLEAN DEFAULT TRUE",
                    "created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP",
                    "status VARCHAR(20) DEFAULT 'sent'",
                ],
                "whatsapp_sessions": [
                    "phone_number VARCHAR(50)",
                    "account_alias VARCHAR(100)",
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
                    "prompt TEXT",
                ],
                "bot_options": [
                    "node_id UUID",
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
                # 1. Create table if not exists with basic ID and tenant_id
                run_query(
                    cur,
                    f"CREATE TABLE IF NOT EXISTS {table} (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id UUID REFERENCES tenants(id));",
                )

                # 2. Add missing columns
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

                # 3. Create index on tenant_id if not exists
                run_query(
                    cur,
                    f"""
                    CREATE INDEX IF NOT EXISTS idx_{table}_tenant ON {table}(tenant_id);
                """,
                )

            # 4. Handle Specific Table Constraints
            logger.info("Ensuring specific business constraints...")

            # Constraint for whatsapp_sessions: Unique tenant + phone
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

            # Uniqueness for products
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
            # Uniqueness for credentials
            run_query(
                cur,
                """
                DO $$
                BEGIN
                    -- Drop old constraint if exists
                    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'unique_service_per_tenant') THEN
                        ALTER TABLE credentials DROP CONSTRAINT unique_service_per_tenant;
                    END IF;

                    -- Add new constraint
                    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'unique_account_per_service') THEN
                        ALTER TABLE credentials ADD CONSTRAINT unique_account_per_service UNIQUE (tenant_id, service_name, account_alias);
                    END IF;
                END $$;
            """,
            )

            logger.info(
                "Database infrastructure initialized successfully for multi-tenancy."
            )
            return  # Éxito total

        except Exception as e:
            logger.error(f"Initialization attempt {attempt+1} failed: {e}")
            if attempt == max_retries - 1:
                logger.error("Max retries reached. Could not initialize database.")
                raise e
            import time

            time.sleep(2)  # Esperar más tiempo entre reintentos
        finally:
            if conn:
                conn.close()


if __name__ == "__main__":
    init_db()
