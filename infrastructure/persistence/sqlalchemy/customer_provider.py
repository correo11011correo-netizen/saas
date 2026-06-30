from uuid import UUID
from typing import Optional
from motor.infrastructure.persistence.sqlalchemy.base_provider import SqlAlchemyProvider
from motor.domain.entities import Customer
from crm.models import Customer as DBCustomer


class CustomerSqlProvider(SqlAlchemyProvider):
    def _to_domain(self, db_model: DBCustomer) -> Customer:
        return Customer(
            id=db_model.id,
            phone=db_model.phone_number,
            name=db_model.full_name,
            email=db_model.email,
            tenant_id=db_model.tenant_id,
        )

    def _to_db(self, entity: Customer) -> DBCustomer:
        return DBCustomer(
            id=entity.id,
            phone_number=entity.phone,
            full_name=entity.name,
            email=entity.email,
            tenant_id=entity.tenant_id,
        )

    def get_by_phone(self, phone: str, tenant_id: UUID) -> Optional[Customer]:
        from sqlalchemy import select

        with self.session_factory() as session:
            query = select(DBCustomer).where(
                DBCustomer.phone_number == phone, DBCustomer.tenant_id == tenant_id
            )
            res = session.execute(query).scalar_one_or_none()
            return self._to_domain(res) if res else None
