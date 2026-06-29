from typing import Any

from sqlalchemy.orm import Session

from db_engine.repositories.base_repo import BaseRepository
from whatsapp.models import BotNode, BotProfile, BotSettings


class BotRepository(BaseRepository):
    """
    Manejo del Grafo de Conversación y Perfiles de Bot.
    """

    def __init__(self, session: Session):
        super().__init__(BotProfile, session)

    def get_full_bot_config(self, bot_profile_id: Any):
        """Obtiene el perfil, sus ajustes y la estructura de nodos."""
        profile = self.get_by_id(bot_profile_id)
        if not profile:
            return None

        settings = (
            self.session.query(BotSettings)
            .filter(BotSettings.bot_profile_id == bot_profile_id)
            .first()
        )

        nodes = self.session.query(BotNode).filter(BotNode.bot_profile_id == bot_profile_id).all()

        return {"profile": profile, "settings": settings, "nodes": nodes}

    def update_bot_settings(self, bot_profile_id: Any, settings_data: dict[str, Any]):
        """Actualiza los ajustes del bot."""
        settings = (
            self.session.query(BotSettings)
            .filter(BotSettings.bot_profile_id == bot_profile_id)
            .first()
        )

        if not settings:
            settings = BotSettings(bot_profile_id=bot_profile_id)
            self.session.add(settings)

        for key, value in settings_data.items():
            if hasattr(settings, key):
                setattr(settings, key, value)

        self.session.flush()
        return settings
