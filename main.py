from fastapi import FastAPI, Depends, HTTPException, Header, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from typing import Dict, Any, Optional
import uvicorn
import os
import uuid
import json
import logging

# Configure global logging to ensure custom loggers print to stdout
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# ... (keep imports and engine/SessionLocal as they are)


from core.dispatcher import dispatcher
from core.auth import auth_service
from core.context import TenantContext
from core.webhooks import router as webhook_router
from core.commands import core_commands
from core.credentials import credentials_commands
from sales.commands import sales_commands
from stock.commands import stock_commands
from stock.sync import stock_sync_commands
from whatsapp.commands import whatsapp_commands, bot_manager_commands
from employees.commands import employee_commands
from core.saas_admin import saas_admin_commands
from core.billing import billing_commands

# ... (Database setup and FastAPI app setup remain as before, I will keep the existing code and just clean up the functions below)

# Database Configuration
DB_URL = os.getenv("DATABASE_URL")
if not DB_URL:
    raise Exception("DATABASE_URL variable not set")
engine = create_engine(DB_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Auto-inicializar la base de datos (Asegurar tablas y columnas)
    try:
        from core.init_db import init_db

        print("🚀 Sincronizando estructura de base de datos...")
        init_db()
        print("✅ Base de datos lista y sincronizada.")
    except Exception as e:
        print(f"❌ Error crítico inicializando la base de datos: {e}")

    # 2. Register all command handlers
    dispatcher.register_handler(core_commands)
    dispatcher.register_handler(core_commands)
    dispatcher.register_handler(credentials_commands)
    dispatcher.register_handler(sales_commands)
    dispatcher.register_handler(stock_commands)
    dispatcher.register_handler(stock_sync_commands)
    dispatcher.register_handler(whatsapp_commands)
    dispatcher.register_handler(bot_manager_commands)
    dispatcher.register_handler(employee_commands)
    dispatcher.register_handler(saas_admin_commands)
    dispatcher.register_handler(billing_commands)

    # Inject DB factory into Webhooks AND Dispatcher
    from core.webhooks import set_db_session_factory

    set_db_session_factory(SessionLocal)
    dispatcher.set_db_session_factory(SessionLocal)
    yield
    # Clean up (if needed)


app = FastAPI(
    title="OmniCore API",
    description="Multi-tenant Command Execution API",
    lifespan=lifespan,
)

# Register Webhook Router
app.include_router(webhook_router)

# Servir archivos estáticos del frontend
app.mount("/static", StaticFiles(directory="frontend"), name="static")


@app.get("/")
async def read_index():
    from fastapi.responses import FileResponse

    return FileResponse("frontend/index.html")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Dependency to get current tenant context from JWT
def get_current_context(
    request: Request, authorization: Optional[str] = Header(None)
) -> TenantContext:
    token = None

    # 1. Intentar obtener token del Header (para llamadas API)
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]

    # 2. Si no hay header, intentar obtenerlo de la Cookie (para navegación web)
    if not token:
        token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(status_code=401, detail="Invalid or missing token")

    context = auth_service.decode_token(token)
    if not context:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return context


# --- SDUI ENDPOINT ---

@app.get("/api/boot")
def boot_app(context: TenantContext = Depends(get_current_context), db=Depends(get_db)):
    """
    The 'Startup Contract'. Delivers the entire UI and config manifest to the APK.
    Filters available modules based on plan and custom entitlements.
    """
    from core.sdui import sdui_engine
    from core.module_entitlements import module_entitlement_service
    
    # 1. Get the basic manifest (theme, base layout)
    manifest = sdui_engine.get_boot_manifest(db, context)
    
    # 2. Calculate which modules this specific tenant is allowed to see
    active_modules = module_entitlement_service.get_active_modules(db, context)
    
    # 3. Filter the layout to only include components belonging to active modules
    # This ensures the APK never even receives the definition of locked modules.
    manifest["active_modules"] = list(active_modules)
    
    return manifest

# --- AUTH ENDPOINTS ---



@app.post("/auth/register")
def register(data: Dict[str, Any], response: Response, db=Depends(get_db)):
    # Data: {email, password, business_name}
    res = auth_service.register(
        db, data["email"], data["password"], data["business_name"]
    )
    if not res["success"]:
        raise HTTPException(status_code=400, detail=res["error"])

    # Establecer cookie de sesión (secure=False para compatibilidad con proxies)
    response.set_cookie(
        key="access_token",
        value=res["token"],
        httponly=True,
        samesite="lax",
        secure=False,
    )
    return res


@app.post("/auth/login")
def login(data: Dict[str, Any], response: Response, db=Depends(get_db)):
    # Data: {email, password}
    res = auth_service.authenticate(db, data["email"], data["password"])
    if not res:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Establecer cookie de sesión (secure=False para compatibilidad con proxies)
    response.set_cookie(
        key="access_token",
        value=res["token"],
        httponly=True,
        samesite="lax",
        secure=False,
    )
    return res


# --- COMMAND EXECUTION ENDPOINT ---


@app.post("/api/execute")
def execute_command(
    payload: Dict[str, Any],
    context: TenantContext = Depends(get_current_context),
    db=Depends(get_db),
):
    """
    Universal endpoint to execute any system command.
    Payload: { "command": "sales.cobrar", "params": { ... } }
    """
    command_name = payload.get("command")
    params = payload.get("params", {})

    if not command_name:
        raise HTTPException(status_code=400, detail="Missing 'command' in payload")

    # Use the dispatcher to execute the command
    dispatcher.db_session_factory = lambda: db
    result = dispatcher.execute(command_name, params, context)

    # Si es un objeto ServiceResponse, accedemos a su atributo success
    if hasattr(result, "success"):
        if not result.success:
            return result
    # Si es un diccionario, verificamos la clave 'success' si existe
    elif isinstance(result, dict) and result.get("success") is False:
        return result

    return result


# --- MIDDLEWARE DE LOGGING ---
# Removed verbose request logging for production.



# Montar frontend al final para que sirva como fallback y maneje rutas relativas
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    print(f"--- SERVIDOR LEVANTANDO EN PUERTO: {port} ---")
    uvicorn.run(app, host="0.0.0.0", port=port)
