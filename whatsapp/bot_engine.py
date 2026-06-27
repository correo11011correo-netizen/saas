import logging
from typing import Any, Dict
from sqlalchemy import text
from sqlalchemy.orm import Session
from core.dispatcher import dispatcher
from core.context import TenantContext
import uuid
import json

logger = logging.getLogger("OmniCore.BotEngine")


class BotEngine:
    def _get_bot_profile_for_credential(self, session: Session, tenant_id: str, phone_number_id: str) -> str:
        """
        Busca el bot_profile_id asociado a la credencial del número de teléfono.
        """
        result = (
            session.execute(
                text(
                    """
                    SELECT ba.bot_profile_id 
                    FROM credentials c
                    JOIN bot_assignments ba ON c.id = ba.credential_id
                    WHERE c.tenant_id = :tid AND c.metadata->>'phone_number_id' = :phone_id
                    """
                ),
                {"tid": tenant_id, "phone_id": phone_number_id},
            )
            .mappings()
            .first()
        )
        return result["bot_profile_id"] if result else None

    def _get_settings(self, session: Session, tenant_id: str, bot_profile_id: str) -> Dict[str, Any]:
        """
        Obtiene la configuración del bot específico para un perfil.
        """
        settings = (
            session.execute(
                text("SELECT * FROM bot_settings WHERE tenant_id = :tid AND bot_profile_id = :bid"),
                {"tid": tenant_id, "bid": bot_profile_id},
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
        self, session: Session, tenant_id: str, sender: str, text_message: str, phone_number_id: str
    ):
        """
        Procesa el mensaje recibido basándose en perfiles de bots.
        """
        logger.info(f"BotEngine recibiendo mensaje de {sender} (PhoneID: {phone_number_id}): {text_message}")

        # 1. Identificar el Bot Perfil activo para esta credencial
        bot_profile_id = self._get_bot_profile_for_credential(session, tenant_id, phone_number_id)
        
        if not bot_profile_id:
            logger.error(f"No se encontró un bot asignado para el phone_number_id {phone_number_id}")
            return

        # 2. REGISTRAR MENSAJE ENTRANTE
        session.execute(
            text(
                "INSERT INTO whatsapp_conversations (phone_number, sender_type, message, message_type, tenant_id, bot_profile_id) "
                "VALUES (:phone, 'user', :msg, 'text', :tid, :bid)"
            ),
            {"phone": sender, "msg": text_message, "tid": tenant_id, "bid": bot_profile_id},
        )

        # 3. GESTIONAR SESIÓN
        # Verificamos si hay una sesión activa para este usuario en este tenant
        session_data = (
            session.execute(
                text(
                    "SELECT current_node_id, bot_profile_id, is_bot_active FROM whatsapp_sessions "
                    "WHERE phone_number = :phone AND tenant_id = :tid"
                ),
                {"phone": sender, "tid": tenant_id},
            )
            .mappings()
            .first()
        )

        is_first_message = False
        if not session_data:
            is_first_message = True
            session.execute(
                text(
                    """
                    INSERT INTO whatsapp_sessions (tenant_id, phone_number, bot_profile_id, is_bot_active, current_node_id)
                    VALUES (:tid, :phone, :bid, TRUE, NULL)
                    """
                ),
                {"tid": tenant_id, "phone": sender, "bid": bot_profile_id},
            )
            session.commit()
            # Recargar datos de sesión
            session_data = (
                session.execute(
                    text(
                        "SELECT current_node_id, bot_profile_id, is_bot_active FROM whatsapp_sessions "
                        "WHERE phone_number = :phone AND tenant_id = :tid"
                    ),
                    {"phone": sender, "tid": tenant_id},
                )
                .mappings()
                .first()
            )
        else:
            # Actualizar el perfil de bot si el número ha sido reasignado
            if session_data["bot_profile_id"] != bot_profile_id:
                session.execute(
                    text("UPDATE whatsapp_sessions SET bot_profile_id = :bid WHERE phone_number = :phone AND tenant_id = :tid"),
                    {"bid": bot_profile_id, "phone": sender, "tid": tenant_id}
                )
                session.commit()
                # Actualizar variable local
                session_data = session_data._asdict() 
                session_data["bot_profile_id"] = bot_profile_id

        current_node_id = session_data["current_node_id"]
        active_bot_profile_id = session_data["bot_profile_id"]
        is_bot_active = session_data.get("is_bot_active", True)

        if not is_bot_active:
            return

        settings = self._get_settings(session, tenant_id, active_bot_profile_id)

        if not settings.get("is_global_active", True):
            self._send_immediate_response(session, tenant_id, sender, settings["handoff_message"], active_bot_profile_id)
            return

        # --- LÓGICA DE INTERACCIÓN ---

        # Caso A: Primer mensaje -> Bienvenida + Nodo Inicio del Bot asignado
        if is_first_message:
            logger.info(f"Flujo de Bienvenida para {sender} con Bot {active_bot_profile_id}")

            node_inicio = (
                session.execute(
                    text("SELECT id, prompt FROM bot_nodes WHERE name = 'inicio' AND tenant_id = :tid AND bot_profile_id = :bid"),
                    {"tid": tenant_id, "bid": active_bot_profile_id},
                ).mappings().first()
            )

            msg_final = settings["welcome_message"]
            if node_inicio:
                msg_final += f"\\n\\n{node_inicio['prompt']}"

            self._send_immediate_response(session, tenant_id, sender, msg_final, active_bot_profile_id)

            if node_inicio:
                session.execute(
                    text("UPDATE whatsapp_sessions SET current_node_id = :nid WHERE phone_number = :phone AND tenant_id = :tid"),
                    {"nid": node_inicio["id"], "phone": sender, "tid": tenant_id},
                )
                session.commit()
            return

        # Caso B: Interacción con Menús (Nodos)
        if current_node_id:
            logger.info(f"Procesando opción '{text_message}' en nodo {current_node_id} (Bot: {active_bot_profile_id})")
            option = (
                session.execute(
                    text(
                        "SELECT next_node_id, action FROM bot_options "
                        "WHERE node_id = :nid AND (label = :label OR label = :label_num) AND tenant_id = :tid AND bot_profile_id = :bid"
                    ),
                    {"nid": current_node_id, "label": text_message, "label_num": text_message.strip(), "tid": tenant_id, "bid": active_bot_profile_id},
                ).mappings().first()
            )

            if option:
                # ACCIÓN: switch_bot -> Cambiar el perfil del bot en la sesión
                if option["action"] == "switch_bot":
                    # El next_node_id se usa aquí como el ID del BOT PROFILE destino
                    target_bot_id = option["next_node_id"]
                    logger.info(f"Cambiando bot a {target_bot_id} para {sender}")
                    
                    session.execute(
                        text("UPDATE whatsapp_sessions SET bot_profile_id = :bid, current_node_id = NULL WHERE phone_number = :phone AND tenant_id = :tid"),
                        {"bid": target_bot_id, "phone": sender, "tid": tenant_id}
                    )
                    session.commit()
                    
                    # Ahora procesamos el mensaje nuevamente pero con el nuevo perfil
                    # Para evitar recursividad infinita, llamamos a una versión simplificada o simplemente
                    # enviamos la bienvenida del nuevo bot.
                    new_settings = self._get_settings(session, tenant_id, target_bot_id)
                    node_inicio_nuevo = (
                        session.execute(
                            text("SELECT id, prompt FROM bot_nodes WHERE name = 'inicio' AND tenant_id = :tid AND bot_profile_id = :bid"),
                            {"tid": tenant_id, "bid": target_bot_id},
                        ).mappings().first()
                    )
                    
                    msg_switch = f"Cambiando al modo: {new_settings['bot_name']}... 🤖"
                    if node_inicio_nuevo:
                        msg_switch += f"\\n\\n{node_inicio_nuevo['prompt']}"
                        session.execute(
                            text("UPDATE whatsapp_sessions SET current_node_id = :nid WHERE phone_number = :phone AND tenant_id = :tid"),
                            {"nid": node_inicio_nuevo["id"], "phone": sender, "tid": tenant_id}
                        )
                        session.commit()
                    
                    self._send_immediate_response(session, tenant_id, sender, msg_switch, target_bot_id)
                    return

                # Si la opción tiene un nodo siguiente, navegamos
                if option["next_node_id"]:
                    node = (
                        session.execute(
                            text("SELECT id, prompt FROM bot_nodes WHERE id = :nid AND tenant_id = :tid AND bot_profile_id = :bid"),
                            {"nid": option["next_node_id"], "tid": tenant_id, "bid": active_bot_profile_id},
                        ).mappings().first()
                    )
                    if node:
                        self._send_immediate_response(session, tenant_id, sender, node["prompt"], active_bot_profile_id)
                        session.execute(
                            text("UPDATE whatsapp_sessions SET current_node_id = :nid WHERE phone_number = :phone AND tenant_id = :tid"),
                            {"nid": node["id"], "phone": sender, "tid": tenant_id},
                        )
                        session.commit()
                        return

                # ACCIÓN: search_products -> Búsqueda en el Bot de Stock
                if option["action"] == "search_products":
                    # En este caso, el mensaje actual es el trigger, pero queremos que el siguiente mensaje sea la búsqueda.
                    self._send_immediate_response(session, tenant_id, sender, "Por favor, escribe el nombre del producto que deseas buscar. 🔍", active_bot_profile_id)
                    # Marcamos la sesión para que el próximo mensaje se trate como búsqueda
                    session.execute(
                        text("UPDATE whatsapp_sessions SET current_node_id = 'SEARCH_MODE' WHERE phone_number = :phone AND tenant_id = :tid"),
                        {"phone": sender, "tid": tenant_id}
                    )
                    session.commit()
                    return

        # --- MODO BÚSQUEDA O FALLBACK ---

        # Si estamos en modo búsqueda
        if current_node_id == 'SEARCH_MODE':
            logger.info(f"Ejecutando búsqueda de productos para {sender}: {text_message}")
            products = (
                session.execute(
                    text("SELECT name, price, quantity FROM products WHERE tenant_id = :tid AND name ILIKE :query"),
                    {"tid": tenant_id, "query": f"%{text_message}%"},
                ).mappings().all()
            )

            if products:
                response_msg = "📦 *Productos encontrados:*\\n\\n"
                for p in products:
                    status = "✅ En Stock" if p['quantity'] > 0 else "❌ Agotado"
                    response_msg += f"• {p['name']} - ${p['price']} ({status})\\n"
                response_msg += "\\nPara volver al menú, escribe 'Menú'."
            else:
                response_msg = f"No encontré productos que coincidan con '{text_message}'. Intenta con otra palabra. 🔍"

            self._send_immediate_response(session, tenant_id, sender, response_msg, active_bot_profile_id)
            
            # Volvemos al nodo anterior o al inicio después de la búsqueda
            node_inicio = (
                session.execute(
                    text("SELECT id FROM bot_nodes WHERE name = 'inicio' AND tenant_id = :tid AND bot_profile_id = :bid"),
                    {"tid": tenant_id, "bid": active_bot_profile_id},
                ).mappings().first()
            )
            if node_inicio:
                session.execute(
                    text("UPDATE whatsapp_sessions SET current_node_id = :nid WHERE phone_number = :phone AND tenant_id = :tid"),
                    {"nid": node_inicio["id"], "phone": sender, "tid": tenant_id}
                )
                session.commit()
            return

        # Fallback: Repetir menú actual
        node = (
            session.execute(
                text("SELECT prompt FROM bot_nodes WHERE id = :nid AND tenant_id = :tid AND bot_profile_id = :bid"),
                {"nid": current_node_id, "tid": tenant_id, "bid": active_bot_profile_id},
            ).mappings().first()
        )
        if node:
            self._send_immediate_response(session, tenant_id, sender, node["prompt"], active_bot_profile_id)
        else:
            # Si no hay nodo, enviamos la bienvenida o un mensaje de error
            self._send_immediate_response(session, tenant_id, sender, "Lo siento, no entiendo esa opción. Intenta escribir 'Hola' para reiniciar.", active_bot_profile_id)

    def _send_immediate_response(
        self, session, tenant_id, sender, body, bot_profile_id: str
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
        # Importante: El dispatcher de whatsapp.send_text debe ser actualizado para usar bot_profile_id
        dispatcher.execute(
            "whatsapp.send_text",
            {"to": sender, "body": body, "bot_profile_id": bot_profile_id},
            context,
        )
