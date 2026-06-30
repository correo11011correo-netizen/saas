from typing import Any, List, Optional, Dict
from uuid import UUID, uuid4
from motor.application.state import state
from motor.domain.entities import BotConfig, User
from motor.infrastructure.providers.base import BaseProvider

class BotService:
    """
    Servicio de Bots: Orquestación de flujos, configuración y mensajería.
    Sustituye a WhatsappCommandHandler y BotManagerCommandHandler.
    """

    def __init__(self):
        self.state = state

    def _get_provider(self, name: str) -> BaseProvider:
        provider = self.state.get_provider(name)
        if not provider:
            raise Exception(f"Provider '{name}' not connected.")
        return provider

    def update_bot_settings(self, bot_profile_id: UUID, tenant_id: UUID, settings: Dict[str, Any]) -> BotConfig:
        bot_provider = self._get_provider("bots")
        bot = bot_provider.get(bot_profile_id)
        if not bot:
            raise ValueError("Bot profile not found")
        
        bot.settings.update(settings)
        return bot_provider.save(bot)

    def toggle_bot_activity(self, phone: str, tenant_id: UUID, is_active: bool):
        session_provider = self._get_provider("bot_sessions")
        session = session_provider.get(phone)
        
        if session:
            session.is_bot_active = is_active
            session_provider.save(session)
        else:
            # Lógica de creación de sesión por defecto
            bot_provider = self._get_provider("bots")
            default_bot = bot_provider.list({"tenant_id": tenant_id, "is_active": True})
            bot_id = default_bot[0].id if default_bot else None
            
            # Crear nueva sesión (asumiendo entidad WhatsappSession)
            from motor.domain.entities import BotSession
            new_session = BotSession(
                phone=phone,
                tenant_id=tenant_id,
                is_bot_active=is_active,
                bot_profile_id=bot_id
            )
            session_provider.save(new_session)

    def send_message(self, to: str, body: str, tenant_id: UUID, bot_profile_id: Optional[UUID] = None):
        """
        Orquestación de envío: Resuelve credenciales y usa el puerto de mensajería.
        """
        messaging_provider = self._get_provider("messaging")
        cred_provider = self._get_provider("credentials")
        
        # Resolver bot_profile_id si no viene
        if not bot_profile_id:
            session_provider = self._get_provider("bot_sessions")
            session = session_provider.get(to)
            if not session:
                raise ValueError("No active session for this phone")
            bot_profile_id = session.bot_profile_id

        # Resolver credenciales
        cred = cred_provider.get_by_bot_id(bot_profile_id, tenant_id)
        if not cred:
            raise Exception("No credentials found for this bot profile")

        # Enviar vía puerto externo (Abstracto)
        return messaging_provider.send_text(
            to=to,
            body=body,
            api_key=cred.api_key,
            phone_id=cred.phone_id
        )

    def save_bot_node(self, name: str, prompt: str, bot_profile_id: UUID, tenant_id: UUID):
        node_provider = self._get_provider("bot_nodes")
        # Lógica de Upsert
        node = node_provider.get_by_name(name, bot_profile_id)
        if node:
            node.prompt = prompt
        else:
            from motor.domain.entities import BotNode
            node = BotNode(name=name, prompt=prompt, bot_profile_id=bot_profile_id, tenant_id=tenant_id)
        
        return node_provider.save(node)

# Singleton instance
bot_service = BotService()
