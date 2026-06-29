import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from core.decorators import command
from core.types import ServiceResponse

logger = logging.getLogger("OmniCore.DevAdmin")


class DevAdminCommandHandler:
    """
    Comandos exclusivos para el Desarrollador.
    Permiten la inspección de logs de desarrollo y la manipulación de infraestructura.
    """

    @command(
        name="dev.logs.list",
        description="Lists the execution logs for debugging.",
        params_model={"limit": "int", "command": "string", "tenant_id": "string"},
    )
    def list_dev_logs(
        self,
        session: Session,
        context: Any,
        limit: int = 100,
        command: str = None,
        tenant_id: str = None,
    ) -> ServiceResponse:
        # Validar que sea desarrollador o superadmin
        if context.role not in ["developer", "superadmin"]:
            return ServiceResponse.error_res(
                "Forbidden: Developer access only.", "DEV_ACCESS_DENIED"
            )

        try:
            query = "SELECT * FROM dev_logs WHERE 1=1"
            params = {}

            if command:
                query += " AND command = :cmd"
                params["cmd"] = command
            if tenant_id:
                query += " AND tenant_id = :tid"
                params["tid"] = tenant_id

            query += " ORDER BY timestamp DESC LIMIT :limit"
            params["limit"] = limit

            result = session.execute(text(query), params).mappings().all()
            return ServiceResponse.success_res(
                data=[dict(r) for r in result], message="Dev logs retrieved."
            )
        except Exception as e:
            return ServiceResponse.error_res(str(e), "DEV_LOG_ERROR")

    @command(
        name="dev.logs.clear",
        description="Clears the dev logs table.",
        params_model={},
    )
    def clear_dev_logs(self, session: Session, context: Any) -> ServiceResponse:
        if context.role not in ["developer", "superadmin"]:
            return ServiceResponse.error_res(
                "Forbidden: Developer access only.", "DEV_ACCESS_DENIED"
            )

        try:
            session.execute(text("DELETE FROM dev_logs"))
            session.commit()
            return ServiceResponse.success_res(message="Dev logs cleared.")
        except Exception as e:
            session.rollback()
            return ServiceResponse.error_res(str(e), "DEV_LOG_CLEAR_ERROR")


dev_admin_commands = DevAdminCommandHandler()
