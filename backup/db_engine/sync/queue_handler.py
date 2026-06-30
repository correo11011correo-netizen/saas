from typing import Any

from sqlalchemy.orm import Session

from db_engine.repositories.sale_repo import SaleRepository
from db_engine.sync.idempotency import IdempotencyManager


class APKQueueHandler:
    """
    Procesador de colas de transacciones provenientes de la APK.
    Asegura que las ventas offline se integren sin duplicados y en el orden correcto.
    """

    def __init__(self, session: Session):
        self.session = session
        self.sale_repo = SaleRepository(session)
        self.idempotency = IdempotencyManager(session)

    def process_sync_queue(
        self, tenant_id: Any, transactions: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """
        Procesa un lote de transacciones sincronizadas desde la APK.
        """
        results = {"processed": 0, "skipped_duplicates": 0, "errors": []}

        for tx in transactions:
            try:
                request_id = tx.get("client_request_id")

                # 1. Verificar Idempotencia
                if self.idempotency.is_duplicate(request_id):
                    results["skipped_duplicates"] += 1
                    continue

                # 2. Preparar datos de la venta y los items
                sale_data = {
                    "tenant_id": tenant_id,
                    "cliente": tx.get("customer_name"),
                    "customer_id": tx.get("customer_id"),
                    "total": tx.get("total"),
                    "metodo_pago": tx.get("payment_method"),
                    "paga_con": tx.get("paid_amount"),
                    "vuelto": tx.get("change"),
                    "client_request_id": request_id,
                    "created_at": tx.get("timestamp"),
                }

                items_data = tx.get("items", [])

                # 3. Crear la venta de forma atómica vía repositorio
                self.sale_repo.create_sale_atomic(sale_data, items_data)

                results["processed"] += 1

            except Exception as e:
                results["errors"].append(
                    {"request_id": tx.get("client_request_id"), "error": str(e)}
                )

        return results
