import logging
from typing import Any, Dict, List
from sqlalchemy import text
from sqlalchemy.orm import Session

from core.types import ServiceResponse
from core.decorators import command
from core.context import TenantContext

logger = logging.getLogger("OmniCore.WhatsappCommands")


class WhatsappCommandHandler:
    """
    Implementación de comandos de WhatsApp Multi-tenant.
    Utiliza SQL directo para garantizar la independencia de repositorios.
    """

    @command(
        name="bot.settings.get",
        description="Gets the global bot settings for the current tenant.",
        params_model={},
    )
    def get_settings(self, session: Session, context: TenantContext) -> ServiceResponse:
        try:
            result = (
                session.execute(
                    text("SELECT * FROM bot_settings WHERE tenant_id = :tid"),
                    {"tid": context.tenant_id},
                )
                .mappings()
                .all()
            )
            if not result:
                return ServiceResponse.error_res(
                    "Bot settings not found", "SETTINGS_NOT_FOUND"
                )

            return ServiceResponse.success_res(
                data=[dict(row) for row in result], message="Settings retrieved."
            )
        except Exception as e:
            return ServiceResponse.error_res(f"Error: {str(e)}", "GET_SETTINGS_ERROR")

    @command(
        name="bot.settings.update",
        description="Updates the global bot settings for a specific profile.",
        params_model={
            "bot_profile_id": "string",
            "bot_name": "string",
            "welcome_message": "string",
            "farewell_message": "string",
            "handoff_message": "string",
            "support_email": "string",
            "is_global_active": "boolean",
        },
    )
    def update_settings(
        self, session: Session, context: TenantContext, **params
    ) -> ServiceResponse:
        try:
            bot_profile_id = params.get("bot_profile_id")
            if not bot_profile_id:
                return ServiceResponse.error_res("bot_profile_id is required", "MISSING_ID")

            update_fields = []
            values = {"tid": context.tenant_id, "bid": bot_profile_id}

            for key in [
                "bot_name",
                "welcome_message",
                "farewell_message",
                "handoff_message",
                "support_email",
                "is_global_active",
            ]:
                if key in params:
                    update_fields.append(f"{key} = :{key}")
                    values[key] = params[key]

            if not update_fields:
                return ServiceResponse.error_res(
                    "No fields to update", "NO_FIELDS_ERROR"
                )

            query = f"UPDATE bot_settings SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP WHERE tenant_id = :tid AND bot_profile_id = :bid"
            session.execute(text(query), values)
            session.commit()

            return ServiceResponse.success_res(
                message="Bot settings updated successfully."
            )
        except Exception as e:
            session.rollback()
            return ServiceResponse.error_res(
                f"Error: {str(e)}", "UPDATE_SETTINGS_ERROR"
            )

    @command(
        name="whatsapp.toggle_bot",
        description="Toggles bot activity for a conversation.",
        params_model={"phone_number": "string", "is_active": "boolean"},
    )
    def toggle_bot(
        self,
        session: Session,
        context: TenantContext,
        phone_number: str,
        is_active: bool,
    ) -> ServiceResponse:
        try:
            logger.info(f"Toggling bot for {phone_number} to {is_active} (Tenant: {context.tenant_id})")
            
            # 1. Intentar actualizar la sesión existente
            res = session.execute(
                text(
                    "UPDATE whatsapp_sessions SET is_bot_active = :active WHERE phone_number = :phone AND tenant_id = :tid"
                ),
                {"active": is_active, "phone": phone_number, "tid": context.tenant_id},
            )
            
            # 2. Si no se actualizó ninguna fila, la sesión no existe. La creamos.
            if res.rowcount == 0:
                logger.info(f"No session found for {phone_number}, creating new session with state {is_active}")
                
                # Buscar un bot activo por defecto para asignar a la nueva sesión
                bot_default = session.execute(
                    text("SELECT id FROM bot_profiles WHERE tenant_id = :tid AND is_active = TRUE LIMIT 1"),
                    {"tid": context.tenant_id},
                ).mappings().first()
                
                bot_id = bot_default["id"] if bot_default else None
                
                session.execute(
                    text(
                        """
                        INSERT INTO whatsapp_sessions (tenant_id, phone_number, bot_profile_id, is_bot_active, current_node_id)
                        VALUES (:tid, :phone, :bid, :active, NULL)
                        """
                    ),
                    {"tid": context.tenant_id, "phone": phone_number, "bid": bot_id, "active": is_active},
                )
            
            session.commit()
            return ServiceResponse.success_res(message="Bot status updated.")
        except Exception as e:
            session.rollback()
            logger.error(f"Error toggling bot for {phone_number}: {str(e)}")
            return ServiceResponse.error_res(f"Error: {str(e)}", "TOGGLE_BOT_ERROR")

    @command(
        name="whatsapp.get_messages",
        description="Retrieves message history for a conversation.",
        params_model={"phone_number": "string"},
    )
    def get_messages(
        self, session: Session, context: TenantContext, phone_number: str
    ) -> ServiceResponse:
        try:
            result = (
                session.execute(
                    text(
                        "SELECT sender_type, message, message_type, created_at FROM whatsapp_conversations WHERE phone_number = :phone AND tenant_id = :tid ORDER BY created_at ASC"
                    ),
                    {"phone": phone_number, "tid": context.tenant_id},
                )
                .mappings()
                .all()
            )
            status_bot = session.execute(
                text(
                    "SELECT is_bot_active FROM whatsapp_sessions WHERE phone_number = :phone AND tenant_id = :tid LIMIT 1"
                ),
                {"phone": phone_number, "tid": context.tenant_id},
            ).scalar()

            return ServiceResponse.success_res(
                data={
                    "messages": [dict(row) for row in result],
                    "is_bot_active": status_bot if status_bot is not None else True,
                },
                message="Messages retrieved.",
            )
        except Exception as e:
            return ServiceResponse.error_res(f"Error: {str(e)}", "GET_MESSAGES_ERROR")

    @command(
        name="whatsapp.delete_conversation",
        description="Deletes all messages for a specific conversation and clears its session.",
        params_model={"phone_number": "string"},
    )
    def delete_conversation(
        self, session: Session, context: TenantContext, phone_number: str
    ) -> ServiceResponse:
        try:
            session.execute(
                text(
                    "DELETE FROM whatsapp_sessions WHERE phone_number = :phone AND tenant_id = :tid"
                ),
                {"phone": phone_number, "tid": context.tenant_id},
            )

            session.execute(
                text(
                    "DELETE FROM whatsapp_conversations WHERE phone_number = :phone AND tenant_id = :tid"
                ),
                {"phone": phone_number, "tid": context.tenant_id},
            )

            session.commit()
            return ServiceResponse.success_res(
                message="Conversation deleted successfully."
            )
        except Exception as e:
            session.rollback()
            return ServiceResponse.error_res(
                f"Error deleting conversation: {str(e)}", "DELETE_CONV_ERROR"
            )

    @command(
        name="bot.node.save",
        description="Saves or updates a bot node.",
        params_model={"name": "string", "prompt": "string", "bot_profile_id": "string"},
    )
    def save_node(
        self, session: Session, context: TenantContext, name: str, prompt: str, bot_profile_id: str
    ) -> ServiceResponse:
        try:
            session.execute(
                text(
                    """
                    INSERT INTO bot_nodes (name, prompt, tenant_id, bot_profile_id)
                    VALUES (:name, :prompt, :tid, :bid)
                    ON CONFLICT (tenant_id, bot_profile_id, name) DO UPDATE
                    SET prompt = EXCLUDED.prompt
                    """
                ),
                {"name": name, "prompt": prompt, "tid": context.tenant_id, "bid": bot_profile_id},
            )
            session.commit()
            return ServiceResponse.success_res(message="Node saved successfully.")
        except Exception as e:
            session.rollback()
            return ServiceResponse.error_res(f"Error: {str(e)}", "SAVE_NODE_ERROR")

    @command(
        name="whatsapp.list_conversations",
        description="Lists recent WhatsApp conversations.",
        params_model={},
    )
    def list_conversations(
        self, session: Session, context: TenantContext
    ) -> ServiceResponse:
        try:
            result = (
                session.execute(
                    text(
                        "SELECT DISTINCT ON (phone_number) phone_number, message AS last_message FROM whatsapp_conversations WHERE tenant_id = :tid ORDER BY phone_number, created_at DESC"
                    ),
                    {"tid": context.tenant_id},
                )
                .mappings()
                .all()
            )
            return ServiceResponse.success_res(
                data=[dict(row) for row in result], message="Conversations listed."
            )
        except Exception as e:
            return ServiceResponse.error_res(f"Error: {str(e)}", "LIST_CONV_ERROR")

    @command(
        name="bot.node.list",
        description="Lists all bot nodes for the current tenant.",
        params_model={},
    )
    def list_nodes(self, session: Session, context: TenantContext) -> ServiceResponse:
        try:
            result = (
                session.execute(
                    text(
                        "SELECT id, name, prompt, bot_profile_id FROM bot_nodes WHERE tenant_id = :tid"
                    ),
                    {"tid": context.tenant_id},
                )
                .mappings()
                .all()
            )
            return ServiceResponse.success_res(
                data=[dict(row) for row in result], message="Nodes listed successfully."
            )
        except Exception as e:
            return ServiceResponse.error_res(f"Error: {str(e)}", "LIST_NODES_ERROR")

    @command(
        name="bot.option.add",
        description="Adds an option to a bot node.",
        params_model={
            "node_id": "string",
            "label": "string",
            "next_node_id": "string",
            "action": "string",
            "bot_profile_id": "string",
        },
    )
    def add_option(
        self,
        session: Session,
        context: TenantContext,
        node_id: str,
        label: str,
        bot_profile_id: str,
        next_node_id: str = None,
        action: str = None,
    ) -> ServiceResponse:
        try:
            session.execute(
                text(
                    """
                    INSERT INTO bot_options (node_id, label, next_node_id, action, tenant_id, bot_profile_id)
                    VALUES (:nid, :label, :next, :action, :tid, :bid)
                    """
                ),
                {
                    "nid": node_id,
                    "label": label,
                    "next": next_node_id,
                    "action": action,
                    "tid": context.tenant_id,
                    "bid": bot_profile_id,
                },
            )
            session.commit()
            return ServiceResponse.success_res(message="Option added successfully.")
        except Exception as e:
            session.rollback()
            return ServiceResponse.error_res(f"Error: {str(e)}", "ADD_OPTION_ERROR")

    @command(
        name="bot.option.list",
        description="Lists all options for a specific bot node.",
        params_model={"node_id": "string"},
    )
    def list_options(
        self, session: Session, context: TenantContext, node_id: str
    ) -> ServiceResponse:
        try:
            result = (
                session.execute(
                    text(
                        "SELECT id, label, next_node_id, action FROM bot_options WHERE node_id = :nid AND tenant_id = :tid"
                    ),
                    {"nid": node_id, "tid": context.tenant_id},
                )
                .mappings()
                .all()
            )
            return ServiceResponse.success_res(
                data=[dict(row) for row in result],
                message="Options listed successfully.",
            )
        except Exception as e:
            session.rollback()
            return ServiceResponse.error_res(f"Error: {str(e)}", "LIST_OPTIONS_ERROR")

    @command(
        name="whatsapp.send_text",
        description="Sends a plain text message via WhatsApp Business API.",
        params_model={
            "to": "string",
            "body": "string",
            "bot_profile_id": "string",
            "sender_type": "string",
        },
    )
    def send_text(
        self,
        session: Session,
        context: TenantContext,
        to: str,
        body: str,
        bot_profile_id: str = None,
        sender_type: str = "bot",
    ) -> ServiceResponse:
        try:
            # 0. Si no se proporciona bot_profile_id, intentar obtenerlo de la sesión
            if not bot_profile_id:
                session_data = session.execute(
                    text("SELECT bot_profile_id FROM whatsapp_sessions WHERE phone_number = :phone AND tenant_id = :tid LIMIT 1"),
                    {"phone": to, "tid": context.tenant_id}
                ).mappings().first()
                if session_data:
                    bot_profile_id = session_data['bot_profile_id']
            
            if not bot_profile_id:
                return ServiceResponse.error_res("No bot profile associated with this session/request", "BOT_PROFILE_MISSING")

            # Buscamos la credencial asociada al bot_profile_id actual para este tenant
            cred_info = (
                session.execute(
                    text(
                        """
                        SELECT c.api_key, c.metadata 
                        FROM credentials c
                        JOIN bot_assignments ba ON c.id = ba.credential_id
                        WHERE ba.bot_profile_id = :bid AND c.tenant_id = :tid
                        LIMIT 1
                        """
                    ),
                    {"bid": bot_profile_id, "tid": context.tenant_id},
                )
                .mappings()
                .first()
            )

            if not cred_info:
                logger.info(f"No specific credential for bot profile {bot_profile_id}, searching fallback for tenant {context.tenant_id}")
                cred_info = (
                    session.execute(
                        text("SELECT api_key, metadata FROM credentials WHERE service_name = 'whatsapp' AND tenant_id = :tid LIMIT 1"),
                        {"tid": context.tenant_id},
                    )
                    .mappings()
                    .first()
                )

            if not cred_info:
                logger.error(f"No WhatsApp credentials found for tenant {context.tenant_id}")
                return ServiceResponse.error_res(
                    "WhatsApp credentials not found", "WHATSAPP_CREDS_ERROR"
                )

            import json
            if isinstance(cred_info["metadata"], dict):
                meta = cred_info["metadata"]
            else:
                meta = json.loads(cred_info["metadata"])
            
            phone_number_id = meta.get("phone_number_id")

            if not phone_number_id:
                return ServiceResponse.error_res(
                    "Phone Number ID not found in credentials metadata", "WHATSAPP_PHONE_ID_ERROR"
                )

            import requests
            url = f"https://graph.facebook.com/v19.0/{phone_number_id}/messages"
            headers = {
                "Authorization": f"Bearer {cred_info['api_key']}",
                "Content-Type": "application/json",
            }
            payload = {
                "messaging_product": "whatsapp",
                "to": to,
                "type": "text",
                "text": {"body": body},
            }

            response = requests.post(url, headers=headers, json=payload)
            if not response.ok:
                logger.error(f"Meta API Error: {response.text}")
                return ServiceResponse.error_res(
                    "Failed to send message via Meta", "META_API_ERROR"
                )

            # 3. Log interaction
            session.execute(
                text(
                    "INSERT INTO whatsapp_conversations (phone_number, sender_type, message, message_type, tenant_id, bot_profile_id) VALUES (:to, :stype, :body, 'text', :tid, :bid)"
                ),
                {
                    "to": to,
                    "stype": sender_type,
                    "body": body,
                    "tid": context.tenant_id,
                    "bid": bot_profile_id,
                },
            )

            session.commit()
            return ServiceResponse.success_res(
                data={"to": to, "status": "sent"}, message="Message sent successfully."
            )
        except Exception as e:
            session.rollback()
            return ServiceResponse.error_res(
                f"Delivery failed: {str(e)}", "DELIVERY_ERROR"
            )

    @command(
        name="whatsapp.list_credentials",
        description="Lists all WhatsApp credentials and their current bot assignments.",
        params_model={},
    )
    def list_credentials(self, session: Session, context: TenantContext) -> ServiceResponse:
        try:
            result = (
                session.execute(
                    text(
                        """
                        SELECT c.id as credential_id, c.account_alias, c.metadata, ba.bot_profile_id
                        FROM credentials c
                        LEFT JOIN bot_assignments ba ON c.id = ba.credential_id
                        WHERE c.service_name = 'whatsapp' AND c.tenant_id = :tid
                        """
                    ),
                    {"tid": context.tenant_id},
                )
                .mappings()
                .all()
            )
            return ServiceResponse.success_res(
                data=[dict(row) for row in result], message="Credentials listed successfully."
            )
        except Exception as e:
            return ServiceResponse.error_res(f"Error listing credentials: {str(e)}", "LIST_CREDS_ERROR")

    @command(
        name="bot.navigate",
        description="Handles navigation between menus for the current tenant.",
        params_model={"sender": "string", "menu_name": "string"},
    )
    def bot_navigate(
        self, session: Session, context: TenantContext, sender: str, menu_name: str
    ) -> ServiceResponse:
        try:
            # Update current menu
            session.execute(
                text(
                    "UPDATE whatsapp_conversations SET current_menu = :menu WHERE phone_number = :sender AND tenant_id = :tid"
                ),
                {"menu": menu_name, "sender": sender, "tid": context.tenant_id},
            )

            # Get menu details
            result = (
                session.execute(
                    text(
                        "SELECT prompt, options FROM whatsapp_menus WHERE menu_name = :menu AND tenant_id = :tid"
                    ),
                    {"menu": menu_name, "tid": context.tenant_id},
                )
                .mappings()
                .first()
            )

            if not result:
                return ServiceResponse.error_res(
                    f"Menu {menu_name} not found", "MENU_NOT_FOUND"
                )

            import json
            options = result["options"]
            if isinstance(options, str):
                options = json.loads(options)

            options_list = [
                f"{i+1}. {opt.get('label', 'Sin etiqueta')}"
                for i, opt in enumerate(options)
            ]
            full_text = f"{result['prompt']}\n\n{chr(10).join(options_list)}"

            session.commit()
            return ServiceResponse.success_res(message=full_text)
        except Exception as e:
            session.rollback()
            return ServiceResponse.error_res(f"Navigation error: {str(e)}", "NAV_ERROR")



