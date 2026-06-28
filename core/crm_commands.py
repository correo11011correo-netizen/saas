import logging
import uuid
from sqlalchemy import text
from sqlalchemy.orm import Session

from core.context import TenantContext
from core.decorators import command
from core.types import ServiceResponse

logger = logging.getLogger("OmniCore.CRM")

class CRMCommandHandler:
    """
    Gestión de Clientes (CRM).
    Permite el seguimiento de clientes, sus datos de contacto y su historial de compras.
    """

    @command(
        name="crm.customer.create",
        description="Creates or updates a customer based on their phone number.",
        params_model={"phone_number": "string", "full_name": "string", "email": "string", "metadata": "dict"},
    )
    def create_or_update_customer(
        self, session: Session, context: TenantContext, phone_number: str, full_name: str = None, email: str = None, metadata: dict = None
    ) -> ServiceResponse:
        try:
            # Buscar si el cliente ya existe para este tenant
            customer = session.execute(
                text("SELECT id FROM customers WHERE tenant_id = :tid AND phone_number = :phone"),
                {"tid": context.tenant_id, "phone": phone_number},
            ).mappings().first()

            if customer:
                customer_id = customer["id"]
                # Actualizar datos si fueron proporcionados
                updates = []
                params = {"tid": context.tenant_id, "phone": phone_number}
                if full_name:
                    updates.append("full_name = :name")
                    params["name"] = full_name
                if email:
                    updates.append("email = :email")
                    params["email"] = email
                if metadata:
                    updates.append("metadata = :meta")
                    params["meta"] = metadata

                if updates:
                    session.execute(
                        text(f"UPDATE customers SET {', '.join(updates)} WHERE tenant_id = :tid AND phone_number = :phone"),
                        params,
                    )
                return ServiceResponse.success_res(data={"customer_id": customer_id}, message="Customer found and updated.")

            # Crear nuevo cliente
            customer_id = uuid.uuid4()
            session.execute(
                text(
                    "INSERT INTO customers (id, tenant_id, phone_number, full_name, email, metadata) VALUES (:id, :tid, :phone, :name, :email, :meta)"
                ),
                {
                    "id": customer_id,
                    "tid": context.tenant_id,
                    "phone": phone_number,
                    "name": full_name,
                    "email": email,
                    "meta": metadata or {},
                },
            )
            return ServiceResponse.success_res(data={"customer_id": customer_id}, message="Customer created successfully.")
        except Exception as e:
            session.rollback()
            return ServiceResponse.error_res(str(e), "CRM_CUSTOMER_CREATE_ERROR")

    @command(
        name="crm.customer.get",
        description="Retrieves a customer's profile and their full purchase history.",
        params_model={"phone_number": "string"},
    )
    def get_customer_profile(
        self, session: Session, context: TenantContext, phone_number: str
    ) -> ServiceResponse:
        try:
            # 1. Obtener datos del cliente
            customer = session.execute(
                text("SELECT * FROM customers WHERE tenant_id = :tid AND phone_number = :phone"),
                {"tid": context.tenant_id, "phone": phone_number},
            ).mappings().first()

            if not customer:
                return ServiceResponse.error_res("Customer not found", "CRM_CUSTOMER_NOT_FOUND")

            # 2. Obtener historial de ventas
            sales = session.execute(
                text(
                    "SELECT s.id, s.total, s.created_at, s.metodo_pago "
                    "FROM sales s JOIN customers c ON s.customer_id = c.id "
                    "WHERE c.tenant_id = :tid AND c.phone_number = :phone "
                    "ORDER BY s.created_at DESC"
                ),
                {"tid": context.tenant_id, "phone": phone_number},
            ).mappings().all()

            return ServiceResponse.success_res(
                data={
                    "profile": dict(customer),
                    "history": [dict(s) for s in sales],
                },
                message="Customer profile retrieved successfully.",
            )
        except Exception as e:
            return ServiceResponse.error_res(str(e), "CRM_CUSTOMER_GET_ERROR")

    @command(
        name="crm.customer.list",
        description="Lists all customers for the current tenant.",
        params_model={},
    )
    def list_customers(self, session: Session, context: TenantContext) -> ServiceResponse:
        try:
            customers = session.execute(
                text("SELECT id, phone_number, full_name, email, created_at FROM customers WHERE tenant_id = :tid ORDER BY created_at DESC"),
                {"tid": context.tenant_id},
            ).mappings().all()

            return ServiceResponse.success_res(
                data=[dict(c) for c in customers],
                message="Customers list retrieved."
            )
        except Exception as e:
            return ServiceResponse.error_res(str(e), "CRM_CUSTOMER_LIST_ERROR")

    @command(
        name="crm.customer.update",
        description="Updates customer contact information.",
        params_model={"phone_number": "string", "full_name": "string", "email": "string", "metadata": "dict"},
    )
    def update_customer(
        self, session: Session, context: TenantContext, phone_number: str, full_name: str = None, email: str = None, metadata: dict = None
    ) -> ServiceResponse:
        # Reutilizamos la lógica de create_or_update
        return self.create_or_update_customer(session, context, phone_number, full_name, email, metadata)

crm_commands = CRMCommandHandler()
