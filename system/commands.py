import logging

from sqlalchemy import text
from sqlalchemy.orm import Session

from core.context import TenantContext
from core.decorators import command
from core.types import ServiceResponse

logger = logging.getLogger("OmniCore.SystemCommands")


class SystemCommandHandler:
    """
    Implementación profesional de comandos de Sistema.
    Lógica directa de auditoría, credenciales y usuarios.
    """

    @command(
        name="system.audit.get_logs",
        description="Retrieves the audit trail for a specific business application.",
        params_model={"limit": "int", "offset": "int", "command": "str"},
    )
    def get_logs(
        self,
        session: Session,
        context: TenantContext,
        limit: int = 50,
        offset: int = 0,
        command: str | None = None,
    ) -> ServiceResponse:
        try:
            query = "SELECT id, tenant_id, user_id, command, params, timestamp FROM audit_log WHERE tenant_id = :tid"
            params = {"tid": context.tenant_id}
            if command:
                query += " AND command = :command"
                params["command"] = command
            query += " ORDER BY timestamp DESC LIMIT :limit OFFSET :offset"
            params["limit"] = limit
            params["offset"] = offset

            result = session.execute(text(query), params).mappings().all()
            return ServiceResponse.success_res(
                data=[dict(row) for row in result], message="Audit logs retrieved."
            )
        except Exception as e:
            return ServiceResponse.error_res(f"Error: {str(e)}", "AUDIT_GET_ERROR")

    @command(
        name="system.users.create",
        description="Creates a new employee user in the business database.",
        params_model={"username": "string", "password": "string", "role": "string"},
    )
    def create_user(
        self,
        session: Session,
        context: TenantContext,
        username: str,
        password: str,
        role: str = "employee",
    ) -> ServiceResponse:
        try:
            import hashlib

            password_hash = hashlib.sha256(password.encode()).hexdigest()

            session.execute(
                text(
                    "INSERT INTO users (email, password_hash, role, tenant_id) VALUES (:email, :pass, :role, :tid)"
                ),
                {"email": username, "pass": password_hash, "role": role, "tid": context.tenant_id},
            )
            session.commit()
            return ServiceResponse.success_res(message=f"User {username} created successfully.")
        except Exception as e:
            session.rollback()
            return ServiceResponse.error_res(f"Error creating user: {str(e)}", "USER_CREATE_ERROR")

    @command(
        name="system.users.list",
        description="Lists all employees and their assigned permissions.",
        params_model={},
    )
    def list_users(self, session: Session, context: TenantContext) -> ServiceResponse:
        try:
            result = (
                session.execute(
                    text("SELECT id, email, role FROM users WHERE tenant_id = :tid"),
                    {"tid": context.tenant_id},
                )
                .mappings()
                .all()
            )

            return ServiceResponse.success_res(
                data=[dict(row) for row in result], message="Employees listed."
            )
        except Exception as e:
            return ServiceResponse.error_res(f"Error listing users: {str(e)}", "USER_LIST_ERROR")


system_commands = SystemCommandHandler()
