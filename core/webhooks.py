import logging
from typing import Any, Dict
from fastapi import APIRouter, Request, BackgroundTasks, HTTPException, Depends
from sqlalchemy import text
from core.dispatcher import dispatcher
from core.types import ServiceResponse
from core.db import get_db

router = APIRouter()
logger = logging.getLogger("OmniCore.Webhooks")

# We need a dependency to get DB session, which is defined in main.py
# Since webhooks.py is imported in main.py, we have to inject it dynamically.
db_session_factory = None


def set_db_session_factory(factory):
    global db_session_factory
    db_session_factory = factory


async def get_tenant_by_secret(secret: str) -> Dict[str, Any]:
    """Look up tenant by webhook_secret."""
    with db_session_factory() as session:
        result = (
            session.execute(
                text("SELECT id FROM tenants WHERE webhook_secret = :secret"),
                {"secret": secret},
            )
            .mappings()
            .first()
        )
        if not result:
            raise HTTPException(status_code=404, detail="Tenant not found")
        return dict(result)


@router.get("/hooks/{secret}/{service}")
async def verify_webhook(secret: str, service: str, request: Request):
    """
    Handles Meta's handshake (GET request).
    """
    logger.info(f"--- Handshake Inicio ---")
    logger.info(f"Secret en URL: {secret}")
    logger.info(f"Params: {request.query_params}")

    # 1. Verify tenant exists
    try:
        tenant = await get_tenant_by_secret(secret)
        logger.info(f"Tenant encontrado: {tenant['id']}")
    except Exception as e:
        logger.error(f"Error buscando tenant: {e}")
        raise HTTPException(status_code=404, detail="Tenant not found")

    # 2. Handle Meta Verification
    params = request.query_params
    hub_mode = params.get("hub.mode")
    hub_token = params.get("hub.verify_token")

    logger.info(f"Hub Mode: {hub_mode}, Token: {hub_token}")

    if hub_mode == "subscribe" and hub_token == secret:
        logger.info("Handshake exitoso. Enviando challenge.")
        return int(params.get("hub.challenge"))

    logger.warning(
        f"Handshake fallido. Token enviado: {hub_token}, Token esperado: {secret}"
    )
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/hooks/{secret}/whatsapp")
async def handle_whatsapp_webhook(
    secret: str, request: Request, background_tasks: BackgroundTasks
):
    """
    Handles WhatsApp message events (POST request).
    """
    # Debug info
    logger.info("--- Recibiendo POST de WhatsApp ---")

    # 2. Get Payload
    payload = await request.json()
    logger.info(f"Payload recibido: {payload}")

    # 1. Identify Tenant
    try:
        tenant = await get_tenant_by_secret(secret)
        tenant_id = tenant["id"]
        logger.info(f"Tenant identificado: {tenant_id}")
    except HTTPException:
        logger.error(f"Tenant no encontrado para secret: {secret}")
        raise HTTPException(status_code=404, detail="Tenant not found")

    # 3. Trigger Background Processing
    if db_session_factory:
        background_tasks.add_task(
            process_webhook_event, db_session_factory, tenant_id, "whatsapp", payload
        )
        logger.info("Tarea en background enviada")
    else:
        logger.error("db_session_factory not initialized")

    return {"status": "ok"}


@router.post("/hooks/mp/ipn")
async def handle_mp_ipn(request: Request, db=Depends(get_db)):
    """
    Handles Mercado Pago IPN notifications.
    """
    payload = await request.json()
    logger.info(f"MP IPN received: {payload}")

    # 1. Verify Payment (Simplificado)
    if payload.get("type") == "payment":
        payment_id = payload.get("data", {}).get("id")
        # Aquí deberías usar el SDK para obtener el detalle del pago y verificarlo
        # ...

        # 2. Update Order Status
        # Buscar orden por external_reference (sale_id)
        # ...

        return {"status": "ok"}

    return {"status": "ignored"}


async def process_webhook_event(
    session_factory, tenant_id: str, event_type: str, payload: Dict[str, Any]
):
    """
    Orchestrates the event by mapping it to a system command.
    """
    with session_factory() as session:
        from whatsapp.bot_engine import BotEngine

        # Event Mapping
        if event_type == "whatsapp":
            # Meta Payload Structure: entry[0].changes[0].value.messages[0]
            try:
                entry = payload.get("entry", [{}])[0]
                changes = entry.get("changes", [{}])[0]
                value = changes.get("value", {})
                messages = value.get("messages", [])

                if not messages:
                    logger.warning("No messages found in payload")
                    return

                msg_data = messages[0]
                sender = msg_data.get("from")

                # Extract text message body
                msg_type = msg_data.get("type", "text")
                if msg_type == "text":
                    message = msg_data.get("text", {}).get("body")
                else:
                    message = f"<{msg_type} message>"

                if not sender or not message:
                    logger.warning(
                        f"Missing sender or message in payload: sender={sender}, msg={message}"
                    )
                    return

                # Use BotEngine
                bot = BotEngine()
                bot.process_message(session, tenant_id, sender, message)
            except (IndexError, KeyError, TypeError) as e:
                logger.error(f"Error parsing Meta payload: {e}")
                logger.error(f"Payload: {payload}")
                return
        else:
            logger.warning(f"Unhandled event type: {secret}")
            return
