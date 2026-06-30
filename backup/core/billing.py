import datetime
import logging
import uuid

from sqlalchemy import text
from sqlalchemy.orm import Session

from core.context import TenantContext
from core.decorators import command
from core.types import ServiceResponse

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
            # 1. Update the tenant table for quick access
            session.execute(
                text("UPDATE tenants SET plan = :plan WHERE id = :tid"),
                {"plan": plan_id, "tid": uuid.UUID(tenant_id)},
            )

            # 2. Update or create the subscription record
            session.execute(
                text(
                    """
                    INSERT INTO tenant_subscriptions (tenant_id, plan_id, subscription_status, end_date)
                    VALUES (:tid, :plan, 'active', :end_date)
                    ON CONFLICT (tenant_id) DO UPDATE SET
                        plan_id = EXCLUDED.plan_id,
                        subscription_status = 'active',
                        end_date = EXCLUDED.end_date
                    """
                ),
                {
                    "tid": uuid.UUID(tenant_id),
                    "plan": plan_id,
                    "end_date": datetime.datetime.now() + datetime.timedelta(days=30),
                },
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
            session.execute(
                text(
                    "UPDATE tenant_subscriptions SET subscription_status = :status WHERE tenant_id = :tid"
                ),
                {"status": status, "tid": uuid.UUID(tenant_id)},
            )
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
            session.execute(
                text(
                    "UPDATE tenant_subscriptions SET end_date = end_date + INTERVAL ':days days' WHERE tenant_id = :tid"
                ),
                {"days": days, "tid": uuid.UUID(tenant_id)},
            )
            session.commit()
            return ServiceResponse.success_res(message=f"Subscription extended by {days} days.")
        except Exception as e:
            session.rollback()
            return ServiceResponse.error_res(str(e), "BILLING_EXTEND_ERROR")


billing_commands = BillingCommandHandler()
