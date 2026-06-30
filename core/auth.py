import datetime
import json
import os
import secrets
import uuid

import bcrypt
import jwt
from sqlalchemy import text
from sqlalchemy.orm import Session

from core.logger import logger

from .context import TenantContext

SECRET_KEY = os.getenv("JWT_SECRET", "OMNICORE_FALLBACK_SECRET_KEY_CHANGE_IN_PROD")
ALGORITHM = "HS256"


class AuthService:
    def register(
        self, session: Session, email: str, password: str, business_name: str, plan: str = "free"
    ) -> dict:
        try:
            # 1. Validar el plan
            plan_check = session.execute(
                text("SELECT 1 FROM saas_plans WHERE plan_id = :pid"),
                {"pid": plan},
            ).scalar()

            if not plan_check and plan != "free":
                return {"success": False, "error": f"Invalid plan: {plan}."}

            effective_plan = plan if plan_check else "free"

            # 2. Orquestar la creación modular
            tenant_id, webhook_secret = self._create_tenant(session, business_name, effective_plan)
            user_id = self._create_admin_user(session, email, password, tenant_id)
            self._setup_initial_state(session, tenant_id)
            self._initialize_frontend_manifest(session, tenant_id)

            session.commit()

            token = self.create_token(tenant_id, user_id, "admin", effective_plan)
            return {
                "success": True,
                "token": token,
                "tenant_id": str(tenant_id),
                "webhook_secret": webhook_secret,
                "user": {
                    "username": email,
                    "business_name": business_name,
                    "role": "admin",
                    "plan": effective_plan,
                },
            }
        except Exception as e:
            session.rollback()
            logger.exception("Registration failed: %s", e)
            return {"success": False, "error": str(e)}

    def _create_tenant(self, session: Session, name: str, plan: str) -> tuple[uuid.UUID, str]:
        tenant_id = uuid.uuid4()
        webhook_secret = secrets.token_urlsafe(32)
        session.execute(
            text(
                "INSERT INTO tenants (id, name, webhook_secret, plan) VALUES (:id, :name, :secret, :plan)"
            ),
            {"id": tenant_id, "name": name, "secret": webhook_secret, "plan": plan},
        )
        return tenant_id, webhook_secret

    def _create_admin_user(
        self, session: Session, email: str, password: str, tenant_id: uuid.UUID
    ) -> uuid.UUID:
        user_id = uuid.uuid4()
        password_bytes = password.encode("utf-8")
        salt = bcrypt.gensalt()
        password_hash = bcrypt.hashpw(password_bytes, salt).decode("utf-8")
        session.execute(
            text(
                "INSERT INTO users (id, email, password_hash, role, tenant_id) VALUES (:id, :email, :pass, 'admin', :tid)"
            ),
            {"id": user_id, "email": email, "pass": password_hash, "tid": tenant_id},
        )
        return user_id

    def _setup_initial_state(self, session: Session, tenant_id: uuid.UUID):
        # Caja chica inicial
        session.execute(
            text("INSERT INTO cash_box (id, tenant_id, abierta) VALUES (:id, :tid, false)"),
            {"id": uuid.uuid4(), "tid": tenant_id},
        )
        # Aplicar blueprint de onboarding (si existe la función en el servicio)
        if hasattr(self, "_apply_onboarding_blueprint"):
            self._apply_onboarding_blueprint(session, tenant_id, "New Business")

    def _initialize_frontend_manifest(self, session: Session, tenant_id: uuid.UUID):
        default_modules = ["stock", "whatsapp", "mercado-pago"]
        for module_name in default_modules:
            session.execute(
                text(
                    "INSERT INTO frontend_manifest (tenant_id, module, version, assets, active) VALUES (:tid, :module, :version, :assets, true)"
                ),
                {
                    "tid": tenant_id,
                    "module": module_name,
                    "version": "1.0",
                    "assets": json.dumps({}),
                },
            )

    def authenticate(self, session: Session, email: str, password: str) -> dict | None:
        user = (
            session.execute(
                text(
                    """SELECT u.id, u.tenant_id, u.role, u.email, u.password_hash, t.name as business_name, t.plan
                    FROM users u
                    LEFT JOIN tenants t ON u.tenant_id = t.id
                    WHERE u.email = :email"""
                ),
                {"email": email},
            )
            .mappings()
            .first()
        )
        if not user:
            return None

        # Use bcrypt to check the password
        try:
            if bcrypt.checkpw(password.encode("utf-8"), user["password_hash"].encode("utf-8")):
                token = self.create_token(user["tenant_id"], user["id"], user["role"], user["plan"])
                return {
                    "token": token,
                    "tenant_id": user["tenant_id"],
                    "user_id": user["id"],
                    "user": {
                        "username": user["email"],
                        "business_name": user["business_name"] or "OmniCore System",
                        "role": user["role"],
                        "plan": user["plan"] or "system",
                    },
                }
        except Exception:
            return None

        return None

    def create_token(self, tenant_id, user_id, role, plan=None) -> str:
        payload = {
            "tenant_id": str(tenant_id) if tenant_id else "SYSTEM",
            "user_id": str(user_id),
            "role": role,
            "plan": plan or "system",
            "exp": datetime.datetime.utcnow() + datetime.timedelta(days=7),
        }
        return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

    def decode_token(self, token: str) -> TenantContext | None:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return TenantContext(
                tenant_id=uuid.UUID(payload["tenant_id"])
                if payload["tenant_id"] != "SYSTEM"
                else None,
                user_id=uuid.UUID(payload["user_id"]),
                role=payload["role"],
                plan=payload.get("plan", "system"),
            )
        except Exception:
            return None

    def verify_token(self, token: str) -> bool:
        return self.decode_token(token) is not None


auth_service = AuthService()
