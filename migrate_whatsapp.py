import logging

import psycopg2

DB_URL = (
    "postgresql://postgres:TFralZyHIJnjyZrNMtoDqqtUlPTsttvT@thomas.proxy.rlwy.net:24031/railway"
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Migration")


def migrate():
    conn = None
    try:
        logger.info("Connecting to database for migration...")
        conn = psycopg2.connect(DB_URL)
        conn.autocommit = True
        cur = conn.cursor()

        # 1. Create whatsapp_sessions table
        logger.info("Creating whatsapp_sessions table...")
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS whatsapp_sessions (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                tenant_id UUID REFERENCES tenants(id),
                phone_number VARCHAR(50) NOT NULL,
                current_node_id UUID,
                account_alias VARCHAR(100) DEFAULT 'Principal',
                is_bot_active BOOLEAN DEFAULT TRUE,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(tenant_id, phone_number)
            );
        """
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_whatsapp_sessions_phone ON whatsapp_sessions(phone_number, tenant_id);"
        )

        # 2. Clean up whatsapp_conversations (ensure it's a log)
        # We don't drop columns to avoid breaking other potential dependencies,
        # but we ensure it has the right indexes.
        logger.info("Ensuring whatsapp_conversations is optimized for logging...")
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_whatsapp_conv_phone_tenant ON whatsapp_conversations(phone_number, tenant_id);"
        )

        # 3. Migrate existing state from conversations to sessions
        logger.info("Migrating existing session state...")
        cur.execute(
            """
            INSERT INTO whatsapp_sessions (tenant_id, phone_number, current_node_id, account_alias, is_bot_active)
            SELECT DISTINCT ON (tenant_id, phone_number)
                   tenant_id, phone_number, current_node_id, account_alias, is_bot_active
            FROM whatsapp_conversations
            WHERE phone_number IS NOT NULL
            ORDER BY tenant_id, phone_number, id DESC
            ON CONFLICT (tenant_id, phone_number) DO NOTHING;
        """
        )

        logger.info("Migration completed successfully.")
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise e
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    migrate()
