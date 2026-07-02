import os
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger("OmniCore.Database")

class DatabaseManager:
    """
    Gestor de Conexiones Resiliente.
    Permite que el sistema arranque sin DB y se reconecte dinámicamente.
    """
    def __init__(self):
        self._engine = None
        self._SessionLocal = None
        self._is_connected = False
        self.initialize()

    def initialize(self):
        """Inicializa el engine y la sesión basándose en el entorno."""
        self.db_url = os.getenv("DATABASE_URL")
        if not self.db_url:
            logger.warning("DATABASE_URL not set. System running in disconnected mode.")
            self._is_connected = False
            return

        try:
            self._engine = create_engine(
                self.db_url, 
                pool_pre_ping=True, # Verifica la conexión antes de cada uso
                pool_recycle=3600
            )
            self._SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self._engine)
            
            # Prueba de conexión inmediata
            with self._engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            self._is_connected = True
            logger.info("Database connected successfully.")
        except SQLAlchemyError as e:
            logger.error(f"Database connection failed: {e}")
            self._is_connected = False
            self._engine = None
            self._SessionLocal = None

    def reconnect(self) -> bool:
        """Fuerza la re-inicialización de la conexión."""
        logger.info("Attempting to reconnect to database...")
        self.initialize()
        return self._is_connected

    def get_session(self) -> Session:
        """
        Retorna una sesión de DB. 
        Lanza una excepción controlada si no hay conexión.
        """
        if not self._SessionLocal:
            # Intentar inicializar si no se había podido antes
            self.initialize()
            if not self._SessionLocal:
                raise ConnectionError("Database not connected. Please check Sentry Panel.")
        
        return self._SessionLocal()

    @property
    def is_connected(self) -> bool:
        return self._is_connected

    @property
    def url(self) -> str:
        return self.db_url or "Not configured"

# Singleton instance
db_manager = DatabaseManager()

def get_db():
    """Generator for FastAPI dependency injection."""
    try:
        db = db_manager.get_session()
        try:
            yield db
        finally:
            db.close()
    except ConnectionError as e:
        logger.error(f"get_db failed: {e}")
        yield None
