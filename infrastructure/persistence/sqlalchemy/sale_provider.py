from typing import List
from infrastructure.persistence.sqlalchemy.base_provider import SqlAlchemyProvider
from domain.entities import Sale, SaleItem
from sales.models import Sale as DBSale, SaleItem as DBSaleItem


class SaleSqlProvider(SqlAlchemyProvider):
    def _to_domain(self, db_model: DBSale) -> Sale:
        # Recuperar items asociados
        items = []
        if hasattr(db_model, "items"):
            for item in db_model.items:
                items.append(
                    SaleItem(
                        product_code=item.product_code,
                        quantity=item.quantity,
                        price=float(item.price),
                    )
                )

        return Sale(
            id=db_model.id,
            customer_id=db_model.customer_id,
            total=float(db_model.total),
            tenant_id=db_model.tenant_id,
            items=items,
        )

    def _to_db(self, entity: Sale) -> DBSale:
        # El guardado de items se maneja habitualmente en la lógica del servicio
        # o mediante relaciones de SQLAlchemy.
        return DBSale(
            id=entity.id,
            customer_id=entity.customer_id,
            total=entity.total,
            tenant_id=entity.tenant_id,
        )

    def save_with_items(self, sale: Sale, items: List[SaleItem]):
        """
        Método extendido para manejar la persistencia atómica de la venta y sus items.
        """
        with self.session_factory() as session:
            db_sale = self._to_db(sale)
            session.merge(db_sale)

            for item in items:
                db_item = DBSaleItem(
                    id=item.id,
                    sale_id=sale.id,
                    product_code=item.product_code,
                    qty=item.quantity,
                    price=item.price,
                    tenant_id=sale.tenant_id,
                )
                session.add(db_item)

            session.commit()
            return sale
