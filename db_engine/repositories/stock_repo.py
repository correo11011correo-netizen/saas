from typing import Any

from sqlalchemy.orm import Session

from db_engine.repositories.base_repo import BaseRepository
from stock.models import ProductVariant, StockMovement


class StockRepository(BaseRepository):
    """
    Manejo de Inventario Universal.
    Implementa el modelo Producto -> Variante para soportar cualquier tipo de negocio.
    """

    def __init__(self, session: Session):
        # El repositorio base ahora opera sobre la VARIANTE, que es lo que tiene el stock.
        super().__init__(ProductVariant, session)

    def get_variant_for_update(self, code: str, tenant_id: Any) -> ProductVariant | None:
        """
        Obtiene una variante bloqueando la fila (SELECT FOR UPDATE).
        Esencial para evitar colisiones en ventas masivas.
        """
        return (
            self.session.query(ProductVariant)
            .filter(ProductVariant.code == code, ProductVariant.tenant_id == tenant_id)
            .with_for_update()
            .first()
        )

    def get_variant_with_product(self, code: str, tenant_id: Any):
        """Retorna la variante y el producto padre asociado."""
        variant = (
            self.session.query(ProductVariant)
            .filter(ProductVariant.code == code, ProductVariant.tenant_id == tenant_id)
            .first()
        )

        if not variant:
            return None, None

        return variant, variant.product

    def update_stock(
        self, variant_id: Any, quantity_change: float, reason: str, user_id: Any = None
    ) -> ProductVariant | None:
        """
        Actualiza la cantidad de stock de una variante y registra el movimiento.
        Soporta decimales para productos pesados.
        """
        variant = self.get_by_id(variant_id)
        if not variant:
            return None

        # Validar que no quede stock negativo
        if variant.quantity + quantity_change < 0:
            raise ValueError(f"Stock insuficiente para la variante {variant.code}")

        variant.quantity += quantity_change

        # Registro obligatorio de movimiento vinculado a la variante
        movement = StockMovement(
            tenant_id=variant.tenant_id,
            variant_id=variant.id,
            quantity=quantity_change,
            reason=reason,
            user_id=user_id,
        )
        self.session.add(movement)

        self.session.flush()
        return variant
