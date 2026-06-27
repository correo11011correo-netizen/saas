import logging
from typing import Any, Dict
from sqlalchemy import text
from sqlalchemy.orm import Session
from core.dispatcher import dispatcher
from core.context import TenantContext
import uuid

logger = logging.getLogger("OmniCore.BotEngine")


class BotEngine:
    def _get_settings(self, session: Session, tenant_id: str, account_alias: str) -> Dict[str, Any]:
        """
        Obtiene la configuración del bot específico para un alias.
        """
        settings = (
            session.execute(
                text("SELECT * FROM bot_settings WHERE tenant_id = :tid AND account_alias = :alias"),
                {"tid": tenant_id, "alias": account_alias},
            )
            .mappings()
            .first()
        )

        if settings:
            return dict(settings)

        # FALLBACKS: Valores predeterminados integrados
        return {
            "bot_name": "Asistente Virtual",
            "welcome_message": "¡Hola! Bienvenido. 🤖 Soy tu asistente virtual. ¿En qué puedo ayudarte hoy?",
            "farewell_message": "Gracias por contactarnos. ¡Que tengas un gran día! 👋",
            "handoff_message": "He desactivado el bot. Un agente humano se pondrá en contacto contigo en breve. 👨‍💻",
            "support_email": "soporte@negocio.com",
            "is_global_active": True,
        }

    def process_message(
        self, session: Session, tenant_id: str, sender: str, text_message: str, account_alias: str
    ):
        """
        Procesa el mensaje recibido integrando la arquitectura de Sectores:
        Configuración Global -> Bienvenida -> Menú Interactivo.
        """
        logger.info(f"BotEngine recibiendo mensaje de {sender} para alias {account_alias}: {text_message}")

        # 1. REGISTRAR MENSAJE ENTRANTE
        session.execute(
            text(
                "INSERT INTO whatsapp_conversations (phone_number, sender_type, message, message_type, tenant_id, account_alias) "
                "VALUES (:phone, 'user', :msg, 'text', :tid, :alias)"
            ),
            {"phone": sender, "msg": text_message, "tid": tenant_id, "alias": account_alias},
        )

        # 2. GESTIONAR SESIÓN
        # Verificamos si es la primera vez que el usuario escribe en esta sesión/tenant
        msg_count = session.execute(
            text(
                "SELECT count(*) FROM whatsapp_conversations WHERE phone_number = :phone AND tenant_id = :tid"
            ),
            {"phone": sender, "tid": tenant_id},
        ).scalar()

        is_first_message = msg_count <= 1

        session.execute(
            text(
                """
                INSERT INTO whatsapp_sessions (tenant_id, phone_number, account_alias, is_bot_active, current_node_id)
                VALUES (:tid, :phone, :alias, TRUE, NULL)
                ON CONFLICT (tenant_id, phone_number)
                DO UPDATE SET is_bot_active = CASE WHEN :first THEN TRUE ELSE whatsapp_sessions.is_bot_active END,
                              current_node_id = CASE WHEN :first THEN NULL ELSE whatsapp_sessions.current_node_id END,
                              account_alias = EXCLUDED.account_alias
                """
            ),
            {"tid": tenant_id, "phone": sender, "alias": account_alias, "first": is_first_message},
        )
        session.commit()

        session_data = (
            session.execute(
                text(
                    "SELECT current_node_id, account_alias, is_bot_active FROM whatsapp_sessions "
                    "WHERE phone_number = :phone AND tenant_id = :tid"
                ),
                {"phone": sender, "tid": tenant_id},
            )
            .mappings()
            .first()
        )

        if not session_data:
            logger.error(f"No se pudo recuperar la sesión para {sender}")
            return

        current_node_id = session_data["current_node_id"]
        is_bot_active = session_data.get("is_bot_active", True)

        if not is_bot_active:
            return

        settings = self._get_settings(session, tenant_id, account_alias)

        if not settings.get("is_global_active", True):
            self._send_immediate_response(session, tenant_id, sender, settings["handoff_message"], account_alias)
            return

        # --- LÓGICA DE TRANSICIÓN MEJORADA ---

        # Caso A: Primer mensaje -> Bienvenida + Posicionamiento en Nodo Inicio
        if is_first_message:
            logger.info(f"Flujo de Bienvenida para {sender}")

            node_inicio = (
                session.execute(
                    text("SELECT id, prompt FROM bot_nodes WHERE name = 'inicio' AND tenant_id = :tid AND account_alias = :alias"),
                    {"tid": tenant_id, "alias": account_alias},
                ).mappings().first()
            )

            # Enviamos la bienvenida + el menú del nodo inicio inmediatamente
            msg_final = settings["welcome_message"]
            if node_inicio:
                msg_final += f"\n\n{node_inicio['prompt']}"

            self._send_immediate_response(session, tenant_id, sender, msg_final, account_alias)

            if node_inicio:
                session.execute(
                    text("UPDATE whatsapp_sessions SET current_node_id = :nid WHERE phone_number = :phone AND tenant_id = :tid"),
                    {"nid": node_inicio["id"], "phone": sender, "tid": tenant_id},
                )
                session.commit()
            return

        # Caso B: Interacción con Menús (Nodos)
        if current_node_id:
            logger.info(f"Procesando opción '{text_message}' en nodo {current_node_id}")
            option = (
                session.execute(
                    text(
                        "SELECT next_node_id, action FROM bot_options "
                        "WHERE node_id = :nid AND (label = :label OR label = :label_num) AND tenant_id = :tid AND account_alias = :alias"
                    ),
                    {"nid": current_node_id, "label": text_message, "label_num": text_message.strip(), "tid": tenant_id, "alias": account_alias},
                ).mappings().first()
            )

            if option:
                # Si la opción tiene un nodo siguiente, navegamos
                if option["next_node_id"]:
                    node = (
                        session.execute(
                            text("SELECT id, prompt FROM bot_nodes WHERE id = :nid AND tenant_id = :tid AND account_alias = :alias"),
                            {"nid": option["next_node_id"], "tid": tenant_id, "alias": account_alias},
                        ).mappings().first()
                    )
                    if node:
                        self._send_immediate_response(session, tenant_id, sender, node["prompt"], account_alias)
                        session.execute(
                            text("UPDATE whatsapp_sessions SET current_node_id = :nid WHERE phone_number = :phone AND tenant_id = :tid"),
                            {"nid": node["id"], "phone": sender, "tid": tenant_id},
                        )
                        session.commit()
                        return

                # Si la opción tiene una ACCIÓN (ej: 'list_products'), el dispatcher debería manejarlo
                # Aquí podríamos expandir para que 'action' ejecute comandos del sistema.
                if option["action"] == "list_products":
                    # Este es un trigger especial para el bot de ventas
                    # Simulamos la respuesta del comando de stock
                    self._send_immediate_response(session, tenant_id, sender, "Consultando stock... 📦", account_alias)
                    # (La lógica de ejecución de comandos se integraría aquí o vía dispatcher)
                    return

        # Fallback: Repetir menú actual
        node = (
            session.execute(
                text("SELECT prompt FROM bot_nodes WHERE id = :nid AND tenant_id = :tid AND account_alias = :alias"),
                {"nid": current_node_id, "tid": tenant_id, "alias": account_alias},
            ).mappings().first()
        )
        if node:
            self._send_immediate_response(session, tenant_id, sender, node["prompt"], account_alias)
    def _send_immediate_response(
        self, session, tenant_id, sender, body, alias: str
    ):
        """Helper para enviar mensajes vía dispatcher rápidamente."""
        tenant_uuid = (
            tenant_id if isinstance(tenant_id, uuid.UUID) else uuid.UUID(tenant_id)
        )
        context = TenantContext(
            tenant_id=tenant_uuid,
            user_id=uuid.UUID("00000000-0000-0000-0000-000000000000"),
            role="system",
        )
        dispatcher.execute(
            "whatsapp.send_text",
            {"to": sender, "body": body, "account_alias": alias},
            context,
        )
