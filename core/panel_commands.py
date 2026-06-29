import json
import logging
import uuid

from sqlalchemy import text
from sqlalchemy.orm import Session

from core.context import TenantContext
from core.decorators import command
from core.types import ServiceResponse

logger = logging.getLogger("OmniCore.PanelCommands")


class PanelCommandHandler:
    """
    Gestión dinámica de la UI. Permite crear, editar y organizar
    los paneles que el SDUIEngine entrega a los clientes y roles.
    """

    @command(
        name="panel.create",
        description="Creates a new UI panel definition.",
        params_model={
            "panel_id": "string",
            "name": "string",
            "config_json": "dict",
            "required_role": "string",
            "tenant_id": "string",
            "priority": "string",
        },
    )
    def create_panel(
        self,
        session: Session,
        context: TenantContext,
        panel_id: str,
        name: str,
        config_json: dict,
        required_role: str = None,
        tenant_id: str = None,
        priority: str = "0",
    ) -> ServiceResponse:
        try:
            session.execute(
                text(
                    """
                    INSERT INTO panel_definitions (panel_id, name, config_json, required_role, tenant_id, priority)
                    VALUES (:pid, :name, :conf, :role, :tid, :prio)
                    """
                ),
                {
                    "pid": panel_id,
                    "name": name,
                    "conf": json.dumps(
                        config_json
                    ),  # Assumed json is handled by SQLAlchemy JSON type, but just in case
                    "role": required_role,
                    "tid": uuid.UUID(tenant_id) if tenant_id else None,
                    "prio": priority,
                },
            )
            session.commit()
            return ServiceResponse.success_res(message=f"Panel {panel_id} created successfully.")
        except Exception as e:
            session.rollback()
            return ServiceResponse.error_res(
                f"Error creating panel: {str(e)}", "PANEL_CREATE_ERROR"
            )

    @command(
        name="panel.update",
        description="Updates an existing panel's configuration or access rules.",
        params_model={
            "panel_id": "string",
            "name": "string",
            "config_json": "dict",
            "required_role": "string",
            "tenant_id": "string",
            "priority": "string",
            "is_active": "boolean",
        },
    )
    def update_panel(
        self,
        session: Session,
        context: TenantContext,
        panel_id: str,
        name: str = None,
        config_json: dict = None,
        required_role: str = None,
        tenant_id: str = None,
        priority: str = None,
        is_active: bool = None,
    ) -> ServiceResponse:
        try:
            # We build the update query dynamically based on provided params
            updates = []
            params = {"pid": panel_id}

            if name:
                updates.append("name = :name")
                params["name"] = name
            if config_json:
                updates.append("config_json = :conf")
                params["conf"] = config_json
            if required_role is not None:
                updates.append("required_role = :role")
                params["role"] = required_role
            if tenant_id:
                updates.append("tenant_id = :tid")
                params["tid"] = uuid.UUID(tenant_id)
            if priority:
                updates.append("priority = :prio")
                params["prio"] = priority
            if is_active is not None:
                updates.append("is_active = :active")
                params["active"] = is_active

            if not updates:
                return ServiceResponse.error_res(
                    "No update parameters provided", "PANEL_UPDATE_NO_DATA"
                )

            query = f"UPDATE panel_definitions SET {', '.join(updates)} WHERE panel_id = :pid"
            session.execute(text(query), params)
            session.commit()
            return ServiceResponse.success_res(message=f"Panel {panel_id} updated successfully.")
        except Exception as e:
            session.rollback()
            return ServiceResponse.error_res(
                f"Error updating panel: {str(e)}", "PANEL_UPDATE_ERROR"
            )

    @command(
        name="panel.list",
        description="Lists all panels and their access rules.",
        params_model={},
    )
    def list_panels(self, session: Session, context: TenantContext) -> ServiceResponse:
        try:
            result = (
                session.execute(text("SELECT * FROM panel_definitions ORDER BY priority ASC"))
                .mappings()
                .all()
            )
            return ServiceResponse.success_res(
                data=[dict(r) for r in result], message="Panels listed."
            )
        except Exception as e:
            return ServiceResponse.error_res(f"Error listing panels: {str(e)}", "PANEL_LIST_ERROR")

    @command(
        name="panel.delete",
        description="Deletes a panel definition.",
        params_model={"panel_id": "string"},
    )
    def delete_panel(
        self, session: Session, context: TenantContext, panel_id: str
    ) -> ServiceResponse:
        try:
            session.execute(
                text("DELETE FROM panel_definitions WHERE panel_id = :pid"),
                {"pid": panel_id},
            )
            session.commit()
            return ServiceResponse.success_res(message=f"Panel {panel_id} deleted.")
        except Exception as e:
            session.rollback()
            return ServiceResponse.error_res(
                f"Error deleting panel: {str(e)}", "PANEL_DELETE_ERROR"
            )


# Singleton
panel_commands = PanelCommandHandler()
