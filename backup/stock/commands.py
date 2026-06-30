import logging

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.context import TenantContext
from core.decorators import command
from core.types import ServiceResponse
from db_engine.repositories.product_repo import ProductRepository

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
    Utiliza ProductRepository para la persistencia de datos.
    """

    def _get_repo(self, session: Session) -> ProductRepository:
        return ProductRepository(session)

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
            repo = self._get_repo(session)
            result = repo.list_all(context.tenant_id)
            return ServiceResponse.success_res(
                data=result,
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
            repo = self._get_repo(session)
            repo.upsert(
                {
                    "code": code,
                    "name": name,
                    "price": price,
                    "quantity": quantity,
                    "category": category,
                    "is_weight": is_weight,
                    "tid": context.tenant_id,
                }
            )

            repo.add_movement(
                code=code,
                quantity=quantity,
                reason="INITIAL_LOAD" if quantity > 0 else "UPDATE",
                user_id=context.user_id,
                tenant_id=context.tenant_id,
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
            repo = self._get_repo(session)
            new_qty = repo.update_quantity(code, context.tenant_id, quantity)

            if new_qty is None:
                return ServiceResponse.error_res(f"Product {code} not found", "PRODUCT_NOT_FOUND")
            if new_qty < 0:
                return ServiceResponse.error_res("Insufficient stock", "STOCK_INSUFFICIENT")

            repo.add_movement(
                code=code,
                quantity=quantity,
                reason=reason,
                user_id=context.user_id,
                tenant_id=context.tenant_id,
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
            repo = self._get_repo(session)
            product = repo.get_by_code(code, context.tenant_id)

            if not product:
                return ServiceResponse.error_res(f"Product {code} not found", "PRODUCT_NOT_FOUND")
            return ServiceResponse.success_res(data=product, message="Product retrieved.")
        except Exception as e:
            return ServiceResponse.error_res(f"Error fetching product: {str(e)}", "STOCK_GET_ERROR")

    @command(
        name="business.monitor.critical_stock",
        description="Retrieves products with quantity below a critical threshold (default 5).",
        params_model={"threshold": "int"},
    )
    def get_critical_stock(
        self,
        session: Session,
        context: TenantContext,
        threshold: int = 5,
    ) -> ServiceResponse:
        try:
            repo = self._get_repo(session)
            result = repo.get_critical_stock(context.tenant_id, threshold)
            return ServiceResponse.success_res(
                data=result,
                message=f"Found {len(result)} products below threshold {threshold}.",
            )
        except Exception as e:
            return ServiceResponse.error_res(
                f"Error checking critical stock: {str(e)}", "STOCK_CRITICAL_ERROR"
            )


stock_commands = StockCommandHandler()
