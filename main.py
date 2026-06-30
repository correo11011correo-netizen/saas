import uvicorn
from fastapi import FastAPI, HTTPException, Body
from typing import Any, Dict
from pydantic import BaseModel

from motor.application.state import state
from motor.domain.service import service
from motor.infrastructure.providers.mock import MockProvider
from motor.infrastructure.persistence.sqlalchemy.user_provider import UserSqlProvider
from motor.infrastructure.persistence.sqlalchemy.product_provider import (
    ProductSqlProvider,
)
from motor.infrastructure.persistence.sqlalchemy.sale_provider import SaleSqlProvider
from motor.infrastructure.persistence.sqlalchemy.customer_provider import (
    CustomerSqlProvider,
)
from motor.infrastructure.persistence.sqlalchemy.bot_provider import BotSqlProvider
from backup.core.database import session_factory  # Adjusted path to backup

app = FastAPI(title="Business Engine Daemon")


class ConnectionRequest(BaseModel):
    function_name: str
    provider_type: str  # 'mock', 'sqlalchemy', 'api'
    connection_string: str = ""


# ... (previous imports)


@app.post("/admin/connect")
async def connect_provider(req: ConnectionRequest):
    """
    Conecta un proveedor de datos a una función del sistema en caliente.
    """
    if req.provider_type == "mock":
        provider = MockProvider(req.function_name)
    elif req.provider_type == "sqlalchemy":
        # Mapping of function names to their specific SQL Provider classes
        mapping = {
            "users": UserSqlProvider,
            "stock": ProductSqlProvider,
            "sales": SaleSqlProvider,
            "crm": CustomerSqlProvider,
            "bots": BotSqlProvider,
        }
        provider_class = mapping.get(req.function_name)
        if not provider_class:
            raise HTTPException(
                status_code=400,
                detail=f"No SQLAlchemy provider for {req.function_name}",
            )

        # Inject the real session factory from the project
        provider = provider_class(
            session_factory=session_factory,
            model_class=provider_class.model_class
            if hasattr(provider_class, "model_class")
            else None,
        )
        # Note: For a more robust implementation, the model_class would be defined inside the provider class.
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Provider type {req.provider_type} not implemented yet.",
        )

    state.set_provider(req.function_name, provider)
    return {
        "success": True,
        "message": f"Provider {req.provider_type} connected to {req.function_name}",
    }


@app.get("/admin/status")
async def get_system_status():
    """Retorna el estado de salud de todos los puentes conectados."""
    return {"engine_status": "active", "providers": state.get_all_status()}


@app.post("/admin/disconnect")
async def disconnect_provider(function_name: str):
    """Desconecta un proveedor específico."""
    if function_name in state.providers:
        del state.providers[function_name]
        return {"success": True, "message": f"Disconnected {function_name}"}
    raise HTTPException(status_code=404, detail="Provider not found")


# --- BUSINESS ENDPOINTS (Puente de Interfaz) ---


@app.post("/api/sale/create")
async def create_sale(data: Dict[str, Any] = Body(...), tenant_id: str = "default"):
    """
    Procesa una venta utilizando el proveedor de datos activo.
    """
    try:
        # El servicio se encarga de buscar el proveedor en el state
        result = service.process_sale(data, tenant_id)
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/product/{code}")
async def get_product(code: str, tenant_id: str = "default"):
    """
    Obtiene info de producto desde el proveedor de stock activo.
    """
    try:
        result = service.get_product_info(code, tenant_id)
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    # Ejecución del Daemon
    uvicorn.run(app, host="0.0.0.0", port=8000)
