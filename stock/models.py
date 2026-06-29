import enum
import uuid

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from db_engine.core.base_model import Base


class ProductType(enum.Enum):
    PHYSICAL = "physical"  # Stock numérico estándar
    SERVICE = "service"  # Sin stock, basado en capacidad/horas
    WEIGHTED = "weighted"  # Stock decimal (kilos, litros)
    DIGITAL = "digital"  # Entrega digital, stock infinito/limitado


class Product(Base):
    __tablename__ = "products"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    name = Column(String(255), nullable=False)
    category = Column(String(100))
    product_type = Column(Enum(ProductType), default=ProductType.PHYSICAL, nullable=False)

    # Relación con variantes
    variants = relationship(
        "ProductVariant", back_populates="product", cascade="all, delete-orphan"
    )


class ProductVariant(Base):
    __tablename__ = "product_variants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    code = Column(String(100), nullable=False, index=True)  # El SKU real
    name = Column(String(255))  # Ej: "Rojo - Talla M" o "100ml"
    price = Column(Numeric(12, 2), default=0.0)
    quantity = Column(Numeric(12, 2), default=0.0)  # Numeric para soportar WEIGHTED
    is_active = Column(Boolean, default=True)

    product = relationship("Product", back_populates="variants")


class StockMovement(Base):
    __tablename__ = "stock_movements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    variant_id = Column(UUID(as_uuid=True), ForeignKey("product_variants.id"), nullable=False)
    quantity = Column(Numeric(12, 2), nullable=False)
    reason = Column(String(255))
    user_id = Column(UUID(as_uuid=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
