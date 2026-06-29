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


def seed_initial_data(cur):
    """
    Puebla la base de datos con datos maestros esenciales para que el sistema sea operativo.
    """
    logger.info("Seeding initial system data...")

    # 1. Insertar Planes SaaS por defecto
    plans = [
        ("free", "Plan Gratuito", 0.0, '["basic_bot", "1_tenant"]'),
        ("pro", "Plan Profesional", 29.99, '["advanced_bot", "multi_bot", "priority_support"]'),
        (
            "enterprise",
            "Plan Empresarial",
            99.99,
            '["custom_bot", "dedicated_support", "unlimited_everything"]',
        ),
    ]
    for p_id, p_name, p_price, p_feats in plans:
        cur.execute(
            """
            INSERT INTO saas_plans (plan_id, name, monthly_price, features)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (plan_id) DO NOTHING
            """,
            (p_id, p_name, p_price, p_feats),
        )

    # 2. Crear SuperAdmin inicial si no existe
    # Se recomienda configurar estas variables en Railway: SUPERADMIN_EMAIL y SUPERADMIN_PASSWORD
    saas_email = os.getenv("SUPERADMIN_EMAIL", "admin@omnicore.system")
    saas_pass = os.getenv("SUPERADMIN_PASSWORD", "AdminSecure123!")

    cur.execute("SELECT 1 FROM users WHERE email = %s AND role = 'superadmin'", (saas_email,))
    if not cur.fetchone():
        import hashlib

        password_hash = hashlib.sha256(saas_pass.encode()).hexdigest()
        cur.execute(
            "INSERT INTO users (email, password_hash, role, tenant_id) VALUES (%s, %s, 'superadmin', NULL)",
            (saas_email, password_hash),
        )
        logger.info(f"Initial SuperAdmin created: {saas_email}")
    else:
        logger.info("SuperAdmin already exists, skipping creation.")


def init_db():
    max_retries = 3
    for attempt in range(max_retries):
        conn = None
        try:
            conn = psycopg2.connect(DB_URL)
            conn.autocommit = True
            cur = conn.cursor()

            # ... (Todo el código de creación de tablas se mantiene igual hasta el final) ...
            # [Sustitución del final de la función init_db]

            # 5. Seed Initial Data
            seed_initial_data(cur)

            logger.info("Database infrastructure initialized and seeded successfully.")
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
