import logging

from sqlalchemy.orm import Session

from core.context import TenantContext
from core.data_commands import data_commands

logger = logging.getLogger("OmniCore.ModuleEntitlements")


class ModuleEntitlementService:
    """
    Servicio de Gestión de Derechos de Acceso a Módulos.
    Determina qué paneles debe cargar la APK basándose en el plan y asignaciones manuales.
    """

    PLAN_HIERARCHY = {"free": 0, "pro": 1, "enterprise": 2}

    def get_active_modules(self, session: Session, context: TenantContext) -> set[str]:
        """
        Calcula la unión de módulos permitidos por plan y módulos asignados individualmente.
        """
        # 1. Módulos otorgados por el plan actual del usuario
        user_plan_level = self.PLAN_HIERARCHY.get(context.plan.lower(), 0)

        # Fetch all available modules and filter by plan level in Python
        res_modules = data_commands.query_data(
            session, TenantContext(tenant_id=None), entity="available_modules"
        )
        
        active_modules = set()
        if res_modules.success:
            for mod in res_modules.data:
                base_plan = mod.get("base_plan", "free").lower()
                plan_level = self.PLAN_HIERARCHY.get(base_plan, 0)
                if plan_level <= user_plan_level:
                    active_modules.add(mod["module_id"])

        # 2. Módulos asignados explícitamente al Tenant (Overrides/Customs)
        res_manual = data_commands.query_data(
            session, context, entity="tenant_modules"
        )
        
        if res_manual.success:
            for row in res_manual.data:
                active_modules.add(row["module_id"])

        return active_modules


module_entitlement_service = ModuleEntitlementService()
