import logging
import uuid

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
        description="Retrieves the audit trail. SuperAdmins and Support can specify a tenant_id to view other businesses.",
        params_model={"limit": "int", "offset": "int", "command": "str", "tenant_id": "string"},
    )
    def get_logs(
        self,
        session: Session,
        context: TenantContext,
        limit: int = 50,
        offset: int = 0,
        command: str | None = None,
        tenant_id: str | None = None,
    ) -> ServiceResponse:
        try:
            # Determinar qué tenant auditar
            # 1. Si es superadmin o support, puede usar el tenant_id pasado por parámetro
            # 2. Si no, se usa obligatoriamente el tenant_id del contexto
            target_tid = None
            if context.role in ["superadmin", "support"]:
                target_tid = uuid.UUID(tenant_id) if tenant_id else context.tenant_id
            else:
                target_tid = context.tenant_id

            if not target_tid:
                return ServiceResponse.error_res(
                    "No tenant context available for auditing.", "NO_TENANT"
                )

            query = "SELECT id, tenant_id, user_id, command, params, timestamp FROM audit_log WHERE tenant_id = :tid"
            params = {"tid": target_tid}
            if command:
                query += " AND command = :command"
                params["command"] = command
            query += " ORDER BY timestamp DESC LIMIT :limit OFFSET :offset"
            params["limit"] = limit
            params["offset"] = offset

            result = session.execute(text(query), params).mappings().all()
            return ServiceResponse.success_res(
                data=[dict(row) for row in result],
                message=f"Audit logs retrieved for tenant {target_tid}.",
            )
        except Exception as e:
            return ServiceResponse.error_res(f"Error: {str(e)}", "AUDIT_GET_ERROR")

    @command(
        name="system.users.create",
        description="Creates a new user. SuperAdmins can create system users, Support/Admin can create business users.",
        params_model={
            "username": "string",
            "password": "string",
            "role": "string",
            "tenant_id": "string",
        },
    )
    def create_user(
        self,
        session: Session,
        context: TenantContext,
        username: str,
        password: str,
        role: str = "employee",
        tenant_id: str | None = None,
    ) -> ServiceResponse:
        try:
            import hashlib

            password_hash = hashlib.sha256(password.encode()).hexdigest()

            # Determinar el tenant destino
            target_tid = None
            if context.role == "superadmin":
                # El superadmin puede crear usuarios de sistema (sin tenant) o usuarios de negocio
                target_tid = uuid.UUID(tenant_id) if tenant_id else None
            elif context.role == "support":
                # El soporte debe especificar un tenant_id para crear un empleado
                if not tenant_id:
                    return ServiceResponse.error_res(
                        "tenant_id is required for support to create users.", "TID_REQUIRED"
                    )
                target_tid = uuid.UUID(tenant_id)
            else:
                # El admin del negocio crea usuarios para su propio tenant
                target_tid = context.tenant_id

            session.execute(
                text(
                    "INSERT INTO users (email, password_hash, role, tenant_id) VALUES (:email, :pass, :role, :tid)"
                ),
                {"email": username, "pass": password_hash, "role": role, "tid": target_tid},
            )
            session.commit()
            return ServiceResponse.success_res(
                message=f"User {username} created successfully as {role}."
            )
        except Exception as e:
            session.rollback()
            return ServiceResponse.error_res(f"Error creating user: {str(e)}", "USER_CREATE_ERROR")

    @command(
        name="system.users.list",
        description="Lists users. SuperAdmins and Support can specify a tenant_id.",
        params_model={"tenant_id": "string"},
    )
    def list_users(
        self, session: Session, context: TenantContext, tenant_id: str | None = None
    ) -> ServiceResponse:
        try:
            target_tid = None
            if context.role in ["superadmin", "support"]:
                target_tid = uuid.UUID(tenant_id) if tenant_id else context.tenant_id
            else:
                target_tid = context.tenant_id

            if not target_tid:
                # Si es superadmin y no hay tid, listamos usuarios de sistema
                result = (
                    session.execute(
                        text("SELECT id, email, role FROM users WHERE tenant_id IS NULL")
                    )
                    .mappings()
                    .all()
                )
            else:
                result = (
                    session.execute(
                        text("SELECT id, email, role FROM users WHERE tenant_id = :tid"),
                        {"tid": target_tid},
                    )
                    .mappings()
                    .all()
                )

            return ServiceResponse.success_res(
                data=[dict(row) for row in result], message="Users listed successfully."
            )
        except Exception as e:
            return ServiceResponse.error_res(f"Error listing users: {str(e)}", "USER_LIST_ERROR")


system_commands = SystemCommandHandler()
