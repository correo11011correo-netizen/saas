import datetime
import hashlib
import json
import os
import secrets
import uuid

import jwt
from sqlalchemy import text
from sqlalchemy.orm import Session

from .context import TenantContext

SECRET_KEY = os.getenv("JWT_SECRET", "OMNICORE_FALLBACK_SECRET_KEY_CHANGE_IN_PROD")
ALGORITHM = "HS256"


class AuthService:
    def register(self, session: Session, email: str, password: str, business_name: str, plan: str = "free") -> dict:
        try:
            # 1. Validar que el plan existe en el catálogo global
            plan_check = session.execute(
                text("SELECT 1 FROM saas_plans WHERE plan_id = :pid"),
                {"pid": plan},
            ).scalar()

            if not plan_check:
                return {"success": False, "error": f"Invalid plan: {plan}"}

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
                    "plan": plan,
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
            token = self.create_token(tenant_id, user_id, "admin", plan)
            return {
                "success": True,
                "token": token,
                "tenant_id": str(tenant_id),
                "webhook_secret": webhook_secret,
                "user": {
                    "username": email,
                    "business_name": business_name,
                    "role": "admin",
                    "plan": plan,
                },
            }
        except Exception as e:
            session.rollback()
            return {"success": False, "error": str(e)}

    def _apply_onboarding_blueprint(self, session: Session, tenant_id: uuid.UUID, business_name: str):
        """
        Aplica la configuración básica necesaria para que el tenant sea operativo
        desde el segundo uno (Credenciales, Bot Settings, Nodos Iniciales).
        """
        # 1. Credenciales placeholder para WhatsApp
        session.execute(
            text(
                "INSERT INTO credentials (id, tenant_id, service_name, account_alias, api_key, metadata) "
                "VALUES (:id, :tid, 'whatsapp', 'Principal', '', :meta)"
            ),
            {
                "id": uuid.uuid4(),
                "tid": tenant_id,
                "meta": json.dumps({"phone_number_id": ""}),
            },
        )

        # 2. Configuración de Sectores del Bot (bot_settings)
        simple_name = business_name.lower().replace(" ", "-").replace(".", "")
        session.execute(
            text(
                """
                INSERT INTO bot_settings (tenant_id, bot_name, welcome_message, farewell_message, handoff_message, support_email, is_global_active)
                VALUES (:tid, :bot_name, :welcome, :farewell, :handoff, :email, TRUE)
                """
            ),
            {
                "tid": tenant_id,
                "bot_name": f"Asistente de {business_name}",
                "welcome": f"¡Hola! Bienvenido a {business_name}. 🤖 Soy tu asistente virtual. ¿En qué puedo ayudarte hoy?",
                "farewell": f"Gracias por contactar a {business_name}. ¡Que tengas un gran día! 👋",
                "handoff": f"He desactivado el bot. Un agente humano de {business_name} se pondrá en contacto contigo en breve. 👨‍💻",
                "email": f"soporte@{simple_name}.com",
            },
        )

        # 3. Nodo de inicio básico
        node_id = uuid.uuid4()
        session.execute(
            text(
                "INSERT INTO bot_nodes (id, name, prompt, tenant_id) "
                "VALUES (:id, 'inicio', :prompt, :tid)"
            ),
            {
                "id": node_id,
                "prompt": f"Bienvenido a {business_name}.\n\nPor favor, elige una opción:\n1. Ver Productos\n2. Soporte",
                "tid": tenant_id,
            },
        )

        options = [
            {"label": "1", "next_node": "productos", "action": "navigate"},
            {"label": "2", "next_node": "soporte", "action": "navigate"},
        ]
        for opt in options:
            session.execute(
                text(
                    "INSERT INTO bot_options (id, node_id, label, next_node_id, action, tenant_id) "
                    "VALUES (:id, :nid, :label, :next, :action, :tid)"
                ),
                {
                    "id": uuid.uuid4(),
                    "nid": node_id,
                    "label": opt["label"],
                    "next": None,
                    "action": opt["action"],
                    "tid": tenant_id,
                },
            )

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
            token = self.create_token(tenant_id, user_id, "admin", plan)
            return {
                "success": True,
                "token": token,
                "tenant_id": str(tenant_id),
                "webhook_secret": webhook_secret,
                "user": {
                    "username": email,
                    "business_name": business_name,
                    "role": "admin",
                    "plan": plan,
                },
            }
        except Exception as e:
            session.rollback()
            return {"success": False, "error": str(e)}

    def authenticate(self, session: Session, email: str, password: str) -> dict | None:
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        user = (
            session.execute(
                text(
                    """SELECT u.id, u.tenant_id, u.role, u.email, t.name as business_name, t.plan
                    FROM users u
                    JOIN tenants t ON u.tenant_id = t.id
                    WHERE u.email = :email AND u.password_hash = :hash"""
                ),
                {"email": email, "hash": password_hash},
            )
            .mappings()
            .first()
        )
        if not user:
            return None
        token = self.create_token(user["tenant_id"], user["id"], user["role"], user["plan"])
        return {
            "token": token,
            "tenant_id": user["tenant_id"],
            "user_id": user["id"],
            "user": {
                "username": user["email"],
                "business_name": user["business_name"],
                "role": user["role"],
                "plan": user["plan"],
            },
        }

    def create_token(self, tenant_id, user_id, role, plan=None) -> str:
        payload = {
            "tenant_id": str(tenant_id),
            "user_id": str(user_id),
            "role": role,
            "plan": plan,
            "exp": datetime.datetime.utcnow() + datetime.timedelta(days=7),
        }
        return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

    def decode_token(self, token: str) -> TenantContext | None:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return TenantContext(
                tenant_id=uuid.UUID(payload["tenant_id"]),
                user_id=uuid.UUID(payload["user_id"]),
                role=payload["role"],
                plan=payload.get("plan", "free"),
            )
        except Exception:
            return None

    def verify_token(self, token: str) -> bool:
        return self.decode_token(token) is not None


auth_service = AuthService()
