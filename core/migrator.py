import fcntl
import logging
import time

from alembic import command
from alembic.config import Config
from alembic.util.exc import CommandError

logger = logging.getLogger("OmniCore.Migrator")


def run_resilient_migrations():
    """
    Ejecuta las migraciones de Alembic de forma resiliente.
    Utiliza un bloqueo de archivo no bloqueante con timeout para evitar
    que el servidor se congele en entornos multi-worker.
    """
    lock_file = "/tmp/alembic.lock"
    timeout = 30  # Segundos máximos de espera
    start_time = time.time()

    try:
        f = open(lock_file, "w")
    except OSError as e:
        logger.error(f"❌ No se pudo abrir el archivo de bloqueo: {e}")
        return

    try:
        while True:
            try:
                # Intentar obtener bloqueo exclusivo NO bloqueante
                fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
                logger.info("🔒 Lock de migración adquirido exitosamente.")
                break
            except BlockingIOError:
                if time.time() - start_time > timeout:
                    logger.warning(
                        f"⚠️ Timeout de {timeout}s alcanzado esperando lock de migración. "
                        "Es posible que otra instancia esté migrando o haya un lock huérfano. "
                        "Procediendo con el arranque para evitar el congelamiento del sistema."
                    )
                    return

                logger.info(
                    "⏳ Otra instancia está ejecutando las migraciones. Reintentando en 2s..."
                )
                time.sleep(2)

        alembic_cfg = Config("alembic.ini")
        try:
            logger.info("🚀 Ejecutando migraciones (upgrade head)...")
            command.upgrade(alembic_cfg, "head")
            logger.info("✅ Migraciones aplicadas con éxito.")
        except CommandError as e:
            if "Can't locate revision" in str(e):
                logger.warning("⚠️ Historial de Alembic desincronizado. Corrigiendo (stamp head)...")
                command.stamp(alembic_cfg, "head")
                logger.info("✅ Historial de Alembic corregido.")
            else:
                logger.error(f"❌ Error en migraciones: {e}")
                raise e
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)
    finally:
        f.close()
