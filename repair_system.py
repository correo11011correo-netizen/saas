import json
import logging
import uuid

import psycopg2

DB_URL = (
    "postgresql://postgres:TFralZyHIJnjyZrNMtoDqqtUlPTsttvT@thomas.proxy.rlwy.net:24031/railway"
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SystemRepair")


def repair():
    conn = None
    try:
        logger.info("Starting system-wide repair for WhatsApp Bot...")
        conn = psycopg2.connect(DB_URL)
        conn.autocommit = True
        cur = conn.cursor()

        # 1. Ensure all tenants have bot_settings
        logger.info("Repairing bot_settings...")
        cur.execute("SELECT id, name FROM tenants")
        tenants = cur.fetchall()

        for tid, name in tenants:
            # Create bot_settings if missing
            cur.execute(
                """
                INSERT INTO bot_settings (tenant_id, bot_name, welcome_message, farewell_message, handoff_message, support_email, is_global_active)
                VALUES (%s, %s, %s, %s, %s, %s, TRUE)
                ON CONFLICT (tenant_id) DO NOTHING
            """,
                (
                    str(tid),
                    f"Asistente de {name}",
                    f"¡Hola! Bienvenido a {name}. 🤖",
                    f"Gracias por contactar a {name}. 👋",
                    f"He pasado el chat a un humano de {name}. 👨‍💻",
                    f"soporte@{name.lower().replace(' ', '-')}.com",
                ),
            )

            # 2. Ensure all tenants have 'Principal' credentials
            cur.execute(
                """
                INSERT INTO credentials (id, tenant_id, service_name, account_alias, api_key, metadata)
                VALUES (%s, %s, 'whatsapp', 'whatsapp', '', %s)
                ON CONFLICT (tenant_id, service_name, account_alias) DO NOTHING
            """,
                (str(uuid.uuid4()), str(tid), json.dumps({"phone_number_id": ""})),
            )

        logger.info(f"Successfully repaired {len(tenants)} tenants.")
        logger.info("System repair completed.")

    except Exception as e:
        logger.error(f"Repair failed: {e}")
        raise e
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    repair()
