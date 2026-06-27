import logging
import os
from typing import List, Optional
from sqlalchemy import text
from sqlalchemy.orm import Session

from core.types import ServiceResponse
from core.decorators import command
from core.context import TenantContext

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
            import hashlib

            password_hash = hashlib.sha256(password.encode()).hexdigest()

            session.execute(
                text(
                    "INSERT INTO users (email, password_hash, role, tenant_id) VALUES (:email, :pass, :role, :tid)"
                ),
                {
                    "email": username,
                    "pass": password_hash,
                    "role": role,
                    "tid": context.tenant_id,
                },
            )
            session.commit()
            return ServiceResponse.success_res(
                message=f"Employee {username} created successfully."
            )
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
                session.execute(
                    text(
                        "INSERT INTO user_permissions (user_id, permission_key, tenant_id) VALUES (:uid, :pk, :tid) ON CONFLICT DO NOTHING"
                    ),
                    {"uid": user_id, "pk": permission_key, "tid": context.tenant_id},
                )
            else:
                session.execute(
                    text(
                        "DELETE FROM user_permissions WHERE user_id = :uid AND permission_key = :pk AND tenant_id = :tid"
                    ),
                    {"uid": user_id, "pk": permission_key, "tid": context.tenant_id},
                )
            session.commit()
            return ServiceResponse.success_res(
                message="Permission updated successfully."
            )
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
            result = (
                session.execute(
                    text("SELECT id, email, role FROM users WHERE tenant_id = :tid"),
                    {"tid": context.tenant_id},
                )
                .mappings()
                .all()
            )
            return ServiceResponse.success_res(
                data=[dict(u) for u in result], message="Users listed."
            )
        except Exception as e:
            return ServiceResponse.error_res(
                f"Error listing users: {str(e)}", "AUTH_LIST_ERROR"
            )

    @command(
        name="core.get_profile",
        description="Returns the current user and business profile information.",
        params_model={},
    )
    def get_profile(self, session: Session, context: TenantContext) -> ServiceResponse:
        try:
            # Obtener datos del tenant
            tenant = (
                session.execute(
                    text("SELECT name, plan FROM tenants WHERE id = :tid"),
                    {"tid": context.tenant_id},
                )
                .mappings()
                .first()
            )

            # Obtener datos del usuario
            user = (
                session.execute(
                    text("SELECT email, role FROM users WHERE id = :uid"),
                    {"uid": context.user_id},
                )
                .mappings()
                .first()
            )

            if not tenant or not user:
                return ServiceResponse.error_res(
                    "Profile not found", "PROFILE_NOT_FOUND"
                )

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
            return ServiceResponse.error_res(
                f"Error retrieving profile: {str(e)}", "PROFILE_ERROR"
            )

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
            session.execute(text("SELECT 1"))
            return ServiceResponse.success_res(
                data={"db": "OK", "api": "OK"}, message="Infrastructure is healthy."
            )
        except Exception as e:
            return ServiceResponse.error_res(f"Unhealthy: {str(e)}", "SYSTEM_UNHEALTHY")


core_commands = CoreCommandHandler()
