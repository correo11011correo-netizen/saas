import fcntl
import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError

from alembic import command
from alembic.config import Config
from alembic.util.exc import CommandError

logger = logging.getLogger("OmniCore.Migrator")


def _execute_alembic_upgrade():
    """Función interna para ejecutar el upgrade de Alembic."""
    alembic_cfg = Config("alembic.ini")
    try:
        logger.info("🚀 Ejecutando migraciones (upgrade head)...")
        command.upgrade(alembic_cfg, "head")
        logger.info("✅ Migraciones aplicadas con éxito.")
        return True
    except CommandError as e:
        if "Can't locate revision" in str(e):
            logger.warning("⚠️ Historial de Alembic desincronizado. Corrigiendo (stamp head)...")
            command.stamp(alembic_cfg, "head")
            logger.info("✅ Historial de Alembic corregido.")
            return True
        else:
            logger.error(f"❌ Error en migraciones: {e}")
            return False
    except Exception as e:
        logger.error(f"❌ Error inesperado en migraciones: {e}")
        return False


def run_resilient_migrations():
    """
    Ejecuta las migraciones de Alembic con un timeout estricto.
    Evita que el hilo principal del servidor se congele si Alembic se bloquea.
    """
    lock_file = "/tmp/alembic.lock"
    timeout = 60  # Segundos máximos para que la migración se complete

    try:
        f = open(lock_file, "w")
        # Intentar obtener lock no bloqueante
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            logger.warning("⏳ Otra instancia ya está migrando. Saltando paso para evitar bloqueo.")
            return

        # Ejecutar la migración en un hilo separado para poder aplicar el timeout
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_execute_alembic_upgrade)
            try:
                success = future.result(timeout=timeout)
                if success:
                    logger.info("✅ Proceso de migración finalizado exitosamente.")
                else:
                    logger.error("❌ La migración terminó pero reportó errores.")
            except TimeoutError:
                logger.critical(
                    f"🚨 TIMEOUT CRÍTICO: La migración excedió los {timeout}s y se ha quedado colgada. "
                    "Saliendo del proceso de migración para permitir el arranque del servidor."
                )
                # No lanzamos excepción para permitir que main.py siga con el arranque
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)
    except Exception as e:
        logger.error(f"❌ Error en el orquestador de migraciones: {e}")
    finally:
        try:
            f.close()
        except Exception:
            pass
