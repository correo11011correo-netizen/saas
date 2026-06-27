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
        params_model={"items": "list", "total": "float", "account_alias": "string"},
    )
    def create_sale(
        self,
        session: Session,
        context: TenantContext,
        items: list,
        total: float,
        account_alias: str,
    ) -> ServiceResponse:
        try:
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
                    "INSERT INTO sales_orders (tenant_id, total, payment_status) VALUES (:tid, :total, 'pending') RETURNING id"
                ),
                {"tid": context.tenant_id, "total": total},
            ).scalar()

            # 3. Create MP Preference
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

            # 4. Update order with payment link
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


sales_commands = SalesCommandHandler()
