import logging

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.context import TenantContext
from core.decorators import command
from core.types import ServiceResponse
from core.data_commands import data_commands

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
    Utiliza el Motor de Datos para abstraer la persistencia.
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
            res = data_commands.query_data(
                session, context, entity="products", sort_by="name", sort_order="ASC"
            )
            if not res.success:
                return res
            
            return ServiceResponse.success_res(
                data=res.data,
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
            # Verificar si el producto ya existe para decidir entre insert o patch
            res_exists = data_commands.query_data(
                session, context, entity="products", filters={"code": code}
            )
            
            product_data = {
                "code": code,
                "name": name,
                "price": price,
                "quantity": quantity,
                "category": category,
                "is_weight": is_weight,
            }

            if res_exists.success and res_exists.data:
                # Actualizar existente
                prod_id = res_exists.data[0]["id"]
                patch_res = data_commands.patch_data(
                    session, context, entity="products", record_id=prod_id, updates=product_data
                )
                if not patch_res.success:
                    return patch_res
            else:
                # Insertar nuevo
                insert_res = data_commands.insert_data(
                    session, context, entity="products", data=product_data
                )
                if not insert_res.success:
                    return insert_res

            # Record movement
            data_commands.insert_data(
                session, 
                context, 
                entity="stock_movements", 
                data={
                    "product_code": code,
                    "quantity": quantity,
                    "reason": "INITIAL_LOAD" if quantity > 0 else "UPDATE",
                    "user_id": context.user_id,
                }
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
            # Buscar el producto para validar existencia y cantidad actual
            res_prod = data_commands.query_data(
                session, context, entity="products", filters={"code": code}
            )

            if not res_prod.success or not res_prod.data:
                return ServiceResponse.error_res(f"Product {code} not found", "PRODUCT_NOT_FOUND")

            product = res_prod.data[0]
            new_qty = product["quantity"] + quantity
            if new_qty < 0:
                return ServiceResponse.error_res("Insufficient stock", "STOCK_INSUFFICIENT")

            # Update quantity atómicamente
            inc_res = data_commands.increment_data(
                session, 
                context, 
                entity="products", 
                record_id=product["id"], 
                field="quantity", 
                value=quantity
            )
            if not inc_res.success:
                return inc_res

            # Record movement
            data_commands.insert_data(
                session, 
                context, 
                entity="stock_movements", 
                data={
                    "product_code": code,
                    "quantity": quantity,
                    "reason": reason,
                    "user_id": context.user_id,
                }
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
            res = data_commands.query_data(
                session, context, entity="products", filters={"code": code}
            )

            if not res.success or not res.data:
                return ServiceResponse.error_res(f"Product {code} not found", "PRODUCT_NOT_FOUND")
            
            return ServiceResponse.success_res(data=res.data[0], message="Product retrieved.")
        except Exception as e:
            return ServiceResponse.error_res(f"Error fetching product: {str(e)}", "STOCK_GET_ERROR")


stock_commands = StockCommandHandler()
