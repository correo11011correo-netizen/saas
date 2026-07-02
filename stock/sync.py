import logging

from sqlalchemy.orm import Session

from core.context import TenantContext
from core.decorators import command
from core.types import ServiceResponse
from core.data_commands import data_commands

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
        self, session: Session, context: TenantContext, last_sync: str = None
    ) -> ServiceResponse:
        try:
            if not last_sync:
                # Sincronización Inicial: Todo el stock
                res = data_commands.query_data(
                    session, context, entity="products"
                )
                if not res.success:
                    return res
                
                # Filtrar solo las columnas necesarias para el APK
                data = [
                    {
                        "code": p.get("code"),
                        "name": p.get("name"),
                        "price": p.get("price"),
                        "quantity": p.get("quantity"),
                        "category": p.get("category"),
                        "is_weight": p.get("is_weight"),
                    }
                    for p in res.data
                ]
                return ServiceResponse.success_res(
                    data=data, message=f"Synchronized {len(data)} products."
                )
            else:
                # Sincronización Incremental: Solo cambios recientes
                res = data_commands.get_modified_products(
                    session, context, last_sync=last_sync
                )
                if not res.success:
                    return res

                return ServiceResponse.success_res(
                    data=res.data, message=f"Synchronized {len(res.data)} products."
                )
        except Exception as e:
            return ServiceResponse.error_res(str(e), "STOCK_SYNC_ERROR")


stock_sync_commands = StockSyncCommandHandler()
