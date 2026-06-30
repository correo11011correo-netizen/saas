from collections.abc import Sequence
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from db_engine.repositories.base_repo import BaseRepository


class ProductModel:
    pass


class ProductRepository(BaseRepository[ProductModel]):
    def __init__(self, session: Session):
        super().__init__(ProductModel, session)

    def list_all(self, tenant_id: Any) -> Sequence[dict]:
        result = (
            self.session.execute(
                text("SELECT * FROM products WHERE tenant_id = :tid ORDER BY name ASC"),
                {"tid": tenant_id},
            )
            .mappings()
            .all()
        )
        return [dict(row) for row in result]

    def get_by_code(self, code: str, tenant_id: Any) -> dict | None:
        result = (
            self.session.execute(
                text("SELECT * FROM products WHERE code = :code AND tenant_id = :tid"),
                {"code": code, "tid": tenant_id},
            )
            .mappings()
            .first()
        )
        return dict(result) if result else None

    def upsert(self, data: dict[str, Any]) -> None:
        self.session.execute(
            text("""
                INSERT INTO products (code, name, price, quantity, category, is_weight, tenant_id)
                VALUES (:code, :name, :price, :quantity, :category, :is_weight, :tid)
                ON CONFLICT (code, tenant_id) DO UPDATE
                SET name = EXCLUDED.name, price = EXCLUDED.price, quantity = EXCLUDED.quantity,
                    category = EXCLUDED.category, is_weight = EXCLUDED.is_weight
            """),
            data,
        )

    def update_quantity(self, code: str, tenant_id: Any, quantity_delta: int) -> int | None:
        # Using FOR UPDATE to prevent race conditions (Atomic update)
        result = self.session.execute(
            text("""
                UPDATE products
                SET quantity = quantity + :delta
                WHERE code = :code AND tenant_id = :tid
                RETURNING quantity
            """),
            {"delta": quantity_delta, "code": code, "tid": tenant_id},
        ).scalar()
        return result

    def get_critical_stock(self, tenant_id: Any, threshold: int) -> Sequence[dict]:
        result = (
            self.session.execute(
                text(
                    "SELECT code, name, quantity FROM products WHERE tenant_id = :tid AND quantity <= :threshold ORDER BY quantity ASC"
                ),
                {"tid": tenant_id, "threshold": threshold},
            )
            .mappings()
            .all()
        )
        return [dict(row) for row in result]

    def add_movement(self, code: str, quantity: int, reason: str, user_id: Any, tenant_id: Any):
        self.session.execute(
            text(
                "INSERT INTO stock_movements (product_code, quantity, reason, user_id, tenant_id) VALUES (:code, :qty, :reason, :uid, :tid)"
            ),
            {"code": code, "qty": quantity, "reason": reason, "uid": user_id, "tid": tenant_id},
        )
