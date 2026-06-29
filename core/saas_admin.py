import logging
import uuid

from sqlalchemy import text
from sqlalchemy.orm import Session

from core.context import TenantContext
from core.decorators import command
from core.types import ServiceResponse

logger = logging.getLogger("OmniCore.SaaSAdmin")


class SaaSAdminCommandHandler:
    """
    Comandos de SuperAdministración para la gestión del SaaS.
    Permite controlar la oferta de módulos, la gestión de clientes y la salud del sistema.
    """

    @command(
        name="saas.tenants.list",
        description="Lists all registered tenants in the system with their current plan.",
        params_model={},
    )
    def list_tenants(self, session: Session, context: TenantContext) -> ServiceResponse:
        try:
            tenants = (
                session.execute(
                    text(
                        "SELECT id, name, plan, status, created_at FROM tenants ORDER BY created_at DESC"
                    )
                )
                .mappings()
                .all()
            )

            return ServiceResponse.success_res(
                data=[dict(t) for t in tenants], message=f"Found {len(tenants)} tenants."
            )
        except Exception as e:
            return ServiceResponse.error_res(str(e), "SAAS_TENANTS_LIST_ERROR")

    @command(
        name="saas.tenants.get",
        description="Gets detailed information about a specific tenant, including its users and active modules.",
        params_model={"tenant_id": "string"},
    )
    def get_tenant_details(
        self, session: Session, context: TenantContext, tenant_id: str
    ) -> ServiceResponse:
        try:
            tenant = (
                session.execute(
                    text("SELECT * FROM tenants WHERE id = :tid"),
                    {"tid": uuid.UUID(tenant_id)},
                )
                .mappings()
                .first()
            )

            if not tenant:
                return ServiceResponse.error_res("Tenant not found", "TENANT_NOT_FOUND")

            users = (
                session.execute(
                    text("SELECT id, email, role FROM users WHERE tenant_id = :tid"),
                    {"tid": uuid.UUID(tenant_id)},
                )
                .mappings()
                .all()
            )

            modules = (
                session.execute(
                    text("SELECT module_id FROM tenant_modules WHERE tenant_id = :tid"),
                    {"tid": uuid.UUID(tenant_id)},
                )
                .mappings()
                .all()
            )

            return ServiceResponse.success_res(
                data={
                    "tenant": dict(tenant),
                    "users": [dict(u) for u in users],
                    "active_modules": [m["module_id"] for m in modules],
                },
                message="Tenant details retrieved.",
            )
        except Exception as e:
            return ServiceResponse.error_res(str(e), "SAAS_TENANT_GET_ERROR")

    @command(
        name="saas.tenants.update_plan",
        description="Manually updates the subscription plan for a tenant.",
        params_model={"tenant_id": "string", "plan": "string"},
    )
    def update_tenant_plan(
        self, session: Session, context: TenantContext, tenant_id: str, plan: str
    ) -> ServiceResponse:
        try:
            session.execute(
                text("UPDATE tenants SET plan = :plan WHERE id = :tid"),
                {"plan": plan, "tid": uuid.UUID(tenant_id)},
            )
            session.commit()
            return ServiceResponse.success_res(
                message=f"Tenant plan updated to {plan} successfully."
            )
        except Exception as e:
            session.rollback()
            return ServiceResponse.error_res(str(e), "SAAS_TENANT_PLAN_ERROR")

    @command(
        name="saas.tenants.suspend",
        description="Suspends a tenant account, blocking all access.",
        params_model={"tenant_id": "string", "status": "string"},
    )
    def suspend_tenant(
        self,
        session: Session,
        context: TenantContext,
        tenant_id: str,
        status: str = "suspended",
    ) -> ServiceResponse:
        try:
            session.execute(
                text("UPDATE tenants SET status = :status WHERE id = :tid"),
                {"status": status, "tid": uuid.UUID(tenant_id)},
            )
            session.commit()
            return ServiceResponse.success_res(message=f"Tenant status updated to {status}.")
        except Exception as e:
            session.rollback()
            return ServiceResponse.error_res(str(e), "SAAS_TENANT_SUSPEND_ERROR")

    @command(
        name="saas.create_module",
        description="Registers a new module in the global catalog.",
        params_model={
            "module_id": "string",
            "name": "string",
            "base_plan": "string",
            "is_custom": "boolean",
        },
    )
    def create_module(
        self,
        session: Session,
        context: TenantContext,
        module_id: str,
        name: str,
        base_plan: str = "free",
        is_custom: bool = False,
    ) -> ServiceResponse:
        try:
            session.execute(
                text(
                    """
                    INSERT INTO available_modules (module_id, name, base_plan, is_custom)
                    VALUES (:mid, :name, :plan, :custom)
                    ON CONFLICT (module_id) DO UPDATE SET name = EXCLUDED.name, base_plan = EXCLUDED.base_plan
                    """
                ),
                {"mid": module_id, "name": name, "plan": base_plan, "custom": is_custom},
            )
            session.commit()
            return ServiceResponse.success_res(message=f"Module {name} registered successfully.")
        except Exception as e:
            session.rollback()
            return ServiceResponse.error_res(str(e), "MODULE_CREATE_ERROR")

    @command(
        name="saas.assign_module_to_tenant",
        description="Assigns a specific module to a tenant, bypassing their plan limits.",
        params_model={"tenant_id": "string", "module_id": "string"},
    )
    def assign_module(
        self, session: Session, context: TenantContext, tenant_id: str, module_id: str
    ) -> ServiceResponse:
        try:
            session.execute(
                text(
                    """
                    INSERT INTO tenant_modules (tenant_id, module_id)
                    VALUES (:tid, :mid)
                    ON CONFLICT (tenant_id, module_id) DO NOTHING
                    """
                ),
                {"tid": uuid.UUID(tenant_id), "mid": module_id},
            )
            session.commit()
            return ServiceResponse.success_res(
                message=f"Module {module_id} assigned to tenant successfully."
            )
        except Exception as e:
            session.rollback()
            return ServiceResponse.error_res(str(e), "MODULE_ASSIGN_ERROR")

    @command(
        name="saas.revoke_module",
        description="Revokes a specific module assignment from a tenant.",
        params_model={"tenant_id": "string", "module_id": "string"},
    )
    def revoke_module(
        self, session: Session, context: TenantContext, tenant_id: str, module_id: str
    ) -> ServiceResponse:
        try:
            session.execute(
                text("DELETE FROM tenant_modules WHERE tenant_id = :tid AND module_id = :mid"),
                {"tid": uuid.UUID(tenant_id), "mid": module_id},
            )
            session.commit()
            return ServiceResponse.success_res(message=f"Module {module_id} revoked from tenant.")
        except Exception as e:
            session.rollback()
            return ServiceResponse.error_res(str(e), "MODULE_REVOKE_ERROR")


saas_admin_commands = SaaSAdminCommandHandler()
