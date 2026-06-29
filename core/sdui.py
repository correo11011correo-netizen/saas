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
        elif context.role == "support":
            return self.get_support_manifest(session, context)
        elif context.role == "admin":
            return self.get_business_admin_manifest(session, context)
        else:
            return self.get_employee_manifest(session, context)

    def get_superadmin_manifest(self, session: Session, context: TenantContext) -> dict[str, Any]:
        return {
            "user": {"role": "superadmin", "plan": "enterprise"},
            "theme": {"primary_color": "#1A237E", "secondary_color": "#E8EAF6", "dark_mode": True},
            "dock": [
                {"id": "tenants", "label": "Negocios", "icon": "business"},
                {"id": "health", "label": "Salud Sistema", "icon": "monitor_heart"},
                {"id": "stats", "label": "Métricas SaaS", "icon": "analytics"},
                {"id": "billing", "label": "Facturación", "icon": "payments"},
            ],
            "layout": {
                "home": [
                    {
                        "component": "GlobalHealthCard",
                        "props": {"cmd": "saas.monitor.global_health"},
                    },
                    {
                        "component": "TenantStatsChart",
                        "props": {"cmd": "saas.monitor.tenant_stats"},
                    },
                    {"component": "TenantAdminTable", "props": {"cmd": "saas.tenants.list"}},
                ],
            },
        }

    def get_support_manifest(self, session: Session, context: TenantContext) -> dict[str, Any]:
        return {
            "user": {"role": "support", "plan": "system"},
            "theme": {"primary_color": "#006064", "secondary_color": "#B2EBF2", "dark_mode": False},
            "dock": [
                {"id": "client_search", "label": "Buscar Cliente", "icon": "search"},
                {"id": "bot_diagnostics", "label": "Diagnóstico Bot", "icon": "bug_report"},
                {"id": "user_mgmt", "label": "Gestión Usuarios", "icon": "people"},
            ],
            "layout": {
                "home": [
                    {
                        "component": "SupportSearchBox",
                        "props": {"placeholder": "Ingrese ID de Tenant..."},
                    },
                    {
                        "component": "SupportBotStatusCard",
                        "props": {"cmd": "support.bot.status_check"},
                    },
                    {
                        "component": "SupportImpersonationPanel",
                        "props": {"cmd": "support.user.impersonate"},
                    },
                ],
            },
        }

    def get_business_admin_manifest(
        self, session: Session, context: TenantContext
    ) -> dict[str, Any]:
        # Mantenemos el layout dinámico pero añadimos el Dock de Dueño
        manifest = self._get_tenant_manifest(session, context)
        manifest["dock"] = [
            {"id": "sales", "label": "Ventas", "icon": "shopping_cart"},
            {"id": "stock", "label": "Stock", "icon": "inventory_2"},
            {"id": "monitoring", "label": "Monitoreo", "icon": "insights"},
            {"id": "staff", "label": "Personal", "icon": "group"},
        ]
        # Añadimos la herramienta de stock crítico al home del dueño
        if "home" in manifest["layout"]:
            manifest["layout"]["home"].append(
                {
                    "component": "CriticalStockAlert",
                    "props": {"cmd": "business.monitor.critical_stock"},
                }
            )
        return manifest

    def get_employee_manifest(self, session: Session, context: TenantContext) -> dict[str, Any]:
        manifest = self._get_tenant_manifest(session, context)
        manifest["dock"] = [
            {"id": "sales", "label": "Ventas", "icon": "shopping_cart"},
            {"id": "stock", "label": "Stock", "icon": "inventory_2"},
        ]
        return manifest

    def _get_tenant_manifest(self, session: Session, context: TenantContext) -> dict[str, Any]:
        theme = (
            session.execute(
                text("SELECT * FROM ui_themes WHERE tenant_id = :tid"), {"tid": context.tenant_id}
            )
            .mappings()
            .first()
        )

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
                "dock": [],
            },
        }


sdui_engine = SDUIEngine()
