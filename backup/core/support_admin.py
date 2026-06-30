import logging
import uuid

from sqlalchemy import text
from sqlalchemy.orm import Session

from core.context import TenantContext
from core.decorators import command
from core.types import ServiceResponse

logger = logging.getLogger("OmniCore.SupportAdmin")


class SupportAdminCommandHandler:
    """
    Herramientas de soporte técnico para resolución de incidencias de clientes.
    Permite monitorear la salud de bots y resetear sesiones.
    """

    @command(
        name="support.bot.status_check",
        description="Verifies if the Meta webhook is reaching the bot for a specific tenant.",
        params_model={"tenant_id": "string"},
    )
    def status_check(
        self, session: Session, context: TenantContext, tenant_id: str
    ) -> ServiceResponse:
        try:
            # Verificamos si hay actividad reciente en las conversaciones del bot
            recent_activity = session.execute(
                text(
                    "SELECT count(*) FROM whatsapp_conversations WHERE tenant_id = :tid AND created_at > now() - interval '1 hour'"
                ),
                {"tid": uuid.UUID(tenant_id)},
            ).scalar()

            status = "active" if recent_activity > 0 else "inactive/silent"
            return ServiceResponse.success_res(
                data={"tenant_id": tenant_id, "status": status, "recent_messages": recent_activity},
                message=f"Bot status for {tenant_id} is {status}.",
            )
        except Exception as e:
            return ServiceResponse.error_res(str(e), "SUPPORT_STATUS_ERROR")

    @command(
        name="support.user.impersonate",
        description="Generates a temporary token to access the UI as a specific user of a tenant. High priority audit log.",
        params_model={"tenant_id": "string", "user_id": "string"},
    )
    def impersonate_user(
        self, session: Session, context: TenantContext, tenant_id: str, user_id: str
    ) -> ServiceResponse:
        try:
            # 1. Verificar que el usuario existe en ese tenant
            user = (
                session.execute(
                    text(
                        "SELECT id, email, role, tenant_id FROM users WHERE id = :uid AND tenant_id = :tid"
                    ),
                    {"uid": uuid.UUID(user_id), "tid": uuid.UUID(tenant_id)},
                )
                .mappings()
                .first()
            )

            if not user:
                return ServiceResponse.error_res(
                    "User not found in the specified tenant", "USER_NOT_FOUND"
                )

            # 2. Obtener el plan del tenant para el token
            tenant = (
                session.execute(
                    text("SELECT plan FROM tenants WHERE id = :tid"), {"tid": uuid.UUID(tenant_id)}
                )
                .mappings()
                .first()
            )

            plan = tenant["plan"] if tenant else "free"

            # 3. Generar token temporal (Expiración corta: 1 hora)
            # Usamos la lógica de create_token pero con una duración reducida
            import datetime

            import jwt

            from core.auth import ALGORITHM, SECRET_KEY

            payload = {
                "tenant_id": str(user["tenant_id"]),
                "user_id": str(user["id"]),
                "role": user["role"],
                "plan": plan,
                "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1),
                "impersonated_by": str(context.user_id),
            }
            token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

            # 4. Auditoría de ALTA PRIORIDAD
            session.execute(
                text(
                    "INSERT INTO audit_log (tenant_id, user_id, command, params) VALUES (:tid, :uid, :cmd, :p)"
                ),
                {
                    "tid": uuid.UUID(tenant_id),
                    "uid": context.user_id,
                    "cmd": "SUPPORT_IMPERSONATION_START",
                    "p": f"Support user {context.user_id} impersonating {user['email']} ({user_id})",
                },
            )
            session.commit()

            return ServiceResponse.success_res(
                data={"token": token, "expires_in": "1 hour"},
                message=f"Temporary token generated for {user['email']}.",
            )
        except Exception as e:
            session.rollback()
            return ServiceResponse.error_res(str(e), "IMPERSONATE_ERROR")
