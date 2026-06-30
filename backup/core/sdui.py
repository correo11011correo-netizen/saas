import json
import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from core.context import TenantContext

logger = logging.getLogger("OmniCore.SDUI")


class SDUIEngine:
    """
    Motor de Interfaz Dirigida por Servidor (Server-Driven UI).
    Orquestador que resuelve dinámicamente los paneles basándose en la base de datos.
    Sigue la jerarquía: Paneles Globales -> Paneles de Rol -> Paneles de Tenant.
    """

    def get_boot_manifest(self, session: Session, context: TenantContext) -> dict[str, Any]:
        """
        Genera el contrato de arranque resolviendo la configuración dinámica de la DB.
        """
        # 1. Resolver los paneles activos para este usuario/tenant
        panels = self._resolve_panels(session, context)

        # 2. Construir el dock basándose en los paneles encontrados
        dock = [
            {
                "id": p["panel_id"],
                "label": p["name"],
                "icon": p["config_json"].get("icon", "default_icon"),
            }
            for p in panels
        ]

        # Crear un ID de versión basado en el contenido de los paneles
        import hashlib

        version_content = json.dumps([p["panel_id"] for p in panels], sort_keys=True)
        version_id = hashlib.sha256(version_content.encode()).hexdigest()[:12]

        # 3. Resolver el layout general
        manifest = {
            "user": {"role": context.role, "plan": context.plan},
            "theme": self._resolve_theme(session, context),
            "dock": dock,
            "layout": {
                "home": self._resolve_home_layout(session, context),
            },
            "version": version_id,
        }

        return manifest

    def _resolve_panels(self, session: Session, context: TenantContext) -> list[dict]:
        """
        Resuelve los paneles aplicando la jerarquía de prioridades.
        Criterios de selección:
        - Paneles globales activos.
        - Paneles específicos para el rol del usuario.
        - Paneles personalizados para el tenant del usuario (estos sobrescriben globales/rol).
        """
        # Query optimizada para traer todo lo que el usuario puede ver
        query = text("""
            SELECT panel_id, name, config_json
            FROM panel_definitions
            WHERE is_active = true
            AND (
                (required_role IS NULL AND tenant_id IS NULL) OR
                (required_role = :role AND tenant_id IS NULL) OR
                (tenant_id = :tid)
            )
            ORDER BY
                CASE WHEN tenant_id IS NOT NULL THEN 1 ELSE 2 END,
                priority ASC
        """)

        result = (
            session.execute(query, {"role": context.role, "tid": context.tenant_id})
            .mappings()
            .all()
        )

        # Para evitar duplicados (si un panel global es sobrescrito por uno de tenant),
        # usamos un diccionario basado en panel_id.
        unique_panels = {}
        for row in result:
            unique_panels[row["panel_id"]] = row

        return list(unique_panels.values())

    def _resolve_theme(self, session: Session, context: TenantContext) -> dict:
        """Resuelve el tema visual del tenant o el default del sistema."""
        theme = (
            session.execute(
                text("SELECT * FROM ui_themes WHERE tenant_id = :tid"), {"tid": context.tenant_id}
            )
            .mappings()
            .first()
        )
        return (
            dict(theme)
            if theme
            else {"primary_color": "#000000", "secondary_color": "#FFFFFF", "dark_mode": False}
        )

    def _resolve_home_layout(self, session: Session, context: TenantContext) -> list:
        """Resuelve el layout de la pantalla de inicio."""
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
        return home_layout["layout_json"] if home_layout else []


sdui_engine = SDUIEngine()
