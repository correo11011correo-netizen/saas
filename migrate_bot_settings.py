import psycopg2
import logging
import re

DB_URL = "postgresql://postgres:TFralZyHIJnjyZrNMtoDqqtUlPTsttvT@thomas.proxy.rlwy.net:24031/railway"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("BotMigration")


def simplify_name(name):
    """Simplifica el nombre del negocio para generar un email (ej: 'Gaseosas S.A.' -> 'gaseosas-sa')"""
    name = name.lower()
    name = re.sub(r"[^a-z0-9\s]", "", name)
    name = name.replace(" ", "-")
    return name


def migrate():
    conn = None
    try:
        logger.info("Connecting to database for Bot Settings migration...")
        conn = psycopg2.connect(DB_URL)
        conn.autocommit = True
        cur = conn.cursor()

        # 1. Create bot_settings table
        logger.info("Creating bot_settings table...")
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS bot_settings (
                tenant_id UUID PRIMARY KEY REFERENCES tenants(id),
                welcome_message TEXT,
                farewell_message TEXT,
                handoff_message TEXT,
                support_email VARCHAR(255),
                support_phone VARCHAR(50),
                bot_name VARCHAR(255),
                is_global_active BOOLEAN DEFAULT TRUE,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """
        )

        # 2. Populate existing tenants
        logger.info("Generating default settings for existing tenants...")
        cur.execute("SELECT id, name FROM tenants")
        tenants = cur.fetchall()

        for tid, name in tenants:
            simple_name = simplify_name(name)

            # Default values
            bot_name = f"Asistente de {name}"
            welcome = f"¡Hola! Bienvenido a {name}. 🤖 Soy tu asistente virtual. ¿En qué puedo ayudarte hoy?"
            farewell = f"Gracias por contactar a {name}. ¡Que tengas un gran día! 👋"
            handoff = f"He desactivado el bot. Un agente humano de {name} se pondrá en contacto contigo en breve. 👨‍💻"
            email = f"soporte@{simple_name}.com"

            cur.execute(
                """
                INSERT INTO bot_settings (tenant_id, bot_name, welcome_message, farewell_message, handoff_message, support_email, is_global_active)
                VALUES (%s, %s, %s, %s, %s, %s, TRUE)
                ON CONFLICT (tenant_id) DO NOTHING
            """,
                (tid, bot_name, welcome, farewell, handoff, email),
            )

        logger.info(f"Successfully processed {len(tenants)} tenants.")
        logger.info("Migration completed successfully.")

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise e
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    migrate()
