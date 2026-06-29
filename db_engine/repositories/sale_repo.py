from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from db_engine.repositories.base_repo import BaseRepository
from sales.models import Sale, SaleItem


class SaleRepository(BaseRepository):
    """
    Manejo de Ventas.
    Incluye lógica de idempotencia para sincronización de APKs.
    """

    def __init__(self, session: Session):
        super().__init__(Sale, session)

    def create_sale_atomic(
        self, sale_data: dict[str, Any], items_data: list[dict[str, Any]]
    ) -> Sale:
        """
        Crea una venta y sus items en una sola transacción.
        Valida idempotencia mediante client_request_id.
        """
        # 1. Validar Idempotencia (Evitar duplicados de APK)
        request_id = sale_data.get("client_request_id")
        if request_id:
            existing_sale = self.find_one({"client_request_id": request_id})
            if existing_sale:
                return existing_sale

        # 2. Crear la Venta
        sale = self.create(sale_data)

        # 3. Crear los Items
        for item in items_data:
            item["sale_id"] = sale.id
            sale_item = SaleItem(**item)
            self.session.add(sale_item)

        self.session.flush()
        return sale

    def get_tenant_revenue(self, tenant_id: Any, start_date: Any = None, end_date: Any = None):
        """Calcula los ingresos totales de un tenant en un rango de fechas."""
        query = self.session.query(func.sum(Sale.total)).filter(Sale.tenant_id == tenant_id)
        if start_date:
            query = query.filter(Sale.created_at >= start_date)
        if end_date:
            query = query.filter(Sale.created_at <= end_date)

        return query.scalar() or 0.0
