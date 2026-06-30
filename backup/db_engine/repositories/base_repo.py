from typing import Any, Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

T = TypeVar("T")


class BaseRepository(Generic[T]):
    """
    Repositorio Base Genérico para NexusDB.
    Proporciona operaciones CRUD estándar para cualquier modelo que herede de NexusBase.
    """

    def __init__(self, model: type[T], session: Session):
        self.model = model
        self.session = session

    def get_by_id(self, id: Any) -> T | None:
        """Obtiene una entidad por su ID."""
        return self.session.get(self.model, id)

    def get_all(
        self, filters: dict[str, Any] = None, limit: int = None, offset: int = None
    ) -> list[T]:
        """
        Obtiene todas las entidades que coincidan con los filtros.
        Ejemplo de filtros: {"tenant_id": 1, "status": "active"}
        """
        query = select(self.model)
        if filters:
            for key, value in filters.items():
                query = query.where(getattr(self.model, key) == value)

        if limit:
            query = query.limit(limit)
        if offset:
            query = query.offset(offset)

        result = self.session.execute(query)
        return result.scalars().all()

    def create(self, data: dict[str, Any]) -> T:
        """
        Crea una nueva entidad.
        Acepta un diccionario de datos para evitar la dependencia directa del modelo en la llamada.
        """
        entity = self.model(**data)
        self.session.add(entity)
        self.session.flush()  # Para obtener el ID generado
        return entity

    def update(self, id: Any, data: dict[str, Any]) -> T | None:
        """
        Actualiza una entidad existente.
        Soporta actualizaciones parciales.
        """
        entity = self.get_by_id(id)
        if not entity:
            return None

        for key, value in data.items():
            if hasattr(entity, key):
                setattr(entity, key, value)

        self.session.flush()
        return entity

    def delete(self, id: Any) -> bool:
        """
        Elimina una entidad.
        En NexusDB, preferimos el Soft Delete, pero este método realiza el borrado físico.
        """
        entity = self.get_by_id(id)
        if not entity:
            return False

        self.session.delete(entity)
        self.session.flush()
        return True

    def find_one(self, filters: dict[str, Any]) -> T | None:
        """Encuentra la primera entidad que coincida con los filtros."""
        entities = self.get_all(filters=filters, limit=1)
        return entities[0] if entities else None
