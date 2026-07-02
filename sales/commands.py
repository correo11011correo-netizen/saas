import os
import uuid

import mercadopago
from sqlalchemy.orm import Session

from core.context import TenantContext
from core.decorators import command
from core.types import ServiceResponse
from core.data_commands import data_commands

BASE_URL = os.getenv("BASE_URL")
if not BASE_URL:
    raise Exception("BASE_URL environment variable is required for Mercado Pago notifications")


class SalesCommandHandler:
    @command(
        name="sales.cobrar",
        description="Processes a sale, updates stock and registers the payment.",
        params_model={
            "customer_phone": "string",
            "items": "list",
            "paga_con": "decimal",
        },
    )
    def cobrar(
        self,
        session: Session,
        context: TenantContext,
        customer_phone: str,
        items: list[dict],
        paga_con: float,
    ) -> ServiceResponse:
        try:
            # 1. Validar stock y calcular total
            total = 0.0
            processed_items = []
            for item in items:
                # Usar motor para buscar el producto
                res = data_commands.query_data(
                    session, context, entity="products", filters={"code": item["code"]}
                )
                if not res.success or not res.data:
                    return ServiceResponse.error_res(
                        f"Product {item['code']} not found", "PRODUCT_NOT_FOUND"
                    )
                
                product = res.data[0]
                if product["quantity"] < item["quantity"]:
                    return ServiceResponse.error_res(
                        f"Insufficient stock for {item['code']}", "INSUFFICIENT_STOCK"
                    )

                subtotal = float(product["price"]) * item["quantity"]
                total += subtotal
                processed_items.append(
                    {
                        "id": product["id"],
                        "code": item["code"],
                        "quantity": item["quantity"],
                        "price": product["price"],
                        "subtotal": subtotal,
                    }
                )

            # 2. INTEGRACIÓN CRM: Obtener o crear el cliente
            from core.crm_commands import crm_commands

            customer_res = crm_commands.create_or_update_customer(
                session, context, phone_number=customer_phone
            )
            if not customer_res.success:
                return ServiceResponse.error_res(f"CRM Error: {customer_res.error}", "CRM_ERROR")
            customer_id = customer_res.data["customer_id"]

            # 3. Registrar la venta
            vuelto = paga_con - total
            if vuelto < 0:
                return ServiceResponse.error_res(
                    f"Payment insufficient. Total: {total}, Paid: {paga_con}",
                    "INSUFFICIENT_PAYMENT",
                )

            sale_id = uuid.uuid4()
            sale_res = data_commands.insert_data(
                session, 
                context, 
                entity="sales", 
                data={
                    "id": sale_id, 
                    "cliente": customer_phone, 
                    "customer_id": customer_id, 
                    "total": total, 
                    "metodo_pago": "efectivo", 
                    "paga_con": paga_con, 
                    "vuelto": vuelto
                }
            )
            if not sale_res.success:
                return sale_res

            # 4. Registrar items y descontar stock
            for pi in processed_items:
                # Registrar item de venta
                data_commands.insert_data(
                    session, 
                    context, 
                    entity="sale_items", 
                    data={
                        "id": uuid.uuid4(), 
                        "sale_id": sale_id, 
                        "product_code": pi["code"], 
                        "quantity": pi["quantity"], 
                        "price": pi["price"], 
                        "subtotal": pi["subtotal"]
                    }
                )
                # Descontar stock atómicamente
                data_commands.increment_data(
                    session, 
                    context, 
                    entity="products", 
                    record_id=pi["id"], 
                    field="quantity", 
                    value=-pi["quantity"]
                )

            return ServiceResponse.success_res(
                data={"sale_id": str(sale_id), "total": total, "vuelto": vuelto},
                message="Sale processed successfully.",
            )
        except Exception as e:
            session.rollback()
            return ServiceResponse.error_res(str(e), "SALES_COBRAR_ERROR")

    @command(
        name="sales.create",
        description="Creates a sales order and generates a Mercado Pago payment link.",
        params_model={
            "items": "list",
            "total": "float",
            "account_alias": "string",
            "client_request_id": "string",
        },
    )
    def create_sale(
        self,
        session: Session,
        context: TenantContext,
        items: list,
        total: float,
        account_alias: str,
        client_request_id: str = None,
    ) -> ServiceResponse:
        try:
            # 0. Idempotency Check
            if client_request_id:
                res = data_commands.query_data(
                    session, context, entity="sales_orders", filters={"client_request_id": client_request_id}
                )
                if res.success and res.data:
                    return ServiceResponse.success_res(
                        data={"sale_id": str(res.data[0]["id"])},
                        message="Sale already registered (idempotency check).",
                    )

            # 1. Get credentials for MP
            res_cred = data_commands.query_data(
                session, 
                context, 
                entity="credentials", 
                filters={"service_name": "mercadopago", "account_alias": account_alias}
            )
            if not res_cred.success or not res_cred.data:
                return ServiceResponse.error_res("MP credentials not found", "MP_CREDS_ERROR")
            
            cred = res_cred.data[0]

            # 2. Create Sale in DB
            sale_res = data_commands.insert_data(
                session, 
                context, 
                entity="sales_orders", 
                data={
                    "total": total, 
                    "payment_status": "pending", 
                    "client_request_id": client_request_id
                }
            )
            if not sale_res.success:
                return sale_res
            sale_id = sale_res.data["id"]

            # 3. SAVE ITEMS
            for item in items:
                subtotal = float(item["price"]) * int(item["quantity"])
                data_commands.insert_data(
                    session, 
                    context, 
                    entity="sale_items", 
                    data={
                        "sale_id": sale_id, 
                        "product_code": item["code"], 
                        "quantity": item["quantity"], 
                        "price": item["price"], 
                        "subtotal": subtotal
                    }
                )

            # 4. Create MP Preference
            sdk = mercadopago.SDK(cred["api_key"])
            preference_data = {
                "items": [
                    {"title": "Venta OmniCore", "quantity": 1, "unit_price": total},
                ],
                "external_reference": str(sale_id),
                "notification_url": f"{BASE_URL}/hooks/mp/ipn",
            }
            preference_response = sdk.preference().create(preference_data)
            payment_link = preference_response["response"]["init_point"]

            # 5. Update order with payment link
            data_commands.patch_data(
                session, 
                context, 
                entity="sales_orders", 
                record_id=sale_id, 
                updates={"payment_link": payment_link}
            )

            return ServiceResponse.success_res(
                data={"payment_link": payment_link, "sale_id": str(sale_id)},
                message="Sale created.",
            )
        except Exception as e:
            session.rollback()
            return ServiceResponse.error_res(str(e), "SALE_CREATE_ERROR")

    @command(
        name="sales.confirm_payment",
        description="Confirms a payment, updates order status, and deducts products from stock.",
        params_model={"sale_id": "string"},
    )
    def confirm_payment(
        self,
        session: Session,
        context: TenantContext,
        sale_id: str,
    ) -> ServiceResponse:
        try:
            # 1. Update Order Status
            patch_res = data_commands.patch_data(
                session, 
                context, 
                entity="sales_orders", 
                record_id=sale_id, 
                updates={"payment_status": "paid"}
            )
            if not patch_res.success:
                return patch_res

            # Obtener total para validar (opcional, pero el código original lo hacía)
            order_res = data_commands.query_data(
                session, context, entity="sales_orders", filters={"id": sale_id}
            )
            if not order_res.success or not order_res.data:
                return ServiceResponse.error_res("Order not found", "ORDER_NOT_FOUND")

            # 2. Deduct Stock for each item in the sale
            items_res = data_commands.query_data(
                session, 
                context, 
                entity="sale_items", 
                filters={"sale_id": sale_id}
            )
            if not items_res.success:
                return items_res

            for item in items_res.data:
                # Buscar el ID del producto para poder usar increment_data
                prod_res = data_commands.query_data(
                    session, 
                    context, 
                    entity="products", 
                    filters={"code": item["product_code"]}
                )
                if prod_res.success and prod_res.data:
                    prod_id = prod_res.data[0]["id"]
                    # Restar cantidad
                    data_commands.increment_data(
                        session, 
                        context, 
                        entity="products", 
                        record_id=prod_id, 
                        field="quantity", 
                        value=-item["quantity"]
                    )

                # Registrar movimiento de stock
                data_commands.insert_data(
                    session, 
                    context, 
                    entity="stock_movements", 
                    data={
                        "product_code": item["product_code"], 
                        "quantity": -item["quantity"], 
                        "reason": "SALE_CONFIRMED", 
                        "user_id": context.user_id
                    }
                )

            return ServiceResponse.success_res(message="Payment confirmed and stock updated.")
        except Exception as e:
            session.rollback()
            return ServiceResponse.error_res(str(e), "CONFIRM_PAYMENT_ERROR")


sales_commands = SalesCommandHandler()
