import logging

from sqlalchemy import text

from db_engine.core.engine import nexus_db
from db_engine.core.panel_seeder import seed_ui_panels
from db_engine.core.permissions_data import PLAN_PERMISSIONS_MAP, SYSTEM_PERMISSIONS
from db_engine.repositories.permission_repo import PermissionRepository
from db_engine.sync.stock_migrator import OmniStockMigrator

logging.basicConfig(level=logging.INFO)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("NexusDB-Bootstrap")


class NexusBootstrap:
    """
    Orquestador de arranque del sistema.
    Detecta el estado de la DB y aplica la configuración necesaria:
    - Fresh Start: Crea tablas y carga semilla.
    - Update: Migra datos antiguos al nuevo esquema.
    """

    def __init__(self):
        self.db = nexus_db

    def initialize(self):
        logger.info("🚀 Iniciando NexusDB Bootstrap...")

        with self.db.session() as session:
            try:
                # 0. Garantizar Esquema de Paneles (Auto-migración rápida)
                self._ensure_panel_schema(session)

                # 1. Verificar si la base de datos está vacía o es antigua
                if self._is_db_empty(session):
                    logger.info("Empty database detected. Performing Fresh Start...")
                    self._fresh_start(session)
                else:
                    logger.info("Existing database detected. Checking for updates...")
                    self._handle_migration(session)

                # 2. Sincronizar Permisos del Sistema (Siempre se hace para añadir nuevos en actualizaciones)
                self._sync_permissions(session)

                # 3. Sincronizar Paneles de UI (Asegura que la estructura de la interfaz sea consistente)
                seed_ui_panels(session)

                logger.info("✅ NexusDB Bootstrap completed successfully.")
            except Exception as e:
                logger.exception(f"❌ Critical error during bootstrap: {e}")
                raise e

    def _ensure_panel_schema(self, session):
        """
        Auto-migración para la tabla de paneles.
        Asegura que la tabla exista antes de que el seeder intente cargar datos.
        """
        logger.info("Checking UI panel schema...")
        session.execute(
            text("""
                CREATE TABLE IF NOT EXISTS panel_definitions (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    panel_id VARCHAR(100) UNIQUE NOT NULL,
                    name VARCHAR(100) NOT NULL,
                    config_json JSONB NOT NULL,
                    required_role VARCHAR(50),
                    tenant_id UUID REFERENCES tenants(id),
                    is_active BOOLEAN DEFAULT true,
                    priority VARCHAR(10) DEFAULT '0',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            """)
        )
        session.commit()

    def _is_db_empty(self, session) -> bool:
        """Verifica si la tabla de tenants existe y tiene datos."""
        try:
            result = session.execute(text("SELECT count(*) FROM tenants"))
            return result.scalar() == 0
        except Exception:
            return True  # Si la tabla no existe, se considera vacía

    def _fresh_start(self, session):
        """Prepara la base de datos desde cero."""
        logger.info("Performing Fresh Start initialization...")
        # Hemos eliminado self.db.create_tables() porque el esquema ya es gestionado
        # por SchemaSync en el arranque del servidor.
        # Aquí solo cargaríamos datos semilla básicos si fueran necesarios.

    def _handle_migration(self, session):
        """
        Detecta si la base de datos es la versión antigua (Sin variantes)
        y ejecuta la migración a OmniStock.
        """
        # Verificamos si existe la tabla 'product_variants'
        try:
            session.execute(text("SELECT 1 FROM product_variants LIMIT 1"))
            logger.info("OmniStock schema already present. Skipping migration.")
        except Exception:
            logger.warning("Legacy stock detected! Running OmniStock Migration...")
            migrator = OmniStockMigrator(session)
            if migrator.migrate_existing_data():
                logger.info("Legacy data migrated to OmniStock successfully.")
            else:
                logger.error("OmniStock migration failed!")

    def _sync_permissions(self, session):
        """Carga y sincroniza las capacidades y los permisos de los planes."""
        logger.info("Syncing system permissions and plan mappings...")
        perm_repo = PermissionRepository(session)

        # 1. Sincronizar la lista maestra de permisos
        perm_repo.sync_system_permissions(SYSTEM_PERMISSIONS)

        # 2. Sincronizar los permisos de los planes
        from core.permissions import Permission, PlanPermission

        for plan, perms_codes in PLAN_PERMISSIONS_MAP.items():
            # Limpiar permisos actuales del plan para evitar duplicados
            session.query(PlanPermission).filter(PlanPermission.plan_name == plan).delete()

            # Añadir permisos definidos en el mapa
            for code in perms_codes:
                perm = session.query(Permission).filter(Permission.code == code).first()
                if perm:
                    plan_perm = PlanPermission(plan_name=plan, permission_id=perm.id)
                    session.add(plan_perm)

        session.commit()


# Singleton para el proceso de arranque
bootstrap = NexusBootstrap()
