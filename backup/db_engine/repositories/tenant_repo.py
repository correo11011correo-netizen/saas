from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from db_engine.repositories.base_repo import BaseRepository


# Model placeholder since we might be using raw SQL in the repo for complex queries
# but we want to maintain the BaseRepository interface.
class TenantModel:
    pass


class TenantRepository(BaseRepository[TenantModel]):
    def __init__(self, session: Session):
        super().__init__(TenantModel, session)

    def get_by_id(self, tenant_id: Any) -> dict | None:
        result = (
            self.session.execute(text("SELECT * FROM tenants WHERE id = :id"), {"id": tenant_id})
            .mappings()
            .first()
        )
        return dict(result) if result else None

    def create(self, data: dict[str, Any]) -> dict:
        # We keep the raw SQL for creation to ensure we match the current a-sync
        # registration logic exactly.
        result = self.session.execute(
            text(
                "INSERT INTO tenants (id, name, webhook_secret, plan) VALUES (:id, :name, :secret, :plan) RETURNING id"
            ),
            data,
        ).scalar()
        return {"id": result}

    def update_plan(self, tenant_id: Any, plan: str):
        self.session.execute(
            text("UPDATE tenants SET plan = :plan WHERE id = :id"), {"plan": plan, "id": tenant_id}
        )
