from typing import Any, TypeVar, List, Optional
from sqlalchemy import select
from motor.infrastructure.providers.base import BaseProvider

T = TypeVar("T")


class SqlAlchemyProvider(BaseProvider[T]):
    """
    Implementación de BaseProvider usando SQLAlchemy.
    Actúa como el adaptador que traduce las órdenes del núcleo a SQL.
    """

    def __init__(self, session_factory, model_class):
        self.session_factory = session_factory
        self.model_class = model_class

    def get(self, id: Any) -> Optional[T]:
        with self.session_factory() as session:
            entity = session.get(self.model_class, id)
            return self._to_domain(entity) if entity else None

    def list(
        self, filters: dict = None, limit: int = None, offset: int = None
    ) -> List[T]:
        with self.session_factory() as session:
            query = select(self.model_class)
            if filters:
                for key, value in filters.items():
                    query = query.where(getattr(self.model_class, key) == value)

            if limit:
                query = query.limit(limit)
            if offset:
                query = query.offset(offset)

            result = session.execute(query).scalars().all()
            return [self._to_domain(row) for row in result]

    def save(self, entity: T) -> T:
        with self.session_factory() as session:
            # Convertir entidad de dominio a modelo de DB
            db_model = self._to_db(entity)

            # Merge maneja tanto insert como update basándose en la PK
            merged = session.merge(db_model)
            session.commit()
            session.refresh(merged)
            return self._to_domain(merged)

    def delete(self, id: Any) -> bool:
        with self.session_factory() as session:
            entity = session.get(self.model_class, id)
            if entity:
                session.delete(entity)
                session.commit()
                return True
            return False

    def health_check(self) -> bool:
        try:
            with self.session_factory() as session:
                session.execute(select(1))
            return True
        except Exception:
            return False

    def _to_domain(self, db_model: Any) -> T:
        """
        MÉTODO A SOBRESCRIBIR.
        Traduce un modelo de SQLAlchemy -> Entidad de Dominio Pura.
        """
        raise NotImplementedError("Must implement _to_domain")

    def _to_db(self, entity: T) -> Any:
        """
        MÉTODO A SOBRESCRIBIR.
        Traduce una Entidad de Dominio Pura -> Modelo de SQLAlchemy.
        """
        raise NotImplementedError("Must implement _to_db")
