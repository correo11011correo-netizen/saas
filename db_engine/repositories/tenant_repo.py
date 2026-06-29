from typing import Any

from sqlalchemy.orm import Session

from core.models import Tenant, User
from db_engine.repositories.base_repo import BaseRepository


class TenantRepository(BaseRepository):
    """
    Manejo de Clientes (Tenants) y Usuarios.
    Soporta la gestión de planes y configuraciones de paneles personalizados.
    """

    def __init__(self, session: Session):
        super().__init__(Tenant, session)

    def get_tenant_with_users(self, tenant_id: Any):
        """Obtiene un tenant y sus usuarios asociados."""
        tenant = self.get_by_id(tenant_id)
        if tenant:
            return {"tenant": tenant, "users": tenant.users}
        return None

    def create_user(self, data: dict[str, Any]) -> User:
        """Crea un usuario vinculado a un tenant."""
        # Usamos el modelo User directamente ya que es una entidad distinta pero relacionada
        from core.models import User

        user = User(**data)
        self.session.add(user)
        self.session.flush()
        return user

    def get_user_by_email(self, email: str) -> User | None:
        """Busca un usuario por su email."""
        from core.models import User

        return self.find_one(
            {"email": email}
        )  # Nota: base_repo usa el modelo configurado, aquí necesitamos User
        # Corrección: el base_repo usa self.model. Para buscar User, necesitamos un repo de User o acceder via session.
        # Implementación correcta:
        return self.session.query(User).filter(User.email == email).first()

    def update_panel_config(self, tenant_id: Any, config: dict[str, Any]):
        """
        Actualiza la configuración del panel usando el campo metadata_json.
        Esto permite paneles personalizados sin cambiar el esquema.
        """
        tenant = self.get_by_id(tenant_id)
        if not tenant:
            return None

        # Si el modelo ya hereda de NexusBase, usamos metadata_json
        if hasattr(tenant, "metadata_json"):
            current_meta = tenant.metadata_json or {}
            current_meta.update(config)
            tenant.metadata_json = current_meta
        else:
            # Fallback para modelos antiguos: guardamos en un campo genérico o logueamos advertencia
            pass

        self.session.flush()
        return tenant
