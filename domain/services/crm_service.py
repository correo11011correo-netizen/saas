from typing import Any, Optional, Dict
from uuid import UUID
from motor.application.state import state
from motor.domain.entities import Customer
from motor.infrastructure.providers.base import BaseProvider


class CRMService:
    """
    Servicio de CRM: Lógica de gestión de clientes.
    Aislamiento total de la base de datos.
    """

    def __init__(self):
        self.state = state

    def _get_provider(self) -> BaseProvider:
        provider = self.state.get_provider("crm")
        if not provider:
            raise Exception("CRM provider not connected.")
        return provider

    def create_or_update_customer(
        self,
        tenant_id: UUID,
        phone: str,
        name: Optional[str] = None,
        email: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> Customer:
        provider = self._get_provider()

        # Buscar cliente por teléfono
        customer = provider.get(phone)

        if customer:
            if name:
                customer.name = name
            if email:
                customer.email = email
            if metadata:
                customer.metadata.update(metadata)
            return provider.save(customer)

        # Crear nuevo
        new_customer = Customer(
            phone=phone, name=name, email=email, tenant_id=tenant_id
        )
        return provider.save(new_customer)

    def get_profile(self, phone: str) -> Dict[str, Any]:
        provider = self._get_provider()
        customer = provider.get(phone)
        if not customer:
            raise ValueError("Customer not found")

        # Para el historial, el CRM pide datos al proveedor de ventas
        sales_provider = self.state.get_provider("sales")
        history = []
        if sales_provider:
            history = sales_provider.list({"customer_id": customer.id})

        return {"profile": customer, "history": history}


# Singleton instance
crm_service = CRMService()
