import logging
from typing import Any, Dict, Optional
from sqlalchemy import text
from sqlalchemy.orm import Session
from core.types import ServiceResponse
from core.decorators import command
from core.context import TenantContext
import uuid

logger = logging.getLogger("OmniCore.SaaSAdmin")

class SaaSAdminCommandHandler:
    """
    Comandos de SuperAdministración para la gestión del SaaS.
    Permite controlar la oferta de módulos y las asignaciones personalizadas.
    """

    @command(
        name="saas.create_module",
        description="Registers a new module in the global catalog.",
        params_model={"module_id": "string", "name": "string", "base_plan": "string", "is_custom": "boolean"},
    )
    def create_module(
        self, 
        session: Session, 
        context: TenantContext, 
        module_id: str, 
        name: str, 
        base_plan: str = "free", 
        is_custom: bool = False
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
                {"mid": module_id, "name": name, "plan": base_plan, "custom": is_custom}
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
        self, 
        session: Session, 
        context: TenantContext, 
        tenant_id: str, 
        module_id: str
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
                {"tid": uuid.UUID(tenant_id), "mid": module_id}
            )
            session.commit()
            return ServiceResponse.success_res(message=f"Module {module_id} assigned to tenant successfully.")
        except Exception as e:
            session.rollback()
            return ServiceResponse.error_res(str(e), "MODULE_ASSIGN_ERROR")

    @command(
        name="saas.revoke_module",
        description="Revokes a specific module assignment from a tenant.",
        params_model={"tenant_id": "string", "module_id": "string"},
    )
    def revoke_module(
        self, 
        session: Session, 
        context: TenantContext, 
        tenant_id: str, 
        module_id: str
    ) -> ServiceResponse:
        try:
            session.execute(
                text(
                    "DELETE FROM tenant_modules WHERE tenant_id = :tid AND module_id = :mid"
                ),
                {"tid": uuid.UUID(tenant_id), "mid": module_id}
            )
            session.commit()
            return ServiceResponse.success_res(message=f"Module {module_id} revoked from tenant.")
        except Exception as e:
            session.rollback()
            return ServiceResponse.error_res(str(e), "MODULE_REVOKE_ERROR")

saas_admin_commands = SaaSAdminCommandHandler()
