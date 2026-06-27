import logging
from typing import Any, Dict
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
                .first()
            )
            if not result:
                return ServiceResponse.error_res(
                    "Bot settings not found", "SETTINGS_NOT_FOUND"
                )

            return ServiceResponse.success_res(
                data=dict(result), message="Settings retrieved."
            )
        except Exception as e:
            return ServiceResponse.error_res(f"Error: {str(e)}", "GET_SETTINGS_ERROR")

    @command(
        name="bot.settings.update",
        description="Updates the global bot settings.",
        params_model={
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
            # Only update fields that are provided
            update_fields = []
            values = {"tid": context.tenant_id}

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

            query = f"UPDATE bot_settings SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP WHERE tenant_id = :tid"
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
            session.execute(
                text(
                    "UPDATE whatsapp_sessions SET is_bot_active = :active WHERE phone_number = :phone AND tenant_id = :tid"
                ),
                {"active": is_active, "phone": phone_number, "tid": context.tenant_id},
            )
            session.commit()
            return ServiceResponse.success_res(message="Bot status updated.")
        except Exception as e:
            session.rollback()
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
            # Obtenemos el estado del bot desde whatsapp_sessions (fuente de verdad actual)
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
            # 1. Clear session state first
            session.execute(
                text(
                    "DELETE FROM whatsapp_sessions WHERE phone_number = :phone AND tenant_id = :tid"
                ),
                {"phone": phone_number, "tid": context.tenant_id},
            )

            # 2. Delete messages from conversations log
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
        params_model={"name": "string", "prompt": "string", "account_alias": "string"},
    )
    def save_node(
        self, session: Session, context: TenantContext, name: str, prompt: str, account_alias: str = "Principal"
    ) -> ServiceResponse:
        try:
            session.execute(
                text(
                    """
                    INSERT INTO bot_nodes (name, prompt, tenant_id, account_alias)
                    VALUES (:name, :prompt, :tid, :alias)
                    ON CONFLICT (tenant_id, account_alias, name) DO UPDATE
                    SET prompt = EXCLUDED.prompt
                    """
                ),
                {"name": name, "prompt": prompt, "tid": context.tenant_id, "alias": account_alias},
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
                        "SELECT id, name, prompt FROM bot_nodes WHERE tenant_id = :tid"
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
        },
    )
    def add_option(
        self,
        session: Session,
        context: TenantContext,
        node_id: str,
        label: str,
        next_node_id: str = None,
        action: str = None,
    ) -> ServiceResponse:
        try:
            session.execute(
                text(
                    """
                    INSERT INTO bot_options (node_id, label, next_node_id, action, tenant_id)
                    VALUES (:nid, :label, :next, :action, :tid)
                    """
                ),
                {
                    "nid": node_id,
                    "label": label,
                    "next": next_node_id,
                    "action": action,
                    "tid": context.tenant_id,
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
            return ServiceResponse.error_res(f"Error: {str(e)}", "LIST_OPTIONS_ERROR")

    @command(
        name="whatsapp.send_text",
        description="Sends a plain text message via WhatsApp Business API.",
        params_model={
            "to": "string",
            "body": "string",
            "sender_type": "string",
            "account_alias": "string",
        },
    )
    def send_text(
        self,
        session: Session,
        context: TenantContext,
        to: str,
        body: str,
        account_alias: str = None,
        sender_type: str = "bot",
    ) -> ServiceResponse:
        try:
            # 0. Si no se proporciona alias, obtener el alias activo de la sesión
            if not account_alias:
                session_data = session.execute(
                    text("SELECT account_alias FROM whatsapp_sessions WHERE phone_number = :phone AND tenant_id = :tid LIMIT 1"),
                    {"phone": to, "tid": context.tenant_id}
                ).mappings().first()
                if session_data:
                    account_alias = session_data['account_alias']
            
            # Fallback a 'bot' si aun no hay alias
            if not account_alias:
                account_alias = 'bot'

            logger.info(f"Intentando enviar mensaje a {to} usando alias {account_alias}")
            # 1. Fetch credentials
            cred = (
                session.execute(
                    text(
                        "SELECT api_key, metadata FROM credentials WHERE service_name = 'whatsapp' AND account_alias = :alias AND tenant_id = :tid"
                    ),
                    {"alias": account_alias, "tid": context.tenant_id},
                )
                .mappings()
                .first()
            )

            if not cred:
                # Intento fallback a 'bot' si el alias original falló
                if account_alias != 'bot':
                    logger.warning(f"No se encontraron credenciales con alias {account_alias}, intentando con 'bot'")
                    cred = session.execute(
                        text("SELECT api_key, metadata FROM credentials WHERE service_name = 'whatsapp' AND account_alias = 'bot' AND tenant_id = :tid"),
                        {"tid": context.tenant_id}
                    ).mappings().first()
                
                if not cred:
                    logger.error(f"No se encontraron credenciales de WhatsApp para tenant {context.tenant_id} y alias {account_alias}")
                    return ServiceResponse.error_res(
                        "WhatsApp credentials not found", "WHATSAPP_CREDS_ERROR"
                    )
            
            logger.info(f"Credenciales encontradas. api_key (parcial): {cred['api_key'][:5]}..., metadata: {cred['metadata']}")

            import json

            # CORRECCIÓN: Verificar si metadata ya es un dict
            if isinstance(cred["metadata"], dict):
                meta = cred["metadata"]
            else:
                meta = json.loads(cred["metadata"])
            
            phone_number_id = meta.get("phone_number_id")

            if not phone_number_id:
                logger.error(f"phone_number_id no encontrado en el metadata de las credenciales para alias {account_alias}")
                return ServiceResponse.error_res(
                    "Phone Number ID not found in WhatsApp credentials metadata", "WHATSAPP_PHONE_ID_ERROR"
                )

            logger.info(f"phone_number_id: {phone_number_id}")

            # 2. Call Meta API
            import requests

            url = f"https://graph.facebook.com/v19.0/{phone_number_id}/messages"
            headers = {
                "Authorization": f"Bearer {cred['api_key']}",
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
                    "INSERT INTO whatsapp_conversations (phone_number, sender_type, message, message_type, tenant_id, account_alias) VALUES (:to, :stype, :body, 'text', :tid, :alias)"
                ),
                {
                    "to": to,
                    "stype": sender_type,
                    "body": body,
                    "tid": context.tenant_id,
                    "alias": account_alias,
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
        description="Creates a new specialized bot profile.",
        params_model={"name": "string", "account_alias": "string"},
    )
    def create_bot(
        self, session: Session, context: TenantContext, name: str, account_alias: str
    ) -> ServiceResponse:
        try:
            session.execute(
                text(
                    "INSERT INTO bot_profiles (tenant_id, name, account_alias) VALUES (:tid, :name, :alias)"
                ),
                {"tid": context.tenant_id, "name": name, "alias": account_alias},
            )
            session.commit()
            return ServiceResponse.success_res(message="Bot profile created successfully.")
        except Exception as e:
            session.rollback()
            return ServiceResponse.error_res(f"Error creating bot: {str(e)}", "BOT_CREATE_ERROR")

    @command(
        name="bot.list",
        description="Lists all bot profiles for the tenant.",
        params_model={},
    )
    def list_bots(self, session: Session, context: TenantContext) -> ServiceResponse:
        try:
            result = session.execute(
                text("SELECT id, name, account_alias, capabilities, is_active FROM bot_profiles WHERE tenant_id = :tid"),
                {"tid": context.tenant_id}
            ).mappings().all()
            return ServiceResponse.success_res(data=[dict(row) for row in result], message="Bot profiles listed.")
        except Exception as e:
            return ServiceResponse.error_res(f"Error listing bots: {str(e)}", "BOT_LIST_ERROR")

    @command(
        name="bot.update_capabilities",
        description="Updates bot capabilities (permissions).",
        params_model={"account_alias": "string", "capabilities": "dict"},
    )
    def update_capabilities(
        self, session: Session, context: TenantContext, account_alias: str, capabilities: Dict[str, bool]
    ) -> ServiceResponse:
        try:
            import json
            session.execute(
                text(
                    "UPDATE bot_profiles SET capabilities = :caps WHERE tenant_id = :tid AND account_alias = :alias"
                ),
                {"caps": json.dumps(capabilities), "tid": context.tenant_id, "alias": account_alias},
            )
            session.commit()
            return ServiceResponse.success_res(message="Bot capabilities updated.")
        except Exception as e:
            session.rollback()
            return ServiceResponse.error_res(f"Error updating capabilities: {str(e)}", "BOT_UPDATE_ERROR")

bot_manager_commands = BotManagerCommandHandler()
whatsapp_commands = WhatsappCommandHandler()
