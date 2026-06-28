import logging

from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from core.context import TenantContext
from core.decorators import command
from core.types import ServiceResponse

logger = logging.getLogger("OmniCore.StockCommands")


class ProductImportItem(BaseModel):
    code: str = Field(..., description="Unique SKU/code of the variant")
    name: str = Field(..., description="Name of the product")
    price: float = Field(..., gt=0, description="Unit price must be positive")
    quantity: int = Field(..., ge=0, description="Initial quantity")
    category: str | None = Field(None, description="Product category")
    is_weight: bool = Field(False, description="Whether the product is sold by weight")


class StockImportModel(BaseModel):
    products: list[ProductImportItem] = Field(
        ..., min_length=1, description="List of products to import"
    )


class StockCommandHandler:
    """
    Implementación de comandos de Stock Multi-tenant.
    Utiliza SQL directo para garantizar la independencia de repositorios.
    """

    @command(
        name="products.list",
        description="Retrieves all products for the current tenant.",
        params_model={},
    )
    def list_products(
        self,
        session: Session,
        context: TenantContext,
    ) -> ServiceResponse:
        try:
            result = (
                session.execute(
                    text("SELECT * FROM products WHERE tenant_id = :tid ORDER BY name ASC"),
                    {"tid": context.tenant_id},
                )
                .mappings()
                .all()
            )
            return ServiceResponse.success_res(
                data=[dict(row) for row in result],
                message="Products retrieved successfully.",
            )
        except Exception as e:
            return ServiceResponse.error_res(
                f"Error listing products: {str(e)}", "STOCK_LIST_ERROR"
            )

    @command(
        name="stock.add",
        description="Adds or updates a product for the current tenant.",
        params_model={
            "code": "string",
            "name": "string",
            "price": "float",
            "quantity": "int",
            "category": "string",
            "is_weight": "boolean",
        },
    )
    def add_product(
        self,
        session: Session,
        context: TenantContext,
        code: str,
        name: str,
        price: float,
        quantity: int,
        category: str | None = None,
        is_weight: bool = False,
    ) -> ServiceResponse:
        try:
            # Upsert product for this tenant
            session.execute(
                text(
                    """
                    INSERT INTO products (code, name, price, quantity, category, is_weight, tenant_id)
                    VALUES (:code, :name, :price, :quantity, :category, :is_weight, :tid)
                    ON CONFLICT (code, tenant_id) DO UPDATE
                    SET name = EXCLUDED.name, price = EXCLUDED.price, quantity = EXCLUDED.quantity, category = EXCLUDED.category, is_weight = EXCLUDED.is_weight
                """
                ),
                {
                    "code": code,
                    "name": name,
                    "price": price,
                    "quantity": quantity,
                    "category": category,
                    "is_weight": is_weight,
                    "tid": context.tenant_id,
                },
            )

            # Record movement
            session.execute(
                text(
                    "INSERT INTO stock_movements (product_code, quantity, reason, user_id, tenant_id) VALUES (:code, :qty, :reason, :uid, :tid)"
                ),
                {
                    "code": code,
                    "qty": quantity,
                    "reason": "INITIAL_LOAD" if quantity > 0 else "UPDATE",
                    "uid": context.user_id,
                    "tid": context.tenant_id,
                },
            )

            session.commit()
            return ServiceResponse.success_res(message=f"Product {name} processed successfully.")
        except Exception as e:
            session.rollback()
            return ServiceResponse.error_res(f"Error adding product: {str(e)}", "STOCK_ADD_ERROR")

    @command(
        name="stock.update",
        description="Updates variant quantity for the current tenant.",
        params_model={"code": "string", "quantity": "int", "reason": "string"},
    )
    def update_stock(
        self,
        session: Session,
        context: TenantContext,
        code: str,
        quantity: int,
        reason: str = "MANUAL",
    ) -> ServiceResponse:
        try:
            # Get current quantity with lock
            result = (
                session.execute(
                    text(
                        "SELECT quantity FROM products WHERE code = :code AND tenant_id = :tid FOR UPDATE"
                    ),
                    {"code": code, "tid": context.tenant_id},
                )
                .mappings()
                .first()
            )

            if not result:
                return ServiceResponse.error_res(f"Product {code} not found", "PRODUCT_NOT_FOUND")

            new_qty = result["quantity"] + quantity
            if new_qty < 0:
                return ServiceResponse.error_res("Insufficient stock", "STOCK_INSUFFICIENT")

            # Update quantity
            session.execute(
                text("UPDATE products SET quantity = :qty WHERE code = :code AND tenant_id = :tid"),
                {"qty": new_qty, "code": code, "tid": context.tenant_id},
            )

            # Record movement
            session.execute(
                text(
                    "INSERT INTO stock_movements (product_code, quantity, reason, user_id, tenant_id) VALUES (:code, :qty, :reason, :uid, :tid)"
                ),
                {
                    "code": code,
                    "qty": quantity,
                    "reason": reason,
                    "uid": context.user_id,
                    "tid": context.tenant_id,
                },
            )

            session.commit()
            return ServiceResponse.success_res(
                data={"new_quantity": new_qty},
                message=f"Stock updated. New total: {new_qty}.",
            )
        except Exception as e:
            session.rollback()
            return ServiceResponse.error_res(
                f"Error updating stock: {str(e)}", "STOCK_UPDATE_ERROR"
            )

    @command(
        name="stock.get",
        description="Retrieves product data for the current tenant.",
        params_model={"code": "string"},
    )
    def get_product(self, session: Session, context: TenantContext, code: str) -> ServiceResponse:
        try:
            result = (
                session.execute(
                    text("SELECT * FROM products WHERE code = :code AND tenant_id = :tid"),
                    {"code": code, "tid": context.tenant_id},
                )
                .mappings()
                .first()
            )

            if not result:
                return ServiceResponse.error_res(f"Product {code} not found", "PRODUCT_NOT_FOUND")
            return ServiceResponse.success_res(data=dict(result), message="Product retrieved.")
        except Exception as e:
            return ServiceResponse.error_res(f"Error fetching product: {str(e)}", "STOCK_GET_ERROR")


stock_commands = StockCommandHandler()
