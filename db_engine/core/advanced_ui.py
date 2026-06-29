import uuid

import func
from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID

from db_engine.core.base_model import Base


class ComponentLibrary(Base):
    """
    Catálogo de componentes UI disponibles en el sistema.
    Define qué 'piezas' existen (ej: ChatWindow, FileGrid, BotControl)
    y cuáles son sus propiedades requeridas.
    """

    __tablename__ = "component_library"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    component_id = Column(String(100), unique=True, nullable=False)  # ej: 'chat_window'
    name = Column(String(100), nullable=False)
    description = Column(String(255))
    default_props = Column(JSON, nullable=False)  # Propiedades por defecto
    allowed_roles = Column(JSON, nullable=True)  # Roles que pueden usar este componente
    is_active = Column(Boolean, default=True)


class PanelComponent(Base):
    """
    Relaciona paneles con componentes específicos.
    Permite que un panel sea una composición de varios componentes.
    """

    __tablename__ = "panel_components"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    panel_id = Column(UUID(as_uuid=True), ForeignKey("panel_definitions.id"), nullable=False)
    component_id = Column(UUID(as_uuid=True), ForeignKey("component_library.id"), nullable=False)

    # Configuración específica de este componente en este panel
    props_override = Column(JSON, nullable=True)
    position = Column(Integer, default=0)  # Orden de renderizado
    grid_area = Column(String(50), nullable=True)  # Para layouts complejos (CSS Grid)

    is_active = Column(Boolean, default=True)


class MediaAsset(Base):
    """
    Gestión de archivos y adjuntos para chats, bots y paneles.
    Soporta cualquier tipo de archivo.
    """

    __tablename__ = "media_assets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    file_name = Column(String(255), nullable=False)
    file_type = Column(String(100), nullable=False)  # mime-type
    file_path = Column(String(512), nullable=False)  # Path en storage
    file_size = Column(Integer, nullable=False)  # bytes
    checksum = Column(String(64), nullable=True)  # SHA256 para evitar duplicados

    created_at = Column(DateTime, default=func.now())
