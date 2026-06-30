from typing import Any, Dict, List, Optional
from uuid import uuid4, UUID
from application.state import state
from domain.entities import Sale, SaleItem, Customer
from infrastructure.providers.base import BaseProvider


class SalesService:
    """
    Servicio de Ventas: Contiene la lógica de negocio compleja y orquestación.
    Totalmente desacoplado de la base de datos.
    """

    def __init__(self):
        self.state = state

    def _get_provider(self, name: str) -> BaseProvider:
        provider = self.state.get_provider(name)
        if not provider:
            raise Exception(
                f"Provider '{name}' not connected. Please connect via /admin/connect"
            )
        return provider

    def process_cash_sale(
        self,
        tenant_id: UUID,
        user_id: UUID,
        customer_phone: str,
        items_data: List[Dict],
        paga_con: float,
    ) -> Dict[str, Any]:
        """
        Lógica completa de 'sales.cobrar'.
        Valida stock, gestiona CRM, calcula totales y registra la venta.
        """
        stock_provider = self._get_provider("stock")
        sales_provider = self._get_provider("sales")
        crm_provider = self._get_provider("crm")

        # 1. Validar stock y calcular total (Lógica de Negocio Pura)
        total = 0.0
        processed_items = []

        for item in items_data:
            product = stock_provider.get(item["code"])
            if not product:
                raise ValueError(f"Product {item['code']} not found")

            # Validación de stock
            if product.quantity < item["quantity"]:
                raise ValueError(
                    f"Insufficient stock for {product.name} ({item['code']})"
                )

            subtotal = product.price * item["quantity"]
            total += subtotal
            processed_items.append(
                SaleItem(
                    product_code=product.code,
                    quantity=item["quantity"],
                    price=product.price,
                )
            )

        # 2. Integración CRM: Obtener o crear cliente
        customer = crm_provider.get(customer_phone)
        if not customer:
            customer = Customer(phone=customer_phone, tenant_id=tenant_id)
            crm_provider.save(customer)

        # 3. Validar pago
        vuelto = paga_con - total
        if vuelto < 0:
            raise ValueError(f"Payment insufficient. Total: {total}, Paid: {paga_con}")

        # 4. Registrar la venta
        sale = Sale(
            customer_id=customer.id,
            total=total,
            tenant_id=tenant_id,
            items=processed_items,
        )
        saved_sale = sales_provider.save(sale)

        # 5. Descontar stock y registrar movimientos
        for item in processed_items:
            # Actualizar cantidad en el objeto de dominio
            product = stock_provider.get(item.product_code)
            product.quantity -= item.quantity
            stock_provider.save(product)

            # Registrar movimiento (asumiendo que el provider tiene método add_movement)
            if hasattr(stock_provider, "add_movement"):
                stock_provider.add_movement(
                    code=item.product_code,
                    quantity=-item.quantity,
                    reason="SALE",
                    user_id=user_id,
                    tenant_id=tenant_id,
                )

        return {"sale_id": saved_sale.id, "total": total, "vuelto": vuelto}

    def create_digital_order(
        self,
        tenant_id: UUID,
        items_data: List[Dict],
        total: float,
        account_alias: str,
        client_request_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Lógica de 'sales.create'.
        Maneja idempotencia, credenciales de pago y creación de orden pendiente.
        """
        sales_provider = self._get_provider("sales")
        cred_provider = self._get_provider("credentials")
        payment_gw = self._get_provider("payment_gateway")

        # 0. Check de Idempotencia
        if client_request_id:
            existing = sales_provider.get(client_request_id)
            if existing:
                return {"sale_id": existing.id, "status": "already_exists"}

        # 1. Obtener credenciales
        cred = cred_provider.get_by_alias(account_alias, tenant_id)
        if not cred:
            raise Exception("Payment credentials not found for this alias")

        # 2. Crear Orden Pendiente
        sale = Sale(
            customer_id=uuid4(),  # Temporal hasta confirmación
            total=total,
            tenant_id=tenant_id,
            items=[
                SaleItem(product_code=i["code"], quantity=i["qty"], price=i["price"])
                for i in items_data
            ],
        )
        saved_sale = sales_provider.save(sale)

        # 3. Generar Link de Pago (Vía Puerto Externo)
        payment_link = payment_gw.create_preference(
            amount=total, external_reference=str(saved_sale.id), api_key=cred.api_key
        )

        # 4. Actualizar orden con el link
        saved_sale.metadata["payment_link"] = payment_link
        sales_provider.save(saved_sale)

        return {"payment_link": payment_link, "sale_id": saved_sale.id}


# Singleton instance
sales_service = SalesService()
