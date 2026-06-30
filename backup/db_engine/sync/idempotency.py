from typing import Any

from sqlalchemy.orm import Session

from sales.models import Sale


class IdempotencyManager:
    """
    Gestiona la idempotencia de las transacciones.
    Asegura que una misma solicitud (identificada por un request_id)
    solo se procese una vez, independientemente de cuántas veces se envíe.
    """

    def __init__(self, session: Session):
        self.session = session

    def is_duplicate(self, client_request_id: Any) -> bool:
        """
        Verifica si una transacción con el ID proporcionado ya existe en la base de datos.
        """
        if not client_request_id:
            return False

        existing_sale = (
            self.session.query(Sale).filter(Sale.client_request_id == client_request_id).first()
        )

        return existing_sale is not None

    def get_existing_transaction(self, client_request_id: Any) -> Sale | None:
        """Retorna la transacción original si es un duplicado."""
        if not client_request_id:
            return None

        return self.session.query(Sale).filter(Sale.client_request_id == client_request_id).first()
