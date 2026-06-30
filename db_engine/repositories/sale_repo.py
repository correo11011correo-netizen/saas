from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from db_engine.repositories.base_repo import BaseRepository


class SaleModel:
    pass


class SaleRepository(BaseRepository[SaleModel]):
    def __init__(self, session: Session):
        super().__init__(SaleModel, session)

    def create_sale(self, data: dict[str, Any]) -> Any:
        result = self.session.execute(
            text("""
                INSERT INTO sales (id, tenant_id, cliente, customer_id, total, metodo_pago, paga_con, vuelto)
                VALUES (:id, :tid, :cliente, :cid, :total, :metodo, :paga, :vuelto)
            """),
            data,
        )
        return result

    def create_sale_item(self, data: dict[str, Any]):
        self.session.execute(
            text("""
                INSERT INTO sale_items (id, tenant_id, sale_id, product_code, quantity, price, subtotal)
                VALUES (:id, :tid, :sid, :code, :qty, :price, :sub)
            """),
            data,
        )

    def create_order(self, data: dict[str, Any]) -> int:
        result = self.session.execute(
            text("""
                INSERT INTO sales_orders (tenant_id, total, payment_status, client_request_id)
                VALUES (:tid, :total, 'pending', :rid) RETURNING id
            """),
            data,
        ).scalar()
        return result

    def add_order_item(self, data: dict[str, Any]):
        self.session.execute(
            text("""
                INSERT INTO sale_items (tenant_id, sale_id, product_code, quantity, price, subtotal)
                VALUES (:tid, :sid, :code, :qty, :price, :sub)
            """),
            data,
        )

    def update_order_status(self, order_id: Any, tenant_id: Any, status: str) -> float | None:
        result = (
            self.session.execute(
                text("""
                UPDATE sales_orders
                SET payment_status = :status
                WHERE id = :id AND tenant_id = :tid
                RETURNING total
            """),
                {"status": status, "id": order_id, "tid": tenant_id},
            )
            .mappings()
            .first()
        )
        return result["total"] if result else None

    def update_order_link(self, order_id: Any, link: str):
        self.session.execute(
            text("UPDATE sales_orders SET payment_link = :link WHERE id = :id"),
            {"link": link, "id": order_id},
        )
