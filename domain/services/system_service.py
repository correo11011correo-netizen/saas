from typing import Any, List, Optional, Dict
from uuid import UUID, uuid4
from motor.application.state import state
from motor.infrastructure.providers.base import BaseProvider

class SystemService:
    """
    Servicio de Sistema: Auditoría, Gestión de Usuarios Globales y Logs.
    Sustituye a SystemCommandHandler.
    """

    def __init__(self):
        self.state = state

    def _get_provider(self, name: str) -> BaseProvider:
        provider = self.state.get_provider(name)
        if not provider:
            raise Exception(f"Provider '{name}' not connected.")
        return provider

    def get_audit_logs(self, tenant_id: Optional[UUID], command: Optional[str] = None, limit: int = 50, offset: int = 0):
        audit_provider = self._get_provider("audit")
        return audit_provider.list(
            filters={"tenant_id": tenant_id, "command": command},
            limit=limit,
            offset=offset
        )

    def create_system_user(self, email: str, password: str, role: str, tenant_id: Optional[UUID] = None):
        user_provider = self._get_provider("users")
        
        # Lógica de hash de password (negocio)
        import hashlib
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        user = User(
            email=email,
            role=role,
            tenant_id=tenant_id,
            password_hash=password_hash
        )
        return user_provider.save(user)

# Singleton instance
system_service = SystemService()
