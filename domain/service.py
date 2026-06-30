from typing import Any
from motor.application.state import state
from motor.domain.entities import Sale


class BusinessService:
    """
    Súper Servicio de Negocio.
    No tiene dependencias de base de datos, solo usa el EngineState para
    encontrar el proveedor adecuado según la función.
    """

    def process_sale(self, sale_data: dict, tenant_id: Any):
        # 1. Obtener proveedor de ventas y productos desde el estado dinámico
        sales_provider = state.get_provider("sales")
        stock_provider = state.get_provider("stock")

        if not sales_provider or not stock_provider:
            raise Exception("Providers for 'sales' or 'stock' are not connected.")

        # 2. Lógica de Negocio (Ejemplo Simplificado)
        # En un escenario real, aquí validaríamos stock usando stock_provider.get(...)

        # Crear la entidad de dominio pura
        new_sale = Sale(
            customer_id=sale_data["customer_id"],
            total=sale_data["total"],
            tenant_id=tenant_id,
            items=sale_data.get("items", []),
        )

        # 3. Persistencia a través del proveedor dinámico
        return sales_provider.save(new_sale)

    def get_product_info(self, code: str, tenant_id: Any):
        stock_provider = state.get_provider("stock")
        if not stock_provider:
            raise Exception("Stock provider not connected.")

        return stock_provider.get(code)


# Singleton instance
service = BusinessService()
