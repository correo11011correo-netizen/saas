import os
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

# Configuración de la URL de la base de datos
DB_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")
if not DB_URL:
    raise Exception("DATABASE_URL environment variable is not set")

# Crear el motor de SQLAlchemy
engine = create_engine(DB_URL, pool_pre_ping=True, pool_recycle=3600)

# Configurar la fábrica de sesiones
# scoped_session asegura que tengamos una sesión única por hilo/request
session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Session = scoped_session(session_factory)


@contextmanager
def db_session():
    """
    Context manager para gestionar la sesión de base de datos de forma segura.
    Garantiza que la sesión se cierre y maneja rollbacks automáticos en caso de error.
    """
    session = Session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        Session.remove()


def get_engine():
    """Retorna el motor de SQLAlchemy."""
    return engine
