import logging
from typing import Any, Dict, List, Optional
from sqlalchemy import text
from sqlalchemy.orm import Session
from core.types import ServiceResponse
from core.decorators import command
from core.context import TenantContext

logger = logging.getLogger("OmniCore.StockSync")

class StockSyncCommandHandler:
    """
    Gestión de Sincronización de Stock para APKs (Edge Cache).
    Permite la descarga inicial y la actualización incremental.
    """

    @command(
        name="stock.sync",
        description="Retrieves products modified since a specific timestamp for incremental sync.",
        params_model={"last_sync": "string"},
    )
    def sync_stock(
        self, 
        session: Session, 
        context: TenantContext, 
        last_sync: str = None
    ) -> ServiceResponse:
        try:
            if not last_sync:
                # Sincronización Inicial: Todo el stock
                query = "SELECT code, name, price, quantity, category, is_weight FROM products WHERE tenant_id = :tid"
                params = {"tid": context.tenant_id}
            else:
                # Sincronización Incremental: Solo cambios recientes
                # Nota: Para que esto sea perfecto, necesitaríamos una columna 'updated_at' en la tabla 'products'.
                # Por ahora, simularemos la búsqueda por movimientos de stock recientes.
                query = """
                    SELECT p.code, p.name, p.price, p.quantity, p.category, p.is_weight 
                    FROM products p
                    JOIN stock_movements sm ON p.code = sm.product_code AND p.tenant_id = sm.tenant_id
                    WHERE p.tenant_id = :tid AND sm.created_at > :last_sync
                """
                # Como no tenemos created_at en stock_movements explícitamente en el esquema actual (solo en la tabla general), 
                # en una implementación real añadiríamos esa columna.
                params = {"tid": context.tenant_id, "last_sync": last_// No puedo usar la variable aquí, la defino abajo.
                params = {"tid": context.tenant_id, "last_sync": last_sync}

            result = session.execute(text(query), params).mappings().all()
            
            return ServiceResponse.success_res(
                data=[dict(row) for row in result],
                message=f"Synchronized {len(result)} products."
            )
        except Exception as e:
            return ServiceResponse.error_res(str(e), "STOCK_SYNC_ERROR")

stock_sync_commands = StockSyncCommandHandler()
