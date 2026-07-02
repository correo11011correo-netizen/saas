import datetime
import logging
import uuid

from sqlalchemy.orm import Session

from core.context import TenantContext
from core.decorators import command
from core.types import ServiceResponse
from core.data_commands import data_commands

logger = logging.getLogger("OmniCore.Billing")


class BillingCommandHandler:
    """
    Gestión Comercial del SaaS.
    Maneja los planes, suscripciones y el estado de pago de los Tenants.
    """

    @command(
        name="billing.set_plan",
        description="Updates the subscription plan for a tenant.",
        params_model={"tenant_id": "string", "plan_id": "string"},
    )
    def set_plan(
        self, session: Session, context: TenantContext, tenant_id: str, plan_id: str
    ) -> ServiceResponse:
        try:
            tid = uuid.UUID(tenant_id)
            # 1. Update the tenant table for quick access
            patch_res = data_commands.patch_data(
                session, context, entity="tenants", record_id=tid, updates={"plan": plan_id}
            )
            if not patch_res.success:
                return patch_res

            # 2. Update or create the subscription record
            # Check if subscription exists
            sub_res = data_commands.query_data(
                session, context, entity="tenant_subscriptions", filters={"tenant_id": tid}
            )
            
            end_date = datetime.datetime.now() + datetime.timedelta(days=30)
            sub_data = {
                "tenant_id": tid,
                "plan_id": plan_id,
                "subscription_status": "active",
                "end_date": end_date,
            }

            if sub_res.success and sub_res.data:
                # Update existing
                sub_id = sub_res.data[0]["id"]
                data_commands.patch_data(
                    session, context, entity="tenant_subscriptions", record_id=sub_id, updates=sub_data
                )
            else:
                # Insert new
                data_commands.insert_data(
                    session, context, entity="tenant_subscriptions", data=sub_data
                )

            session.commit()
            return ServiceResponse.success_res(
                message=f"Tenant upgraded to {plan_id} plan successfully."
            )
        except Exception as e:
            session.rollback()
            return ServiceResponse.error_res(str(e), "BILLING_PLAN_ERROR")

    @command(
        name="billing.update_status",
        description="Updates the payment status of a subscription.",
        params_model={"tenant_id": "string", "status": "string"},
    )
    def update_status(
        self, session: Session, context: TenantContext, tenant_id: str, status: str
    ) -> ServiceResponse:
        try:
            tid = uuid.UUID(tenant_id)
            # Buscar la suscripción primero
            sub_res = data_commands.query_data(
                session, context, entity="tenant_subscriptions", filters={"tenant_id": tid}
            )
            if not sub_res.success or not sub_res.data:
                return ServiceResponse.error_res("Subscription not found", "SUB_NOT_FOUND")
            
            sub_id = sub_res.data[0]["id"]
            patch_res = data_commands.patch_data(
                session, context, entity="tenant_subscriptions", record_id=sub_id, updates={"subscription_status": status}
            )
            if not patch_res.success:
                return patch_res

            session.commit()
            return ServiceResponse.success_res(message=f"Subscription status updated to {status}.")
        except Exception as e:
            session.rollback()
            return ServiceResponse.error_res(str(e), "BILLING_STATUS_ERROR")

    @command(
        name="billing.extend_subscription",
        description="Extends the expiration date of a tenant's subscription.",
        params_model={"tenant_id": "string", "days": "int"},
    )
    def extend_subscription(
        self, session: Session, context: TenantContext, tenant_id: str, days: int
    ) -> ServiceResponse:
        try:
            tid = uuid.UUID(tenant_id)
            # Buscar suscripción actual
            sub_res = data_commands.query_data(
                session, context, entity="tenant_subscriptions", filters={"tenant_id": tid}
            )
            if not sub_res.success or not sub_res.data:
                return ServiceResponse.error_res("Subscription not found", "SUB_NOT_FOUND")
            
            sub = sub_res.data[0]
            # Calcular nueva fecha en Python (ya que el motor no soporta INTERVAL de SQL)
            current_end_date = sub["end_date"]
            # Si es string, convertir a datetime
            if isinstance(current_end_date, str):
                from dateutil import parser
                current_end_date = parser.parse(current_end_date)
            
            new_end_date = current_end_date + datetime.timedelta(days=days)
            
            patch_res = data_commands.patch_data(
                session, context, entity="tenant_subscriptions", record_id=sub["id"], updates={"end_date": new_end_date}
            )
            if not patch_res.success:
                return patch_res

            session.commit()
            return ServiceResponse.success_res(message=f"Subscription extended by {days} days.")
        except Exception as e:
            session.rollback()
            return ServiceResponse.error_res(str(e), "BILLING_EXTEND_ERROR")


billing_commands = BillingCommandHandler()
