import datetime
import hashlib
import json
import os
import secrets
import uuid

import jwt
from sqlalchemy.orm import Session

from .context import TenantContext
from core.data_commands import data_commands

SECRET_KEY = os.getenv("JWT_SECRET", "OMNICORE_FALLBACK_SECRET_KEY_CHANGE_IN_PROD")
ALGORITHM = "HS256"


class AuthService:
    def register(
        self, session: Session, email: str, password: str, business_name: str, plan: str = "free"
    ) -> dict:
        try:
            # 1. Validar que el plan existe en el catálogo global
            plan_res = data_commands.query_data(
                session, 
                TenantContext(tenant_id=None), # Root access for global plans
                entity="saas_plans", 
                filters={"plan_id": plan}
            )

            if not plan_res.success or not plan_res.data:
                return {"success": False, "error": f"Invalid plan: {plan}"}

            tenant_id = uuid.uuid4()
            webhook_secret = secrets.token_urlsafe(32)

            # Insert Tenant
            data_commands.insert_data(
                session, 
                TenantContext(tenant_id=tenant_id), 
                entity="tenants", 
                data={
                    "id": tenant_id, 
                    "name": business_name, 
                    "webhook_secret": webhook_secret, 
                    "plan": plan
                }
            )

            user_id = uuid.uuid4()
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            
            # Insert User
            data_commands.insert_data(
                session, 
                TenantContext(tenant_id=tenant_id), 
                entity="users", 
                data={
                    "id": user_id, 
                    "email": email, 
                    "password_hash": password_hash, 
                    "role": "admin", 
                    "tenant_id": tenant_id
                }
            )

            # Insert Cash Box
            data_commands.insert_data(
                session, 
                TenantContext(tenant_id=tenant_id), 
                entity="cash_box", 
                data={
                    "id": uuid.uuid4(), 
                    "tenant_id": tenant_id, 
                    "abierta": False
                }
            )

            # Aplicar configuración inicial automática
            self._apply_onboarding_blueprint(session, tenant_id, business_name)

            # Insert default frontend manifest entries
            default_modules = ["stock", "whatsapp", "mercado-pago"]
            for module_name in default_modules:
                data_commands.insert_data(
                    session, 
                    TenantContext(tenant_id=tenant_id), 
                    entity="frontend_manifest", 
                    data={
                        "tenant_id": tenant_id, 
                        "module": module_name, 
                        "version": "1.0", 
                        "assets": json.dumps({}), 
                        "active": True
                    }
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

    def _apply_onboarding_blueprint(
        self, session: Session, tenant_id: uuid.UUID, business_name: str
    ):
        """
        Aplica la configuración básica necesaria para que el tenant sea operativo
        desde el segundo uno (Credenciales, Bot Settings, Nodos Iniciales).
        """
        ctx = TenantContext(tenant_id=tenant_id)

        # 1. Credenciales placeholder para WhatsApp
        data_commands.insert_data(
            session, 
            ctx, 
            entity="credentials", 
            data={
                "id": uuid.uuid4(), 
                "tenant_id": tenant_id, 
                "service_name": "whatsapp", 
                "account_alias": "Principal", 
                "api_key": "", 
                "metadata": json.dumps({"phone_number_id": ""})
            }
        )

        # 2. Configuración de Sectores del Bot (bot_settings)
        simple_name = business_name.lower().replace(" ", "-").replace(".", "")
        data_commands.insert_data(
            session, 
            ctx, 
            entity="bot_settings", 
            data={
                "tenant_id": tenant_id, 
                "bot_name": f"Asistente de {business_name}",
                "welcome": f"¡Hola! Bienvenido a {business_name}. 🤖 Soy tu asistente virtual. ¿En qué puedo ayudarte hoy?",
                "farewell": f"Gracias por contactar a {business_name}. ¡Que tengas un gran día! 👋",
                "handoff": f"He desactivado el bot. Un agente humano de {business_name} se pondrá en contacto contigo en breve. 👨‍💻",
                "email": f"soporte@{simple_name}.com",
                "is_global_active": True
            }
        )

        # 3. Nodo de inicio básico
        node_id = uuid.uuid4()
        data_commands.insert_data(
            session, 
            ctx, 
            entity="bot_nodes", 
            data={
                "id": node_id, 
                "name": "inicio", 
                "prompt": f"Bienvenido a {business_name}.\n\nPor favor, elige una opción:\n1. Ver Productos\n2. Soporte", 
                "tenant_id": tenant_id
            }
        )

        options = [
            {"label": "1", "next_node": "productos", "action": "navigate"},
            {"label": "2", "next_node": "soporte", "action": "navigate"},
        ]
        for opt in options:
            data_commands.insert_data(
                session, 
                ctx, 
                entity="bot_options", 
                data={
                    "id": uuid.uuid4(), 
                    "nid": node_id, 
                    "label": opt["label"], 
                    "next": None, 
                    "action": opt["action"], 
                    "tid": tenant_id
                }
            )

    def authenticate(self, session: Session, email: str, password: str) -> dict | None:
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        # 1. Buscar usuario por email y hash
        # Nota: Usamos TenantContext(tenant_id=None) para búsquedas globales de login
        user_res = data_commands.query_data(
            session, 
            TenantContext(tenant_id=None), 
            entity="users", 
            filters={"email": email, "password_hash": password_hash}
        )

        if not user_res.success or not user_res.data:
            return None
        
        user = user_res.data[0]
        tenant_id = user["tenant_id"]
        
        # 2. Buscar datos del tenant
        tenant_res = data_commands.query_data(
            session, 
            TenantContext(tenant_id=tenant_id), 
            entity="tenants", 
            filters={"id": tenant_id}
        )
        
        if not tenant_res.success or not tenant_res.data:
            return None
            
        tenant = tenant_res.data[0]
        
        token = self.create_token(tenant["id"], user["id"], user["role"], tenant["plan"])
        return {
            "token": token,
            "tenant_id": tenant["id"],
            "user_id": user["id"],
            "user": {
                "username": user["email"],
                "business_name": tenant["name"],
                "role": user["role"],
                "plan": tenant["plan"],
            },
        }

    def create_token(self, tenant_id, user_id, role, plan=None) -> str:
        payload = {
            "tenant_id": str(tenant_id) if tenant_id else "SYSTEM",
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
                tenant_id=uuid.UUID(payload["tenant_id"])
                if payload["tenant_id"] != "SYSTEM"
                else None,
                user_id=uuid.UUID(payload["user_id"]),
                role=payload["role"],
                plan=payload.get("plan", "free"),
            )
        except Exception:
            return None

    def verify_token(self, token: str) -> bool:
        return self.decode_token(token) is not None


auth_service = AuthService()
