import os
from contextlib import asynccontextmanager
from typing import Any

import uvicorn
from fastapi import (
    Depends,
    FastAPI,
    Header,
    HTTPException,
    Request,
    Response,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from core.advanced_ui_commands import advanced_ui_commands
from core.auth import auth_service
from core.billing import billing_commands
from core.commands import core_commands
from core.context import TenantContext
from core.credentials import credentials_commands
from core.crm_commands import crm_commands
from core.deployment_validator import DeploymentValidator
from core.dev_admin_commands import dev_admin_commands
from core.dispatcher import dispatcher
from core.logger import setup_logging
from core.module_entitlements import module_entitlement_service
from core.panel_commands import panel_commands
from core.realtime import realtime_manager
from core.saas_admin import saas_admin_commands
from core.schema_sync import SchemaSync
from core.sdui import sdui_engine
from core.url_gateway import url_gateway
from core.webhooks import router as webhook_router
from core.webhooks import set_db_session_factory
from db_engine.bootstrap import bootstrap
from employees.commands import employee_commands
from sales.commands import sales_commands
from stock.commands import stock_commands
from stock.sync import stock_sync_commands
from whatsapp.commands import bot_manager_commands, whatsapp_commands

# Configure global logging
logger = setup_logging()

# Database Configuration
DB_URL = os.getenv("DATABASE_URL")
if not DB_URL:
    raise Exception("DATABASE_URL variable not set")
engine = create_engine(DB_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Iniciando secuencia de arranque del sistema...")

    # 0. Validación de Despliegue (Pre-flight)
    try:
        validator = DeploymentValidator(engine)
        if not validator.validate_all():
            logger.warning(
                "⚠️ Advertencia: El sistema ha detectado problemas de infraestructura. Intenta reiniciar la DB si el arranque se congela."
            )
    except Exception as e:
        logger.error(f"❌ Error crítico en el validador de despliegue: {e}")

    # 1. Sincronización Automática de Esquema (Sustituye a Alembic)
    try:
        logger.info("Step 1/3: Sincronizando esquema de base de datos...")
        syncer = SchemaSync(engine)
        syncer.sync()
        logger.info("✅ Esquema sincronizado.")
    except Exception as e:
        logger.critical(f"❌ Error crítico en la sincronización del esquema: {e}", exc_info=True)
        # Permitimos que el servidor inicie para diagnóstico, pero marcamos inestabilidad.

    # 2. Ejecutar el Bootstrap de NexusDB
    try:
        logger.info(
            "Step 2/3: Ejecutando NexusDB Bootstrap (Sincronización de Permisos y Datos)..."
        )
        bootstrap.initialize()
        logger.info("✅ Bootstrap completado exitosamente.")
    except Exception as e:
        logger.error(
            f"⚠️ Error en Bootstrap: {e}. El sistema puede presentar inconsistencias en permisos.",
            exc_info=True,
        )

    # 3. Registro de Handlers de Comandos
    try:
        logger.info("Step 3/3: Registrando manejadores de comandos...")
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
        dispatcher.register_handler(crm_commands)
        dispatcher.register_handler(panel_commands)
        dispatcher.register_handler(advanced_ui_commands)
        dispatcher.register_handler(dev_admin_commands)
        logger.info("✅ Todos los comandos han sido registrados.")
    except Exception as e:
        logger.critical(f"❌ Error registrando comandos: {e}", exc_info=True)
        raise e

    # Inject DB factory into Webhooks AND Dispatcher
    set_db_session_factory(SessionLocal)
    dispatcher.set_db_session_factory(SessionLocal)

    logger.info("🌟 Servidor OmniCore completamente operativo y listo para recibir peticiones.")
    yield


app = FastAPI(
    title="OmniCore API",
    description="Multi-tenant Command Execution API",
    lifespan=lifespan,
)


# Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # Registrar el error con nivel CRITICAL y stack trace completo
    logger.critical(f"Unhandled exception: {exc}", exc_info=True)

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": "Internal server error occurred.",
            "code": "INTERNAL_SERVER_ERROR",
        },
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
    request: Request, authorization: str | None = Header(None)
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


@app.post("/api/log-error")
async def log_error(
    payload: dict[str, Any],
    context: TenantContext = Depends(get_current_context),
    db=Depends(get_db),
):
    """
    Endpoint para centralizar logs de errores del frontend y backend.
    """
    db.execute(
        text(
            "INSERT INTO error_logs (tenant_id, source, message, stack_trace) VALUES (:tid, :src, :msg, :st)"
        ),
        {
            "tid": context.tenant_id,
            "src": payload.get("source", "unknown"),
            "msg": payload.get("message", ""),
            "st": payload.get("stack_trace", ""),
        },
    )
    db.commit()
    return {"success": True}


@app.get("/api/test-error")
async def test_error():
    logger.info("Test log: triggering an error")
    raise Exception("This is a test error for logging verification")


# Register Webhook Router
app.include_router(webhook_router)


@app.get("/api/cmd/{token}")
def execute_url_command(token: str, db=Depends(get_db)):
    """
    Gateway for executing commands via signed URLs.
    No auth token required as the signature is the proof of authority.
    """
    return url_gateway.validate_and_execute(token, db)


# Servir archivos estáticos del frontend
app.mount("/static", StaticFiles(directory="frontend"), name="static")


@app.get("/api/health")
def health_check(db=Depends(get_db)):
    """
    Endpoint para verificación de salud. Usado por Railway para despliegues Zero-Downtime.
    """
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Database Down")
    return {"status": "ok"}


# --- REALTIME GATEWAY ---


@app.websocket("/ws/realtime")
async def websocket_endpoint(websocket: WebSocket, token: str = None):
    """
    Real-time gateway for chats, bot events and UI updates.
    """
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    try:
        # Validate token using the same logic as REST API
        from core.auth import auth_service

        context = auth_service.decode_token(token)
        if not context:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        await realtime_manager.connect(websocket, str(context.tenant_id), str(context.user_id))

        try:
            while True:
                # Keep connection alive and listen for client-side events if needed
                await websocket.receive_text()
                # Handle incoming WS messages here (e.g. typing indicators)
        except WebSocketDisconnect:
            realtime_manager.disconnect(str(context.tenant_id), str(context.user_id))

    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close()


# --- SDUI ENDPOINT ---


@app.get("/api/boot")
def boot_app(context: TenantContext = Depends(get_current_context), db=Depends(get_db)):
    """
    The 'Startup Contract'. Delivers the entire UI and config manifest to the APK.
    Filters available modules based on plan and custom entitlements.
    """

    # 1. Get the basic manifest (theme, base layout)
    manifest = sdui_engine.get_boot_manifest(db, context)

    # 2. Calculate which modules this specific tenant is allowed to see (Skip for SuperAdmin)
    if context.tenant_id:
        active_modules = module_entitlement_service.get_active_modules(db, context)
        # 3. Filter the layout to only include components belonging to active modules
        # This ensures the APK never even receives the definition of locked modules.
        manifest["active_modules"] = list(active_modules)
    else:
        manifest["active_modules"] = []

    return manifest


# --- AUTH ENDPOINTS ---


@app.get("/auth/onboarding-status")
def get_onboarding_status(
    context: TenantContext = Depends(get_current_context), db=Depends(get_db)
):
    """
    Indica al usuario qué pasos le faltan para completar la configuración inicial.
    """
    # 1. Verificar credenciales de WhatsApp
    creds = (
        db.execute(
            text(
                "SELECT api_key FROM credentials WHERE tenant_id = :tid AND service_name = 'whatsapp'"
            ),
            {"tid": context.tenant_id},
        )
        .mappings()
        .first()
    )
    whatsapp_configured = bool(creds and creds["api_key"])

    # 2. Verificar si hay productos cargados
    products_count = db.execute(
        text("SELECT count(*) as total FROM products WHERE tenant_id = :tid"),
        {"tid": context.tenant_id},
    ).scalar()
    stock_loaded = (products_count or 0) > 0

    return {
        "status": "complete" if whatsapp_configured and stock_loaded else "incomplete",
        "steps": {
            "whatsapp_configured": whatsapp_configured,
            "stock_loaded": stock_loaded,
        },
        "next_step": "Configure WhatsApp"
        if not whatsapp_configured
        else ("Load Stock" if not stock_loaded else "Ready"),
    }


@app.post("/auth/register")
def register(data: dict[str, Any], response: Response, db=Depends(get_db)):
    # Data: {email, password, business_name, plan}
    res = auth_service.register(
        db, data["email"], data["password"], data["business_name"], data.get("plan", "free")
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
def login(data: dict[str, Any], response: Response, db=Depends(get_db)):
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
    payload: dict[str, Any],
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


# Montar frontend al final para que sirva como fallback y maneje rutas relativas
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    logger.info(f"--- SERVIDOR LEVANTANDO EN PUERTO: {port} ---")
    uvicorn.run(app, host="0.0.0.0", port=port, log_config=None)
