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
        Genera el contrato de arranque completo para la APK.
        """
        # 1. Tema Visual
        theme = (
            session.execute(
                text("SELECT * FROM ui_themes WHERE tenant_id = :tid"), {"tid": context.tenant_id}
            )
            .mappings()
            .first()
        )

        # 2. Layout de la Pantalla Principal (Home)
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

        # 3. Matriz de Permisos (Comandos permitidos)
        # Aquí podríamos listar los comandos del dispatcher que el usuario puede usar
        permissions = []
        # (En una impl. real, filtraríamos los comandos registrados en el dispatcher según el rol)

        return {
            "user": {
                "name": "Usuario",  # Debería venir del contexto/DB
                "role": context.role,
                "plan": context.plan,
            },
            "theme": dict(theme)
            if theme
            else {"primary_color": "#000000", "secondary_color": "#FFFFFF", "dark_mode": False},
            "layout": {
                "home": home_layout["layout_json"] if home_layout else [],
                "dock": [],  # Configuración de la barra inferior
            },
            "permissions": permissions,
        }


sdui_engine = SDUIEngine()
