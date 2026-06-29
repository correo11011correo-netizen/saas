import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from core.decorators import command
from core.types import ServiceResponse

logger = logging.getLogger("OmniCore.AdvancedUI")


class AdvancedUICommandHandler:
    """
    Comandos para la creación de interfaces complejas.
    Permite definir la librería de componentes y componer paneles avanzados.
    """

    @command(
        name="ui.component.create",
        description="Adds a new component to the library.",
        params_model={"component_id": "string", "name": "string", "default_props": "dict"},
    )
    def create_component(
        self, session: Session, context: Any, component_id: str, name: str, default_props: dict
    ) -> ServiceResponse:
        try:
            session.execute(
                text(
                    "INSERT INTO component_library (component_id, name, default_props) VALUES (:cid, :name, :props)"
                ),
                {"cid": component_id, "name": name, "props": default_props},
            )
            session.commit()
            return ServiceResponse.success_res(message=f"Component {component_id} registered.")
        except Exception as e:
            session.rollback()
            return ServiceResponse.error_res(str(e), "COMPONENT_CREATE_ERROR")

    @command(
        name="ui.panel.compose",
        description="Composes a panel using multiple components.",
        params_model={"panel_id": "uuid", "components": "list"},
    )
    def compose_panel(
        self, session: Session, context: Any, panel_id: str, components: list
    ) -> ServiceResponse:
        """
        components: [{ "component_id": "uuid", "props_override": {}, "position": 0 }]
        """
        try:
            # Limpiar componentes actuales del panel
            session.execute(
                text("DELETE FROM panel_components WHERE panel_id = :pid"), {"pid": panel_id}
            )

            for comp in components:
                session.execute(
                    text(
                        "INSERT INTO panel_components (panel_id, component_id, props_override, position) VALUES (:pid, :cid, :props, :pos)"
                    ),
                    {
                        "pid": panel_id,
                        "cid": comp["component_id"],
                        "props": comp.get("props_override"),
                        "pos": comp.get("position", 0),
                    },
                )
            session.commit()
            return ServiceResponse.success_res(message="Panel composed successfully.")
        except Exception as e:
            session.rollback()
            return ServiceResponse.error_res(str(e), "PANEL_COMPOSE_ERROR")

    @command(
        name="media.upload",
        description="Uploads a file to the system.",
        params_model={
            "tenant_id": "string",
            "file_name": "string",
            "file_type": "string",
            "file_path": "string",
            "file_size": "int",
        },
    )
    def upload_media(self, session: Session, context: Any, **params) -> ServiceResponse:
        try:
            session.execute(
                text(
                    "INSERT INTO media_assets (tenant_id, file_name, file_type, file_path, file_size) VALUES (:tid, :name, :type, :path, :size)"
                ),
                {
                    "tid": params["tenant_id"],
                    "name": params["file_name"],
                    "type": params["file_type"],
                    "path": params["file_path"],
                    "size": params["file_size"],
                },
            )
            session.commit()
            return ServiceResponse.success_res(message="Media asset registered.")
        except Exception as e:
            session.rollback()
            return ServiceResponse.error_res(str(e), "MEDIA_UPLOAD_ERROR")


advanced_ui_commands = AdvancedUICommandHandler()
