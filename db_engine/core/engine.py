from db_engine.core.base_model import Base
from db_engine.core.session import db_session, get_engine


class NexusDB:
    """
    El Cerebro de NexusDB. Coordina el acceso a la base de datos,
    la gestión de sesiones y la ejecución de comandos de persistencia.
    """

    def __init__(self):
        self.engine = get_engine()
        self.base = Base

    def session(self):
        """Retorna el context manager de sesión."""
        return db_session()

    def create_tables(self):
        """
        Crea las tablas definidas en la Base.
        NOTA: En producción, esto debe ser reemplazado por Alembic.
        """
        self.base.metadata.create_all(self.engine)


# Instancia Singleton para ser utilizada en todo el proyecto
nexus_db = NexusDB()
