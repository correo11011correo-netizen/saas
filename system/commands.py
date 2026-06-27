import json
import logging
import uuid
from typing import Any, Dict, Optional
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.core.dispatcher.core_types import CoreContext, ServiceResponse
from src.core.dispatcher.decorators import command
from src.infrastructure.db.core_db_manager import core_db_manager
from src.infrastructure.repositories.user_repository import UserRepository

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
        context: CoreContext,
        limit: int = 50,
        offset: int = 0,
        command: Optional[str] = None,
    ) -> ServiceResponse:
        try:
            query = "SELECT id, agent_id, command, status, message, timestamp FROM system_audit_log WHERE app_id = :app_id"
            params = {"app_id": context.app_id}
            if command:
                query += " AND command = :command"
                params["command"] = command
            query += " ORDER BY timestamp DESC LIMIT :limit OFFSET :offset"
            params["limit"] = limit
            params["offset"] = offset
            results = core_db_manager.execute_raw(query, params).mappings().all()
            return ServiceResponse.success_res(
                data=[dict(row) for row in results], message="Audit logs retrieved."
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
        context: CoreContext,
        username: str,
        password: str,
        role: str = "employee",
    ) -> ServiceResponse:
        try:
            repo = UserRepository(session, context.business_id)
            import hashlib

            password_hash = hashlib.sha256(password.encode()).hexdigest()
            repo.create_user(username, password_hash, role=role)
            session.commit()
            return ServiceResponse.success_res(
                message=f"User {username} created successfully."
            )
        except Exception as e:
            session.rollback()
            return ServiceResponse.error_res(
                f"Error creating user: {str(e)}", "USER_CREATE_ERROR"
            )

    @command(
        name="system.users.list",
        description="Lists all employees and their assigned permissions.",
        params_model={},
    )
    def list_users(self, session: Session, context: CoreContext) -> ServiceResponse:
        try:
            repo = UserRepository(session, context.business_id)
            users = repo.list_users()
            detailed_users = []
            for user in users:
                user_data = dict(user)
                user_data["permissions"] = repo.get_user_permissions(user["id"])
                detailed_users.append(user_data)
            return ServiceResponse.success_res(
                data=detailed_users, message="Employees listed."
            )
        except Exception as e:
            return ServiceResponse.error_res(
                f"Error listing users: {str(e)}", "USER_LIST_ERROR"
            )


system_commands = SystemCommandHandler()
