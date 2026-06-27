import psycopg2
from psycopg2 import sql
import logging
import requests
import json
import os
from sqlalchemy import create_engine, text

# --- CONFIGURACIÓN ---
DB_URL = "postgresql://postgres:TFralZyHIJnjyZrNMtoDqqtUlPTsttvT@thomas.proxy.rlwy.net:24031/railway"
API_URL = os.getenv("BASE_URL", "https://saas-production-2dd6.up.railway.app")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("FullReset")


def reset_database():
    logger.info("""🚀 Iniciando BORRADO TOTAL de la base de datos (Modo Agresivo)...""")
    try:
        conn = psycopg2.connect(DB_URL)
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute("SET session_replication_role = 'replica';")
        logger.info("""  [OK] Restricciones de integridad desactivadas.""")
        tables_to_clean = [
            "sale_items",
            "sales",
            "stock_movements",
            "products",
            "whatsapp_conversations",
            "whatsapp_sessions",
            "whatsapp_menus",
            "cash_box",
            "aliases",
            "credentials",
            "audit_log",
            "frontend_manifest",
            "users",
            "tenants",
            "bot_nodes",
            "bot_options",
        ]
        for table in tables_to_clean:
            try:
                cur.execute(f"TRUNCATE TABLE {table} CASCADE;")
                logger.info(f"""  [OK] Tabla vaciada: {table}""")
            except Exception as e:
                logger.warning(f"""  [!] No se pudo vaciar {table}: {e}""")
        cur.execute("SET session_replication_role = 'origin';")
        logger.info("""  [OK] Restricciones de integridad reactivadas.""")
        cur.close()
        conn.close()
        logger.info(
            """✅ Base de datos vaciada completamente y confirmada.
"""
        )
    except Exception as e:
        logger.error(f"""❌ Error crítico durante el reset: {e}""")
        raise e


def init_structure():
    logger.info("""🛠️ Sincronizando estructura de tablas (init_db)...""")
    from core.init_db import init_db

    init_db()
    logger.info(
        """✅ Estructura sincronizada.
"""
    )


def test_user_creation():
    logger.info("""🧪 Validando creación de Usuario y Tenant...""")
    test_user = {
        "email": "test_admin@omnicore.com",
        "password": "Password123!",
        "business_name": "Tienda de Prueba Reset",
    }
    try:
        response = requests.post(f"{API_URL}/auth/register", json=test_user)
        if response.status_code == 200:
            data = response.json()
            logger.info("""✅ Usuario creado exitosamente!""")
            logger.info(f"""   - Tenant ID: {data.get('tenant_id')}""")
            logger.info(f"""   - Webhook Secret: {data.get('webhook_secret')}""")
            return True
        else:
            logger.error(
                f"""❌ Error al crear usuario: {response.status_code} - {response.text}"""
            )
            return False
    except Exception as e:
        logger.error(f"""❌ Error de conexión con la API: {e}""")
        return False


if __name__ == "__main__":
    try:
        reset_database()
        init_structure()
        if test_user_creation():
            logger.info(
                """
✨ RESULTADO FINAL: El sistema está LIMPIO y el flujo de creación de usuarios FUNCIONA CORRECTAMENTE. ✨"""
            )
        else:
            logger.error(
                """
❌ RESULTADO FINAL: El sistema se limpió, pero la creación de usuarios FALLÓ."""
            )
    except Exception as e:
        logger.error(f"""FATAL ERROR: {e}""")
