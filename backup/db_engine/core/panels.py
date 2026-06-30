import uuid

from sqlalchemy import JSON, Boolean, Column, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID

from db_engine.core.base_model import Base


class PanelDefinition(Base):
    """
    Define un panel de la UI dinámicamente.
    Permite crear paneles globales, por rol o personalizados por cliente.
    """

    __tablename__ = "panel_definitions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    panel_id = Column(String(100), nullable=False, index=True)  # Ej: 'sales.pos', 'admin.stats'
    name = Column(String(100), nullable=False)
    config_json = Column(JSON, nullable=False)  # Layout, iconos, componentes, etc.

    # Jerarquía de Acceso
    required_role = Column(
        String(50), nullable=True
    )  # 'admin', 'employee', 'support', 'superadmin'
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=True, index=True)

    is_active = Column(Boolean, default=True)
    priority = Column(String(10), default="0")  # Para ordenar los paneles en el dock
