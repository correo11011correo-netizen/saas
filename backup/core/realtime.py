import asyncio
import logging
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger("OmniCore.Realtime")


class ConnectionManager:
    """
    Gestor de conexiones WebSocket para tiempo real.
    Maneja el routing de mensajes entre usuarios, bots y administradores.
    """

    def __init__(self):
        # {tenant_id: {user_id: WebSocket}}
        self.active_connections: dict[str, dict[str, WebSocket]] = {}
        # {user_id: Set[tenant_id]} - Para usuarios que saltan entre cuentas (Soporte)
        self.user_subscriptions: dict[str, set[str]] = {}

    async def connect(self, websocket: WebSocket, tenant_id: str, user_id: str):
        await websocket.accept()

        if tenant_id not in self.active_connections:
            self.active_connections[tenant_id] = {}

        self.active_connections[tenant_id][user_id] = websocket

        if user_id not in self.user_subscriptions:
            self.user_subscriptions[user_id] = set()
        self.user_subscriptions[user_id].add(tenant_id)

        logger.info(f"WebSocket connected: User {user_id} on Tenant {tenant_id}")

    def disconnect(self, tenant_id: str, user_id: str):
        if tenant_id in self.active_connections:
            self.active_connections[tenant_id].pop(user_id, None)
            if not self.active_connections[tenant_id]:
                del self.active_connections[tenant_id]

        if user_id in self.user_subscriptions:
            self.user_subscriptions[user_id].discard(tenant_id)
            if not self.user_subscriptions[user_id]:
                del self.user_subscriptions[user_id]

        logger.info(f"WebSocket disconnected: User {user_id} from Tenant {tenant_id}")

    async def send_personal_message(self, tenant_id: str, user_id: str, message: dict):
        """Envía un mensaje a un usuario específico en un tenant."""
        if tenant_id in self.active_connections and user_id in self.active_connections[tenant_id]:
            websocket = self.active_connections[tenant_id][user_id]
            await websocket.send_json(message)

    async def broadcast_to_tenant(self, tenant_id: str, message: dict):
        """Envía un mensaje a todos los usuarios conectados de un tenant."""
        if tenant_id in self.active_connections:
            for user_id, websocket in self.active_connections[tenant_id].items():
                await websocket.send_json(message)

    async def send_system_event(self, event_type: str, payload: Any):
        """
        Evento global para el Shell (ej: 'UI_UPDATE', 'BOT_STATUS_CHANGED').
        Se envía a todos los usuarios conectados independientemente del tenant.
        """
        all_messages = {
            "event": event_type,
            "payload": payload,
            "timestamp": asyncio.get_event_loop().time(),
        }

        for tenant_id, users in self.active_connections.items():
            for user_id, websocket in users.items():
                await websocket.send_json(all_messages)


# Singleton para uso en toda la API
realtime_manager = ConnectionManager()
