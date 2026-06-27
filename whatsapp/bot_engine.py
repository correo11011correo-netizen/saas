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

        # 2. GESTIONAR SESIÓN PRIMERO (Insertar/Actualizar con el alias correcto)
        msg_count = session.execute(
            text(
                "SELECT count(*) FROM whatsapp_conversations WHERE phone_number = :phone AND tenant_id = :tid AND account_alias = :alias"
            ),
            {"phone": sender, "tid": tenant_id, "alias": account_alias},
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
                              account_alias = EXCLUDED.account_alias -- Asegurar que el alias siempre esté actualizado
        session.execute(
            text(
                """
                INSERT INTO whatsapp_sessions (tenant_id, phone_number, account_alias, is_bot_active, current_node_id)
                VALUES (:tid, :phone, :alias, TRUE, NULL)
                ON CONFLICT (tenant_id, phone_number)
                DO UPDATE SET is_bot_active = CASE WHEN :first THEN TRUE ELSE whatsapp_sessions.is_bot_active END,
                              current_node_id = CASE WHEN :first THEN NULL ELSE whatsapp_sessions.current_node_id END,
                              account_alias = EXCLUDED.account_alias -- Asegurar que el alias siempre esté actualizado
                """
            ),
            {"tid": tenant_id, "phone": sender, "alias": account_alias, "first": is_first_message},
        )
        session.commit()
        
        session_data = (
            session.execute(
                text(
                    "SELECT current_node_id, account_alias, is_bot_active FROM whatsapp_sessions "
                    "WHERE phone_number = :phone AND tenant_id = :tid AND account_alias = :alias"
                ),
                {"phone": sender, "tid": tenant_id, "alias": account_alias},
            )
            .mappings()
            .first()
        )


        if not session_data:
            logger.error(f"No se pudo recuperar la sesión para {sender} con alias {account_alias}")
            return

        current_node_id = session_data["current_node_id"]
        is_bot_active = session_data.get("is_bot_active", True)

        if not is_bot_active:
            logger.info(f"Bot desactivado para el usuario {sender} y alias {account_alias}. Ignorando mensaje.")
            return

        # 3. CARGAR CONFIGURACIÓN DEL BOT (Ahora con el alias correcto)
        settings = self._get_settings(session, tenant_id, account_alias)

        # SECTOR: Derivación (Si el bot está globalmente desactivado)
        if not settings.get("is_global_active", True):
            logger.info(
                f"Bot {account_alias} globalmente inactivo para {tenant_id}. Enviando mensaje de derivación."
            )
            self._send_immediate_response(
                session, tenant_id, sender, settings["handoff_message"], account_alias
            )
            return

        # 4. DETERMINAR RESPUESTA (Sectores vs Nodos)

        # SECTOR: Bienvenida (Si es primer mensaje o no hay nodo asignado)
        if is_first_message or not current_node_id:
            logger.info(
                f"Activando flujo de Bienvenida para {sender} en bot {account_alias} (FirstMsg: {is_first_message})"
            )
            welcome_msg = settings["welcome_message"]

            # Buscamos el nodo 'inicio' para dejar al usuario posicionado en el menú
            node = (
                session.execute(
                    text(
                        "SELECT id FROM bot_nodes WHERE name = 'inicio' AND tenant_id = :tid AND account_alias = :alias"
                    ),
                    {"tid": tenant_id, "alias": account_alias},
                )
                .mappings()
                .first()
            )

            # Respondemos con la bienvenida personalizada
            self._send_immediate_response(
                session, tenant_id, sender, welcome_msg, account_alias
            )

            if node:
                session.execute(
                    text(
                        "UPDATE whatsapp_sessions SET current_node_id = :nid WHERE phone_number = :phone AND tenant_id = :tid AND account_alias = :alias"
                    ),
                    {"nid": node["id"], "phone": sender, "tid": tenant_id, "alias": account_alias},
                )
                session.commit()
            return

        # SECTOR: Interacción (Nodos y Opciones)
        logger.info(f"Procesando interacción en nodo {current_node_id} para bot {account_alias}")
        option = (
            session.execute(
                text(
                    "SELECT next_node_id, action FROM bot_options "
                    "WHERE node_id = :nid AND label = :label AND tenant_id = :tid AND account_alias = :alias"
                ),
                {"nid": current_node_id, "label": text_message, "tid": tenant_id, "alias": account_alias},
            )
            .mappings()
            .first()
        )

        if option and option["next_node_id"]:
            node = (
                session.execute(
                    text(
                        "SELECT id, prompt FROM bot_nodes WHERE id = :nid AND tenant_id = :tid AND account_alias = :alias"
                    ),
                    {"nid": option["next_node_id"], "tid": tenant_id, "alias": account_alias},
                )
                .mappings()
                .first()
            )
            if node:
                self._send_immediate_response(
                    session, tenant_id, sender, node["prompt"], account_alias
                )
                session.execute(
                    text(
                        "UPDATE whatsapp_sessions SET current_node_id = :nid WHERE phone_number = :phone AND tenant_id = :tid AND account_alias = :alias"
                    ),
                    {"nid": node["id"], "phone": sender, "tid": tenant_id, "alias": account_alias},
                )
                session.commit()
                return

        # Fallback: Si no entiende la opción, repetimos el nodo actual
        node = (
            session.execute(
                text(
                    "SELECT id, prompt FROM bot_nodes WHERE id = :nid AND tenant_id = :tid AND account_alias = :alias"
                ),
                {"nid": current_node_id, "tid": tenant_id, "alias": account_alias},
            )
            .mappings()
            .first()
        )
        if node:
            self._send_immediate_response(
                session, tenant_id, sender, node["prompt"], account_alias
            )

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
