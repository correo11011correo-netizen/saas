import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from core.context import TenantContext

logger = logging.getLogger("OmniCore.SDUI")


class SDUIEngine:
    """
    Motor de Interfaz Dirigida por Servidor (Server-Driven UI).
    Orquestador que define qué componentes nativos debe renderizar la APK.
    """

    def get_boot_manifest(self, session: Session, context: TenantContext) -> dict[str, Any]:
        """
        Genera el contrato de arranque, delegando según el rol.
        """
        if context.role == "superadmin":
            return self.get_superadmin_manifest(session, context)
        elif context.role == "admin":
            return self.get_business_admin_manifest(session, context)
        else:
            return self.get_employee_manifest(session, context)

    def get_superadmin_manifest(self, session: Session, context: TenantContext) -> dict[str, Any]:
        return {
            "user": {"role": "superadmin", "plan": "enterprise"},
            "theme": {"primary_color": "#2C3E50", "secondary_color": "#ECF0F1", "dark_mode": True},
            "dock": [
                {"id": "tenants", "label": "Negocios", "icon": "building"},
                {"id": "billing", "label": "Pagos Globales", "icon": "credit_card"},
                {"id": "analytics", "label": "Métricas SaaS", "icon": "chart"},
            ],
            "layout": {"home": [{"component": "AdminTenantTable", "props": {}}]},
        }

    def get_business_admin_manifest(
        self, session: Session, context: TenantContext
    ) -> dict[str, Any]:
        # Aquí se mantiene la lógica original de layouts dinámicos por tenant
        return self._get_tenant_manifest(session, context)

    def get_employee_manifest(self, session: Session, context: TenantContext) -> dict[str, Any]:
        # Similar a admin pero con filtrado estricto de componentes
        manifest = self._get_tenant_manifest(session, context)
        # TODO: Implementar lógica de filtrado de componentes por permisos
        return manifest

    def _get_tenant_manifest(self, session: Session, context: TenantContext) -> dict[str, Any]:
        # 1. Tema Visual
        theme = (
            session.execute(
                text("SELECT * FROM ui_themes WHERE tenant_id = :tid"), {"tid": context.tenant_id}
            )
            .mappings()
            .first()
        )

        # 2. Layout
        home_layout = (
            session.execute(
                text(
                    "SELECT layout_json FROM ui_layouts WHERE tenant_id = :tid AND screen_id = 'home'"
                ),
                {"tid": context.tenant_id},
            )
            .mappings()
            .first()
        )

        return {
            "user": {"role": context.role, "plan": context.plan},
            "theme": dict(theme)
            if theme
            else {"primary_color": "#000000", "secondary_color": "#FFFFFF", "dark_mode": False},
            "layout": {
                "home": home_layout["layout_json"] if home_layout else [],
                "dock": [{"id": "sales", "label": "Ventas", "icon": "cart"}],  # Placeholder
            },
        }


sdui_engine = SDUIEngine()
