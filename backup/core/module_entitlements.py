import logging

from sqlalchemy import text
from sqlalchemy.orm import Session

from core.context import TenantContext

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

        plan_modules = (
            session.execute(
                text("""
                SELECT module_id FROM available_modules
                WHERE (
                    CASE
                        WHEN base_plan = 'free' THEN 0
                        WHEN base_plan = 'pro' THEN 1
                        WHEN base_plan = 'enterprise' THEN 2
                        ELSE 0
                    END
                ) <= :plan_level
            """),
                {"plan_level": user_plan_level},
            )
            .mappings()
            .all()
        )

        active_modules = {row["module_id"] for row in plan_modules}

        # 2. Módulos asignados explícitamente al Tenant (Overrides/Customs)
        manual_modules = (
            session.execute(
                text("SELECT module_id FROM tenant_modules WHERE tenant_id = :tid"),
                {"tid": context.tenant_id},
            )
            .mappings()
            .all()
        )

        active_modules.update({row["module_id"] for row in manual_modules})

        return active_modules


module_entitlement_service = ModuleEntitlementService()
