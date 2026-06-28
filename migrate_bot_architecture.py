import logging
import os

import psycopg2

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Migration")

DB_URL = os.getenv("DATABASE_URL")
if not DB_URL:
    raise Exception("DATABASE_URL variable not set")


def migrate():
    conn = None
    try:
        conn = psycopg2.connect(DB_URL)
        conn.autocommit = True
        cur = conn.cursor()

        logger.info("Starting bot architecture migration...")

        # 1. Create bot_assignments table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS bot_assignments (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                tenant_id UUID REFERENCES tenants(id),
                credential_id UUID REFERENCES credentials(id),
                bot_profile_id UUID REFERENCES bot_profiles(id),
                is_primary BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (tenant_id, credential_id)
            );
        """)
        logger.info("✅ Table 'bot_assignments' created.")

        # 2. Add bot_profile_id to bot_nodes
        cur.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='bot_nodes' AND column_name='bot_profile_id') THEN
                    ALTER TABLE bot_nodes ADD COLUMN bot_profile_id UUID REFERENCES bot_profiles(id);
                END IF;
            END $$;
        """)
        logger.info("✅ Column 'bot_profile_id' added to 'bot_nodes'.")

        # 3. Add bot_profile_id to bot_options
        cur.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='bot_options' AND column_name='bot_profile_id') THEN
                    ALTER TABLE bot_options ADD COLUMN bot_profile_id UUID REFERENCES bot_profiles(id);
                END IF;
            END $$;
        """)
        logger.info("✅ Column 'bot_profile_id' added to 'bot_options'.")

        # 4. Migrate data from account_alias to bot_profile_id
        # For bot_nodes
        cur.execute("""
            UPDATE bot_nodes bn
            SET bot_profile_id = bp.id
            FROM bot_profiles bp
            WHERE bn.account_alias = bp.account_alias AND bn.tenant_id = bp.tenant_id;
        """)
        logger.info("✅ Migrated 'bot_nodes' account_alias -> bot_profile_id.")

        # For bot_options
        cur.execute("""
            UPDATE bot_options bo
            SET bot_profile_id = bp.id
            FROM bot_profiles bp
            WHERE bo.account_alias = bp.account_alias AND bo.tenant_id = bp.tenant_id;
        """)
        logger.info("✅ Migrated 'bot_options' account_alias -> bot_profile_id.")

        # 5. (Optional) Now we could remove account_alias, but for safety we'll keep it
        # until we verify the backend is fully updated.

        logger.info("Migration completed successfully.")

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise e
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    migrate()