class BotManagerCommandHandler:
    """
    Gestión de perfiles de bots especializados.
    """
    @command(
        name="bot.create",
        description="Creates a specialized bot 'employee' with specific functions and a dynamic menu.",
        params_model={"name": "string", "functions": "list"},
    )
    def create_bot(
        self, session: Session, context: TenantContext, name: str, functions: list[str] = None
    ) -> ServiceResponse:
        try:
            if functions is None:
                functions = []

            # 1. Create the Bot Profile
            res = session.execute(
                text(
                    "INSERT INTO bot_profiles (tenant_id, name, capabilities) VALUES (:tid, :name, :caps) RETURNING id"
                ),
                {"tid": context.tenant_id, "name": name, "caps": json.dumps({"functions": functions})},
            )
            bot_id = res.scalar()

            # 2. Create the Root Node
            node_res = session.execute(
                text(
                    """
                    INSERT INTO bot_nodes (name, prompt, tenant_id, bot_profile_id)
                    VALUES ('root', :prompt, :tid, :bid)
                    RETURNING id
                    """
                ),
                {
                    "prompt": f"Bienvenido a {name}. 🤖\\n\\nSeleccione una opción del menú para comenzar. 👇",
                    "tid": context.tenant_id,
                    "bid": bot_id,
                },
            )
            root_node_id = node_res.scalar()

            # 3. Link Root Node as start_node_id in capabilities
            session.execute(
                text(
                    "UPDATE bot_profiles SET capabilities = jsonb_set(capabilities, '{start_node_id}', :sid, true) WHERE id = :bid"
                ),
                {"sid": f'"{root_node_id}"', "bid": bot_id},
            )

            # 4. Dynamically Generate Menu Options based on functions
            FUNCTION_MAP = {
                "manage_stock": {"label": "📦 Consultar Stock", "action": "search_products"},
                "process_sales": {"label": "🛒 Realizar Venta", "action": "process_sale"},
                "generate_payments": {"label": "💳 Generar Cobro", "action": "generate_payment"},
                "customer_support": {"label": "🎧 Soporte y Ayuda", "action": "send_support_info"},
                "bot_orchestration": {"label": "🤖 Cambiar de Bot", "action": "switch_bot"},
            }

            for func in functions:
                if func in FUNCTION_MAP:
                    session.execute(
                        text(
                            """
                            INSERT INTO bot_options (node_id, label, action, tenant_id, bot_profile_id)
                            VALUES (:nid, :label, :action, :tid, :bid)
                            """
                        ),
                        {
                            "nid": root_node_id,
                            "label": FUNCTION_MAP[func]["label"],
                            "action": FUNCTION_MAP[func]["action"],
                            "tid": context.tenant_id,
                            "bid": bot_id,
                        },
                    )

            # 5. Initialize Default Settings
            session.execute(
                text(
                    """
                    INSERT INTO bot_settings (tenant_id, bot_profile_id, bot_name, welcome_message, farewell_message, handoff_message, support_email, is_global_active)
                    VALUES (:tid, :bid, :name, :welcome, :farewell, :handoff, :email, TRUE)
                    """
                ),
                {
                    "tid": context.tenant_id,
                    "bid": bot_id,
                    "name": name,
                    "welcome": f"¡Hola! Bienvenido a {name}. 🤖 ¿En qué puedo ayudarte hoy?",
                    "farewell": "Gracias por contactarnos. ¡Que tengas un gran día! 👋",
                    "handoff": "He desactivado el bot. Un agente humano se pondrá en contacto contigo en breve. 👨‍💻",
                    "email": "soporte@negocio.com",
                },
            )

            session.commit()
            return ServiceResponse.success_res(message=f"Bot employee '{name}' created with {len(functions)} functions.")
        except Exception as e:
            session.rollback()
            return ServiceResponse.error_res(f"Error creating bot employee: {str(e)}", "BOT_CREATE_ERROR")

    @command(
        name="bot.assign",
        description="Assigns a credential to a bot profile.",
        params_model={"credential_id": "string", "bot_profile_id": "string"},
    )
    def assign_bot(
        self, session: Session, context: TenantContext, credential_id: str, bot_profile_id: str
    ) -> ServiceResponse:
        try:
            logger.info(f"Assigning bot {bot_profile_id} to credential {credential_id} (Tenant: {context.tenant_id})")
            session.execute(
                text(
                    """
                    INSERT INTO bot_assignments (tenant_id, credential_id, bot_profile_id)
                    VALUES (:tid, :cid, :bid)
                    ON CONFLICT (tenant_id, credential_id) DO UPDATE
                    SET bot_profile_id = EXCLUDED.bot_profile_id
                    """
                ),
                {"tid": context.tenant_id, "cid": credential_id, "bid": bot_profile_id},
            )
            session.commit()
            return ServiceResponse.success_res(message="Bot assigned to credential successfully.")
        except Exception as e:
            session.rollback()
            logger.error(f"Error assigning bot {bot_profile_id} to {credential_id}: {str(e)}")
            return ServiceResponse.error_res(f"Error assigning bot: {str(e)}", "BOT_ASSIGN_ERROR")

    @command(
        name="bot.list",
        description="Lists all bot profiles for the tenant.",
        params_model={},
    )
    def list_bots(self, session: Session, context: TenantContext) -> ServiceResponse:
        try:
            result = session.execute(
                text("SELECT id, name, capabilities, is_active FROM bot_profiles WHERE tenant_id = :tid"),
                {"tid": context.tenant_id}
            ).mappings().all()
            return ServiceResponse.success_res(data=[dict(row) for row in result], message="Bot profiles listed.")
        except Exception as e:
            return ServiceResponse.error_res(f"Error listing bots: {str(e)}", "BOT_LIST_ERROR")

    @command(
        name="bot.update_capabilities",
        description="Updates bot capabilities (permissions).",
        params_model={"bot_profile_id": "string", "capabilities": "dict"},
    )
    def update_capabilities(
        self, session: Session, context: TenantContext, bot_profile_id: str, capabilities: Dict[str, bool]
    ) -> ServiceResponse:
        try:
            import json
            session.execute(
                text(
                    "UPDATE bot_profiles SET capabilities = :caps WHERE tenant_id = :tid AND id = :bid"
                ),
                {"caps": json.dumps(capabilities), "tid": context.tenant_id, "bid": bot_profile_id},
            )
            session.commit()
            return ServiceResponse.success_res(message="Bot capabilities updated.")
        except Exception as e:
            session.rollback()
            return ServiceResponse.error_res(f"Error updating capabilities: {str(e)}", "BOT_UPDATE_ERROR")

bot_manager_commands = BotManagerCommandHandler()
whatsapp_commands = WhatsappCommandHandler()
