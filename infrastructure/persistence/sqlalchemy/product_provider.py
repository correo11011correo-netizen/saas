from uuid import UUID
from infrastructure.persistence.sqlalchemy.base_provider import SqlAlchemyProvider
from domain.entities import Product
from stock.models import Product as DBProduct


class ProductSqlProvider(SqlAlchemyProvider):
    def _to_domain(self, db_model: DBProduct) -> Product:
        return Product(
            id=db_model.id,
            code=db_model.code,
            name=db_model.name,
            price=float(db_model.price),
            quantity=db_model.quantity,
            tenant_id=db_model.tenant_id,
        )

    def _to_db(self, entity: Product) -> DBProduct:
        return DBProduct(
            id=entity.id,
            code=entity.code,
            name=entity.name,
            price=entity.price,
            quantity=entity.quantity,
            tenant_id=entity.tenant_id,
        )

    def add_movement(
        self, code: str, quantity: int, reason: str, user_id: UUID, tenant_id: UUID
    ):
        # Implementación específica para movimientos de stock
        from stock.models import StockMovement

        with self.session_factory() as session:
            movement = StockMovement(
                product_code=code,
                quantity=quantity,
                reason=reason,
                user_id=user_id,
                tenant_id=tenant_id,
            )
            session.add(movement)
            session.commit()
