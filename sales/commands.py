import mercadopago
from sqlalchemy import text
from core.types import ServiceResponse
from core.decorators import command
from core.context import TenantContext
from sqlalchemy.orm import Session
import json
import os

BASE_URL = os.getenv("BASE_URL")
if not BASE_URL:
    raise Exception("BASE_URL environment variable is required for Mercado Pago notifications")

class SalesCommandHandler:
    @command(
        name="sales.create",
        description="Creates a sales order and generates a Mercado Pago payment link.",
        params_model={"items": "list", "total": "float", "account_alias": "string", "client_request_id": "string"},
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
            # 0. Idempotency Check: If a request ID is provided, check if sale already exists
            if client_request_id:
                existing_sale = session.execute(
                    text("SELECT id FROM sales_orders WHERE client_request_id = :rid AND tenant_id = :tid"),
                    {"rid": client_request_id, "tid": context.tenant_id}
                ).mappings().first()
                
                if existing_sale:
                    # Sale already exists, return its ID (Avoid duplication during offline sync)
                    return ServiceResponse.success_res(
                        data={"sale_id": str(existing_sale["id"])}, 
                        message="Sale already registered (idempotency check)."
                    )

            # 1. Get credentials for MP
            cred = (
                session.execute(
                    text(
                        "SELECT api_key FROM credentials WHERE service_name = 'mercadopago' AND account_alias = :alias AND tenant_id = :tid"
                    ),
                    {"alias": account_alias, "tid": context.tenant_id},
                )
                .mappings()
                .first()
            )

            if not cred:
                return ServiceResponse.error_res(
                    "MP credentials not found", "MP_CREDS_ERROR"
                )

            # 2. Create Sale in DB
            sale_id = session.execute(
                text(
                    "INSERT INTO sales_orders (tenant_id, total, payment_status, client_request_id) VALUES (:tid, :total, 'pending', :rid) RETURNING id"
                ),
                {"tid": context.tenant_id, "total": total, "rid": client_request_id},
            ).scalar()

            # 3. SAVE ITEMS (Cierre del ciclo de stock)

            for item in items:
                # Esperamos item con: code, quantity, price
                subtotal = float(item['price']) * int(item['quantity'])
                session.execute(
                    text(
                        "INSERT INTO sale_items (tenant_id, sale_id, product_code, quantity, price, subtotal) "
                        "VALUES (:tid, :sid, :code, :qty, :price, :sub)"
                    ),
                    {
                        "tid": context.tenant_id,
                        "sid": sale_id,
                        "code": item['code'],
                        "qty": item['quantity'],
                        "price": item['price'],
                        "sub": subtotal,
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
            session.execute(
                text("UPDATE sales_orders SET payment_link = :link WHERE id = :id"),
                {"link": payment_link, "id": sale_id},
            )
            session.commit()

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
            result = session.execute(
                text(
                    "UPDATE sales_orders SET payment_status = 'paid' WHERE id = :id AND tenant_id = :tid RETURNING total"
                ),
                {"id": sale_id, "tid": context.tenant_id},
            ).mappings().first()

            if not result:
                return ServiceResponse.error_res("Order not found or already processed", "ORDER_NOT_FOUND")

            # 2. Deduct Stock for each item in the sale
            items = session.execute(
                text("SELECT product_code, quantity FROM sale_items WHERE sale_id = :sid AND tenant_id = :tid"),
                {"sid": sale_id, "tid": context.tenant_id},
            ).mappings().all()

            for item in items:
                # Restar cantidad (quantity negativa)
                session.execute(
                    text(
                        "UPDATE products SET quantity = quantity - :qty WHERE code = :code AND tenant_id = :tid"
                    ),
                    {"qty": item['quantity'], "code": item['product_code'], "tid": context.tenant_id},
                )
                
                # Registrar movimiento de stock
                session.execute(
                    text(
                        "INSERT INTO stock_movements (product_code, quantity, reason, user_id, tenant_id) "
                        "VALUES (:code, :qty, 'SALE_CONFIRMED', :uid, :tid)"
                    ),
                    {
                        "code": item['product_code'],
                        "qty": -item['quantity'],
                        "uid": context.user_id,
                        "tid": context.tenant_id,
                    }
                )

            session.commit()
            return ServiceResponse.success_res(message="Payment confirmed and stock updated.")
        except Exception as e:
            session.rollback()
            return ServiceResponse.error_res(str(e), "CONFIRM_PAYMENT_ERROR")


sales_commands = SalesCommandHandler()
