import uuid

import func
from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID

from db_engine.core.base_model import Base


class DevLog(Base):
    """
    Registro detallado de ejecuciones para modo desarrollo.
    Almacena la traza completa de comandos, parámetros y respuestas.
    """

    __tablename__ = "dev_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime, default=func.now(), index=True)

    # Detalles de la ejecución
    command = Column(String(255), nullable=False, index=True)
    params = Column(JSON, nullable=True)
    result = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    execution_time_ms = Column(Integer, nullable=True)

    # Contexto
    user_id = Column(UUID(as_uuid=True), nullable=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=True)
    role = Column(String(50), nullable=True)

    # Metadatos del entorno
    environment = Column(String(50), default="dev")
    trace_id = Column(String(100), nullable=True)
