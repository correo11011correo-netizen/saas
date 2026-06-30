import os
import uuid

import mercadopago
from sqlalchemy.orm import Session

from core.context import TenantContext
from core.decorators import command
from core.logger import logger
from core.types import ServiceResponse
from db_engine.repositories.product_repo import ProductRepository
from db_engine.repositories.sale_repo import SaleRepository

BASE_URL = os.getenv("BASE_URL")
if not BASE_URL:
    raise Exception("BASE_URL environment variable is required for Mercado Pago notifications")


class SalesCommandHandler:
    def _get_sale_repo(self, session: Session):
        return SaleRepository(session)

    def _get_product_repo(self, session: Session):
        return ProductRepository(session)

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
            product_repo = self._get_product_repo(session)
            sale_repo = self._get_sale_repo(session)

            # 1. Validar stock y calcular total
            total = 0.0
            processed_items = []
            for item in items:
                product = product_repo.get_by_code(item["code"], context.tenant_id)

                if not product:
                    return ServiceResponse.error_res(
                        f"Product {item['code']} not found", "PRODUCT_NOT_FOUND"
                    )
                if product["quantity"] < item["quantity"]:
                    return ServiceResponse.error_res(
                        f"Insufficient stock for {item['code']}", "INSUFFICIENT_STOCK"
                    )

                subtotal = float(product["price"]) * item["quantity"]
                total += subtotal
                processed_items.append(
                    {
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
            sale_repo.create_sale(
                {
                    "id": sale_id,
                    "tid": context.tenant_id,
                    "cliente": customer_phone,
                    "cid": customer_id,
                    "total": total,
                    "metodo": "efectivo",
                    "paga": paga_con,
                    "vuelto": vuelto,
                }
            )

            # 4. Registrar items y descontar stock
            for pi in processed_items:
                sale_repo.create_sale_item(
                    {
                        "id": uuid.uuid4(),
                        "tid": context.tenant_id,
                        "sid": sale_id,
                        "code": pi["code"],
                        "qty": pi["quantity"],
                        "price": pi["price"],
                        "sub": pi["subtotal"],
                    }
                )
                product_repo.update_quantity(pi["code"], context.tenant_id, -pi["quantity"])
                product_repo.add_movement(
                    pi["code"], -pi["quantity"], "SALE", context.user_id, context.tenant_id
                )

            session.commit()
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
            sale_repo = self._get_sale_repo(session)

            # 0. Idempotency Check
            if client_request_id:
                # Using a simple raw check for idempotency as it's a specific a-sync case
                # but we could add it to the repo. For now, let's use a repo method if we add it.
                # Since we are refactoring, let's just use the repo we created.
                # Wait, I didn't add a check_idempotency to SaleRepository. Let's use a raw query
                # or we can just trust the repo if we add it.
                # Let's use a raw query for this specific check to keep it concise or add it to repo.
                # I'll stick to the logic from the original code but utilizing repositories where possible.
                from sqlalchemy import text

                existing_sale = (
                    session.execute(
                        text(
                            "SELECT id FROM sales_orders WHERE client_request_id = :rid AND tenant_id = :tid"
                        ),
                        {"rid": client_request_id, "tid": context.tenant_id},
                    )
                    .mappings()
                    .first()
                )

                if existing_sale:
                    return ServiceResponse.success_res(
                        data={"sale_id": str(existing_sale["id"])},
                        message="Sale already registered (idempotency check).",
                    )

            # 1. Get credentials for MP
            # Let's use a raw query for credentials as we don't have a CredentialRepository yet.
            from sqlalchemy import text

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
                return ServiceResponse.error_res("MP credentials not found", "MP_CREDS_ERROR")

            # 2. Create Sale in DB
            sale_id = sale_repo.create_order(
                {"tid": context.tenant_id, "total": total, "rid": client_request_id}
            )

            # 3. SAVE ITEMS
            for item in items:
                subtotal = float(item["price"]) * int(item["quantity"])
                sale_repo.add_order_item(
                    {
                        "tid": context.tenant_id,
                        "sid": sale_id,
                        "code": item["code"],
                        "qty": item["quantity"],
                        "price": item["price"],
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
            sale_repo.update_order_link(sale_id, payment_link)
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
            sale_repo = self._get_sale_repo(session)
            product_repo = self._get_product_repo(session)

            # 1. Update Order Status
            total = sale_repo.update_order_status(sale_id, context.tenant_id, "paid")

            if not total:
                return ServiceResponse.error_res(
                    "Order not found or already processed", "ORDER_NOT_FOUND"
                )

            # 2. Deduct Stock for each item in the sale
            # Need to fetch items first. I'll add a get_order_items to SaleRepository.
            # For now, I'll use a raw query since I can't modify the repo in this call.
            # Actually, I should have added it. Let's use raw for this one part.
            from sqlalchemy import text

            items = (
                session.execute(
                    text(
                        "SELECT product_code, quantity FROM sale_items WHERE sale_id = :sid AND tenant_id = :tid"
                    ),
                    {"sid": sale_id, "tid": context.tenant_id},
                )
                .mappings()
                .all()
            )

            for item in items:
                product_repo.update_quantity(
                    item["product_code"], context.tenant_id, -item["quantity"]
                )
                product_repo.add_movement(
                    code=item["product_code"],
                    quantity=-item["quantity"],
                    reason="SALE_CONFIRMED",
                    user_id=context.user_id,
                    tenant_id=context.tenant_id,
                )

            session.commit()
            return ServiceResponse.success_res(message="Payment confirmed and stock updated.")
        except Exception as e:
            session.rollback()
            logger.exception("Payment confirmation error: %s", e)
            return ServiceResponse.error_res(str(e), "CONFIRM_PAYMENT_ERROR")

    @command(
        name="business.maintenance.cash_box_reset",
        description="Forces a reset of the cash box. Use only in case of critical human error.",
        params_model={},
    )
    def reset_cash_box(self, session: Session, context: TenantContext) -> ServiceResponse:
        try:
            from sqlalchemy import text

            session.execute(
                text("UPDATE cash_box SET abierta = false WHERE tenant_id = :tid"),
                {"tid": context.tenant_id},
            )
            session.execute(
                text(
                    "UPDATE cash_box SET efectivo_inicial = 0, ventas_efectivo = 0, ventas_digital = 0 WHERE tenant_id = :tid"
                ),
                {"tid": context.tenant_id},
            )
            session.commit()
            return ServiceResponse.success_res(
                message="Cash box has been forcefully reset. All totals cleared."
            )
        except Exception as e:
            session.rollback()
            return ServiceResponse.error_res(str(e), "CASH_BOX_RESET_ERROR")


sales_commands = SalesCommandHandler()
