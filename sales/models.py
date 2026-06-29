import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID

from core.database import Base


class Sale(Base):
    __tablename__ = "sales"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    cliente = Column(String(255))
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"))
    total = Column(Numeric(12, 2), default=0.0)
    metodo_pago = Column(String(50))
    paga_con = Column(Numeric(12, 2))
    vuelto = Column(Numeric(12, 2))
    client_request_id = Column(UUID(as_uuid=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SaleItem(Base):
    __tablename__ = "sale_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    sale_id = Column(UUID(as_uuid=True), ForeignKey("sales.id"), nullable=False)
    product_code = Column(String(100), nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(Numeric(12, 2), nullable=False)
    subtotal = Column(Numeric(12, 2), nullable=False)


class CashBox(Base):
    __tablename__ = "cash_box"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    abierta = Column(Boolean, default=False)
    efectivo_inicial = Column(Numeric(12, 2), default=0.0)
    ventas_efectivo = Column(Numeric(12, 2), default=0.0)
    ventas_digital = Column(Numeric(12, 2), default=0.0)
    hora_apertura = Column(DateTime(timezone=True))


class Alias(Base):
    __tablename__ = "aliases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    nombre = Column(String(100), nullable=False)
    limite = Column(Numeric(12, 2), default=0.0)
    acumulado = Column(Numeric(12, 2), default=0.0)
