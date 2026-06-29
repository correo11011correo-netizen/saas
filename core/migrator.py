import logging

from alembic import command
from alembic.config import Config
from alembic.util.exc import CommandError

logger = logging.getLogger("OmniCore.Migrator")


def run_resilient_migrations():
    """
    Ejecuta las migraciones de Alembic de forma resiliente.
    Si falla por revisiones faltantes, intenta corregir el historial automáticamente.
    """
    alembic_cfg = Config("alembic.ini")

    try:
        logger.info("🚀 Intentando ejecutar migraciones (upgrade head)...")
        command.upgrade(alembic_cfg, "head")
        logger.info("✅ Migraciones aplicadas con éxito.")
    except CommandError as e:
        # Si el error es por una revisión faltante, intentamos corregir el estado
        if "Can't locate revision" in str(e):
            logger.warning(
                "⚠️ Historial de Alembic desincronizado. Intentando corregir (stamp head)..."
            )
            try:
                command.stamp(alembic_cfg, "head")
                logger.info("✅ Historial de Alembic corregido (stamp head).")
            except Exception as stamp_e:
                logger.error(f"❌ Error crítico intentando corregir el historial: {stamp_e}")
                raise stamp_e
        else:
            logger.error(f"❌ Error en migraciones: {e}")
            raise e
