import logging

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger("OmniCore.Deployment")


class DeploymentValidator:
    """
    Validador de salud pre-arranque.
    Asegura que la infraestructura esté lista antes de iniciar la API.
    """

    def __init__(self, engine):
        self.engine = engine

    def validate_all(self) -> bool:
        logger.info("🔍 Iniciando validación de despliegue (Pre-flight checks)...")

        checks = [
            (self.check_db_connectivity, "Conectividad de Base de Datos"),
            (self.check_migration_lock, "Verificación de Bloqueos de Migración"),
        ]

        all_passed = True
        for check_func, name in checks:
            try:
                if not check_func():
                    logger.error(f"❌ {name} FALLÓ")
                    all_passed = False
            except Exception as e:
                logger.error(f"❌ {name} generó un error crítico: {e}")
                all_passed = False

        if all_passed:
            logger.info("✅ Todos los chequeos de despliegue pasaron exitosamente.")
        else:
            logger.warning("⚠️ El sistema inició con advertencias de validación.")

        return all_passed

    def check_db_connectivity(self) -> bool:
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("  - Conectividad DB: OK")
            return True
        except SQLAlchemyError as e:
            logger.error(f"  - Conectividad DB: FALLO ({e})")
            return False

    def check_migration_lock(self) -> bool:
        """
        Verifica si hay transacciones que puedan bloquear las migraciones.
        Detecta tanto transacciones activas largas como sesiones 'idle in transaction'.
        """
        try:
            with self.engine.connect() as conn:
                # Consultar transacciones que pueden bloquear:
                # 1. Activas por más de 30 segundos
                # 2. En estado 'idle in transaction' (esto es crítico en Postgres)
                query = text("""
                    SELECT pid, state, now() - xact_start as duration
                    FROM pg_stat_activity
                    WHERE (state = 'active' AND (now() - xact_start) > interval '30 seconds')
                       OR (state = 'idle in transaction')
                       AND query NOT LIKE '%pg_stat_activity%';
                """)
                result = conn.execute(query).fetchall()

                if result:
                    logger.warning(
                        f"⚠️ Bloqueos potenciales detectados: {len(result)} sesiones conflictivas."
                    )
                    for row in result:
                        logger.warning(f"  - PID {row[0]}: Estado '{row[1]}', Duración: {row[2]}")
                    logger.warning(
                        "Sugerencia: Reinicia la base de datos o mata los PIDs indicados para liberar las tablas."
                    )
                    return False

                logger.info("  - Bloqueos de Migración: Ninguno detectado")
                return True
        except Exception as e:
            logger.error(f"  - Error verificando bloqueos: {e}")
            return False
