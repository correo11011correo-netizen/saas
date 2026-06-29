import datetime
import hashlib
import json
import os
import secrets
import uuid

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
            # --- SCHEMA INTEGRITY GUARD ---
            # Asegura la existencia de tablas críticas antes de operar.
            session.execute(
                text(
                    "CREATE TABLE IF NOT EXISTS saas_plans (plan_id VARCHAR(50) PRIMARY KEY, name VARCHAR(100) NOT NULL, monthly_price DECIMAL(12,2) DEFAULT 0, features JSONB DEFAULT '[]');"
                )
            )
            session.execute(
                text(
                    "INSERT INTO saas_plans (plan_id, name, monthly_price) VALUES ('free', 'Plan Gratuito', 0.0) ON CONFLICT DO NOTHING;"
                )
            )
            session.execute(
                text(
                    "CREATE TABLE IF NOT EXISTS tenants (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), name VARCHAR(255) NOT NULL, status VARCHAR(50) DEFAULT 'active', created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP, webhook_secret VARCHAR(255) UNIQUE, plan VARCHAR(50) DEFAULT 'free', business_category VARCHAR(100) DEFAULT 'general');"
                )
            )
            session.execute(
                text(
                    "CREATE TABLE IF NOT EXISTS users (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), email VARCHAR(255) UNIQUE NOT NULL, password_hash VARCHAR(255) NOT NULL, role VARCHAR(50) DEFAULT 'employee', tenant_id UUID REFERENCES tenants(id));"
                )
            )
            session.execute(
                text(
                    "CREATE TABLE IF NOT EXISTS cash_box (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id UUID REFERENCES tenants(id), abierta BOOLEAN DEFAULT false, efectivo_inicial DECIMAL(12,2) DEFAULT 0, ventas_efectivo DECIMAL(12,2) DEFAULT 0, ventas_digital DECIMAL(12,2) DEFAULT 0, hora_apertura TIMESTAMP WITH TIME ZONE);"
                )
            )
            session.execute(
                text(
                    "CREATE TABLE IF NOT EXISTS credentials (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id UUID REFERENCES tenants(id), service_name VARCHAR(100), account_alias VARCHAR(100), api_key TEXT, secret TEXT, metadata JSONB);"
                )
            )
            session.execute(
                text(
                    "CREATE TABLE IF NOT EXISTS bot_profiles (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id UUID REFERENCES tenants(id), name VARCHAR(100) NOT NULL, capabilities JSONB, is_active BOOLEAN DEFAULT TRUE, created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP);"
                )
            )
            session.execute(
                text(
                    "CREATE TABLE IF NOT EXISTS bot_settings (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id UUID REFERENCES tenants(id), bot_profile_id UUID REFERENCES bot_profiles(id), bot_name VARCHAR(100), welcome_message TEXT, farewell_message TEXT, handoff_message TEXT, support_email VARCHAR(255), is_global_active BOOLEAN DEFAULT TRUE, updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP);"
                )
            )
            session.execute(
                text(
                    "CREATE TABLE IF NOT EXISTS bot_nodes (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id UUID REFERENCES tenants(id), bot_profile_id UUID REFERENCES bot_profiles(id), name VARCHAR(100) NOT NULL, prompt TEXT NOT NULL);"
                )
            )
            session.execute(
                text(
                    "CREATE TABLE IF NOT EXISTS bot_options (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id UUID REFERENCES tenants(id), node_id UUID REFERENCES bot_nodes(id), label VARCHAR(100) NOT NULL, next_node_id UUID, action VARCHAR(100));"
                )
            )
            session.execute(
                text(
                    "CREATE TABLE IF NOT EXISTS frontend_manifest (id SERIAL PRIMARY KEY, tenant_id UUID REFERENCES tenants(id), module VARCHAR(100) NOT NULL, version VARCHAR(50) NOT NULL, assets JSONB NOT NULL, active BOOLEAN DEFAULT true, updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP);"
                )
            )
            session.commit()
            # ------------------------------

            # 1. Validar que el plan existe en el catálogo global
            plan_check = session.execute(
                text("SELECT 1 FROM saas_plans WHERE plan_id = :pid"),
                {"pid": plan},
            ).scalar()

            if not plan_check and plan != "free":
                return {
                    "success": False,
                    "error": f"Invalid plan: {plan}. Please use 'free' or contact support.",
                }

            tenant_id = uuid.uuid4()
            webhook_secret = secrets.token_urlsafe(32)

            session.execute(
                text(
                    "INSERT INTO tenants (id, name, webhook_secret, plan) VALUES (:id, :name, :secret, :plan)"
                ),
                {
                    "id": tenant_id,
                    "name": business_name,
                    "secret": webhook_secret,
                    "plan": plan if plan_check else "free",
                },
            )
            user_id = uuid.uuid4()
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            session.execute(
                text(
                    "INSERT INTO users (id, email, password_hash, role, tenant_id) VALUES (:id, :email, :pass, 'admin', :tid)"
                ),
                {
                    "id": user_id,
                    "email": email,
                    "pass": password_hash,
                    "tid": tenant_id,
                },
            )
            session.execute(
                text("INSERT INTO cash_box (id, tenant_id, abierta) VALUES (:id, :tid, false)"),
                {"id": uuid.uuid4(), "tid": tenant_id},
            )

            # Aplicar configuración inicial automática
            self._apply_onboarding_blueprint(session, tenant_id, business_name)

            # Insert default frontend manifest entries
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
            session.commit()
            token = self.create_token(tenant_id, user_id, "admin", plan if plan_check else "free")
            return {
                "success": True,
                "token": token,
                "tenant_id": str(tenant_id),
                "webhook_secret": webhook_secret,
                "user": {
                    "username": email,
                    "business_name": business_name,
                    "role": "admin",
                    "plan": plan if plan_check else "free",
                },
            }
        except Exception as e:
            session.rollback()
            logger.exception("Registration failed: %s", e)
            return {"success": False, "error": str(e)}

    def authenticate(self, session: Session, email: str, password: str) -> dict | None:
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        user = (
            session.execute(
                text(
                    """SELECT u.id, u.tenant_id, u.role, u.email, t.name as business_name, t.plan
                    FROM users u
                    LEFT JOIN tenants t ON u.tenant_id = t.id
                    WHERE u.email = :email AND u.password_hash = :hash"""
                ),
                {"email": email, "hash": password_hash},
            )
            .mappings()
            .first()
        )
        if not user:
            return None

        # El tenant_id puede ser None para superadmin y support
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
