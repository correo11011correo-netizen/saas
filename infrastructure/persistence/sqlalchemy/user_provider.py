from infrastructure.persistence.sqlalchemy.base_provider import SqlAlchemyProvider
from domain.entities import User
from core.models import User as DBUser  # Asumiendo que el modelo original está aquí


class UserSqlProvider(SqlAlchemyProvider):
    def _to_domain(self, db_model: DBUser) -> User:
        return User(
            id=db_model.id,
            email=db_model.email,
            role=db_model.role,
            tenant_id=db_model.tenant_id,
        )

    def _to_db(self, entity: User) -> DBUser:
        return DBUser(
            id=entity.id,
            email=entity.email,
            role=entity.role,
            tenant_id=entity.tenant_id,
        )
