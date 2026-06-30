from typing import Any, List, Optional, Dict
from infrastructure.providers.base import BaseProvider


class MockProvider(BaseProvider):
    """
    Proveedor de datos en memoria para pruebas rápidas.
    Permite que el sistema funcione sin ninguna base de datos conectada.
    """

    def __init__(self, entity_type: str):
        self.entity_type = entity_type
        self.data: Dict[Any, Any] = {}

    def get(self, id: Any) -> Optional[Any]:
        return self.data.get(id)

    def list(self, filters: dict = None) -> List[Any]:
        return list(self.data.values())

    def save(self, entity: Any) -> Any:
        # Intentar obtener el ID de la entidad (asumiendo que tiene atributo .id)
        entity_id = getattr(entity, "id", None)
        if entity_id:
            self.data[entity_id] = entity
        return entity

    def delete(self, id: Any) -> bool:
        if id in self.data:
            del self.data[id]
            return True
        return False

    def health_check(self) -> bool:
        return True
