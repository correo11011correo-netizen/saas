from sqlalchemy import JSON, Column, DateTime, func
from sqlalchemy.ext.declarative import declarative_base


# Nueva Base para NexusDB
# Todos los modelos que hereden de NexusBase tendrán automáticamente:
# 1. created_at: Fecha de creación automática
# 2. updated_at: Fecha de actualización automática
# 3. metadata_json: Campo JSON para extensiones flexibles (sin necesidad de migraciones)
class NexusBase:
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    metadata_json = Column(JSON, nullable=True)


# Definición de la Base declarativa real
Base = declarative_base(cls=NexusBase)
