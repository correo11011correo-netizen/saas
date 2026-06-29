from typing import Any

from sqlalchemy.orm import Session

from core.permissions import Permission, PlanPermission, UserPermission
from db_engine.repositories.base_repo import BaseRepository


class PermissionRepository(BaseRepository):
    """
    Gestor de Permisos y Capacidades.
    Carga y valida los permisos basados en el plan del tenant y las asignaciones del usuario.
    """

    def __init__(self, session: Session):
        super().__init__(Permission, session)

    def get_user_capabilities(self, user_id: Any, plan_name: str) -> set[str]:
        """
        Calcula el set final de capacidades de un usuario.
        Lógica: (Permisos del Plan) + (Permisos Otorgados) - (Permisos Revocados).
        """
        # 1. Obtener permisos básicos del plan
        plan_perms_query = (
            self.session.query(Permission.code)
            .join(PlanPermission)
            .filter(PlanPermission.plan_name == plan_name.lower())
            .all()
        )

        capabilities = {row[0] for row in plan_perms_query}

        # 2. Aplicar overrides del usuario
        user_perms_query = (
            self.session.query(Permission.code, UserPermission.is_granted)
            .join(UserPermission)
            .filter(UserPermission.user_id == user_id)
            .all()
        )

        for code, is_granted in user_perms_query:
            if is_granted:
                capabilities.add(code)
            else:
                capabilities.discard(code)

        return capabilities

    def get_all_available_permissions(self, module: str = None) -> list[Permission]:
        """Retorna la lista de permisos disponibles para configurar en el panel."""
        query = self.session.query(Permission)
        if module:
            query = query.filter(Permission.module == module)
        return query.all()

    def sync_system_permissions(self, permissions_list: list[dict[str, str]]):
        """
        Sincroniza la lista de permisos del sistema.
        Útil para actualizaciones de versión donde se añaden nuevas capacidades.
        """
        for p_data in permissions_list:
            perm = self.find_one({"code": p_data["code"]})
            if not perm:
                self.create(
                    {
                        "code": p_data["code"],
                        "description": p_data.get("description", ""),
                        "module": p_data.get("module", "general"),
                    }
                )
