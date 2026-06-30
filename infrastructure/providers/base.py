from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar, List, Optional

T = TypeVar("T")


class BaseProvider(ABC, Generic[T]):
    """
    Interface base para cualquier proveedor de datos.
    Sواء sea una base de datos SQL, una API externa o un archivo.
    """

    @abstractmethod
    def get(self, id: Any) -> Optional[T]:
        pass

    @abstractmethod
    def list(self, filters: dict = None) -> List[T]:
        pass

    @abstractmethod
    def save(self, entity: T) -> T:
        pass

    @abstractmethod
    def delete(self, id: Any) -> bool:
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """Verifica si la conexión al recurso es activa."""
        pass
