from typing import List
from uuid import UUID
from application.state import state
from domain.entities import Product
from infrastructure.providers.base import BaseProvider


class StockService:
    """
    Servicio de Stock: Lógica de existencias y movimientos.
    Aislación total de la base de datos.
    """

    def __init__(self):
        self.state = state

    def _get_provider(self) -> BaseProvider:
        provider = self.state.get_provider("stock")
        if not provider:
            raise Exception("Stock provider not connected.")
        return provider

    def add_or_update_product(
        self, tenant_id: UUID, user_id: UUID, data: dict
    ) -> Product:
        provider = self._get_provider()

        # Buscar si existe
        product = provider.get(data["code"])
        if product:
            product.name = data.get("name", product.name)
            product.price = data.get("price", product.price)
            product.quantity += data.get("quantity", 0)
        else:
            product = Product(
                code=data["code"],
                name=data["name"],
                price=data["price"],
                quantity=data["quantity"],
                tenant_id=tenant_id,
            )

        saved_product = provider.save(product)

        # Registrar movimiento
        if hasattr(provider, "add_movement"):
            provider.add_movement(
                code=product.code,
                quantity=data.get("quantity", 0),
                reason="MANUAL_UPDATE",
                user_id=user_id,
                tenant_id=tenant_id,
            )

        return saved_product

    def update_quantity(
        self,
        code: str,
        tenant_id: UUID,
        user_id: UUID,
        delta: int,
        reason: str = "MANUAL",
    ) -> Product:
        provider = self._get_provider()
        product = provider.get(code)

        if not product:
            raise ValueError(f"Product {code} not found")

        if product.quantity + delta < 0:
            raise ValueError("Insufficient stock for this operation")

        product.quantity += delta
        saved_product = provider.save(product)

        if hasattr(provider, "add_movement"):
            provider.add_movement(
                code=code,
                quantity=delta,
                reason=reason,
                user_id=user_id,
                tenant_id=tenant_id,
            )

        return saved_product

    def get_critical_stock(self, tenant_id: UUID, threshold: int = 5) -> List[Product]:
        provider = self._get_provider()
        all_products = provider.list({"tenant_id": tenant_id})
        return [p for p in all_products if p.quantity < threshold]


# Singleton instance
stock_service = StockService()
