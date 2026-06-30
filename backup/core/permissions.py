import uuid

from sqlalchemy import Boolean, Column, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from db_engine.core.base_model import Base


class Permission(Base):
    """
    Define una capacidad granular dentro del sistema.
    Ejemplos: 'can_manage_stock', 'can_process_refunds', 'can_view_revenue'.
    """

    __tablename__ = "permissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(100), unique=True, nullable=False)  # Ej: 'sale.create'
    description = Column(String(255))
    module = Column(String(50))  # Ej: 'sales', 'stock', 'admin'


class PlanPermission(Base):
    """
    Mapea qué permisos están incluidos en cada plan (Free, Pro, Enterprise).
    """

    __tablename__ = "plan_permissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_name = Column(String(50), nullable=False, index=True)  # 'free', 'pro', 'enterprise'
    permission_id = Column(UUID(as_uuid=True), ForeignKey("permissions.id"), nullable=False)

    permission = relationship("Permission")


class UserPermission(Base):
    """
    Asignaciones específicas de permisos a usuarios.
    Permite que el administrador del tenant otorgue o revoque permisos individuales.
    """

    __tablename__ = "user_permissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    permission_id = Column(UUID(as_uuid=True), ForeignKey("permissions.id"), nullable=False)
    is_granted = Column(Boolean, default=True)  # True = Otorgado, False = Revocado explícitamente

    permission = relationship("Permission")
