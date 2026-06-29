import fcntl
import logging

from alembic import command
from alembic.config import Config
from alembic.util.exc import CommandError

logger = logging.getLogger("OmniCore.Migrator")


def run_resilient_migrations():
    """
    Ejecuta las migraciones de Alembic de forma resiliente con un bloqueo de archivo
    para evitar ejecuciones concurrentes en entornos multi-worker.
    """
    lock_file = "/tmp/alembic.lock"
    with open(lock_file, "w") as f:
        try:
            # Intentar obtener bloqueo exclusivo
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            logger.info("⏳ Otra instancia está ejecutando las migraciones. Esperando...")
            fcntl.flock(f, fcntl.LOCK_EX)  # Bloquea hasta que la otra instancia termine
            logger.info("✅ Otra instancia terminó. Continuando...")
            return

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
