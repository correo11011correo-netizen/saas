import logging
import os
import hashlib

from sqlalchemy.orm import Session

from core.context import TenantContext
from core.decorators import command
from core.types import ServiceResponse
from core.data_commands import data_commands

logger = logging.getLogger("OmniCore.CoreCommands")


class CoreCommandHandler:
    """
    Implementación de comandos de Núcleo Multi-tenant.
    Lógica de gestión de usuarios y sistema.
    """

    @command(
        name="user.invite_employee",
        description="Invites a new employee to the tenant with specific role.",
        params_model={"username": "string", "password": "string", "role": "string"},
    )
    def create_employee_account(
        self,
        session: Session,
        context: TenantContext,
        username: str,
        password: str,
        role: str = "employee",
    ) -> ServiceResponse:
        try:
            password_hash = hashlib.sha256(password.encode()).hexdigest()

            res = data_commands.insert_data(
                session, 
                context, 
                entity="users", 
                data={
                    "email": username, 
                    "password_hash": password_hash, 
                    "role": role, 
                    "tenant_id": context.tenant_id
                }
            )
            if not res.success:
                return res

            session.commit()
            return ServiceResponse.success_res(message=f"Employee {username} created successfully.")
        except Exception as e:
            session.rollback()
            return ServiceResponse.error_res(
                f"Error creating employee: {str(e)}", "AUTH_CREATE_ERROR"
            )

    @command(
        name="user.set_permission",
        description="Assigns or revokes a granular permission key for a user.",
        params_model={
            "user_id": "string",
            "permission_key": "string",
            "granted": "boolean",
        },
    )
    def set_user_permission(
        self,
        session: Session,
        context: TenantContext,
        user_id: str,
        permission_key: str,
        granted: bool,
    ) -> ServiceResponse:
        try:
            if granted:
                res = data_commands.insert_data(
                    session, 
                    context, 
                    entity="user_permissions", 
                    data={
                        "user_id": user_id, 
                        "permission_key": permission_key, 
                        "tenant_id": context.tenant_id
                    }
                )
                if not res.success:
                    # If it fails because of conflict, we just ignore it (equivalent to ON CONFLICT DO NOTHING)
                    if "conflict" in str(res.error).lower() or "duplicate" in str(res.error).lower():
                        pass
                    else:
                        return res
            else:
                # Delete requires ID
                res_id = data_commands.query_data(
                    session, 
                    context, 
                    entity="user_permissions", 
                    filters={"user_id": user_id, "permission_key": permission_key}
                )
                if res_id.success and res_id.data:
                    perm_id = res_id.data[0]["id"]
                    data_commands.delete_data(
                        session, context, entity="user_permissions", record_id=perm_id
                    )

            session.commit()
            return ServiceResponse.success_res(message="Permission updated successfully.")
        except Exception as e:
            session.rollback()
            return ServiceResponse.error_res(
                f"Error setting permission: {str(e)}", "AUTH_PERMISSION_ERROR"
            )

    @command(
        name="user.list",
        description="Lists all users/employees of the tenant.",
        params_model={},
    )
    def list_users(self, session: Session, context: TenantContext) -> ServiceResponse:
        try:
            res = data_commands.query_data(
                session, context, entity="users"
            )
            if not res.success:
                return res

            # Filter fields as original code did (id, email, role)
            filtered_data = [
                {"id": u["id"], "email": u["email"], "role": u["role"]} 
                for u in res.data
            ]
            return ServiceResponse.success_res(
                data=filtered_data, message="Users listed."
            )
        except Exception as e:
            return ServiceResponse.error_res(f"Error listing users: {str(e)}", "AUTH_LIST_ERROR")

    @command(
        name="core.get_profile",
        description="Returns the current user and business profile information.",
        params_model={},
    )
    def get_profile(self, session: Session, context: TenantContext) -> ServiceResponse:
        try:
            # Obtener datos del tenant
            res_tenant = data_commands.query_data(
                session, context, entity="tenants", filters={"id": context.tenant_id}
            )
            # Obtener datos del usuario
            res_user = data_commands.query_data(
                session, context, entity="users", filters={"id": context.user_id}
            )

            if not res_tenant.success or not res_tenant.data or not res_user.success or not res_user.data:
                return ServiceResponse.error_res("Profile not found", "PROFILE_NOT_FOUND")

            tenant = res_tenant.data[0]
            user = res_user.data[0]

            return ServiceResponse.success_res(
                data={
                    "business_name": tenant["name"],
                    "plan": tenant["plan"],
                    "username": user["email"],
                    "role": user["role"],
                },
                message="Profile retrieved successfully.",
            )
        except Exception as e:
            return ServiceResponse.error_res(f"Error retrieving profile: {str(e)}", "PROFILE_ERROR")

    @command(
        name="system.info",
        description="Provides general information about the system, version, and data model.",
        params_model={},
    )
    def get_info(self, session: Session, context: TenantContext) -> ServiceResponse:
        version = os.getenv("SYSTEM_VERSION", "1.0.0-stable")
        return ServiceResponse.success_res(
            message=f"OmniCore-AI v{version} is a stateless Meta-Orchestrator.",
            data={"version": version, "architecture": "Dispatcher Pattern"},
        )

    @command(
        name="system.get_health",
        description="Performs a comprehensive health check of the infrastructure.",
        params_model={},
    )
    def get_health(self, session: Session, context: TenantContext) -> ServiceResponse:
        try:
            # Use a simple query on any table to check connectivity instead of 'SELECT 1'
            res = data_commands.query_data(
                session, TenantContext(tenant_id=None), entity="tenants", limit=1
            )
            if not res.success:
                raise Exception(res.error)
            
            return ServiceResponse.success_res(
                data={"db": "OK", "api": "OK"}, message="Infrastructure is healthy."
            )
        except Exception as e:
            return ServiceResponse.error_res(f"Unhealthy: {str(e)}", "SYSTEM_UNHEALTHY")


core_commands = CoreCommandHandler()
