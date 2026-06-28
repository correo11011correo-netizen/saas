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

    # 1. Verify Payment Event
    if payload.get("type") == "payment":
        payment_id = payload.get("data", {}).get("id")
        
        # Para validar el pago, necesitamos obtener los detalles desde la API de MP
        # En un entorno real, aquí llamaríamos al SDK de MP para confirmar el estado 'approved'
        
        # 2. Find the Sale ID from the payment details
        # Dado que MP envía la notificación, necesitamos recuperar la 'external_reference'
        # que es nuestro sale_id.
        import mercadopago
        # Obtenemos la API Key de MP del tenant (simplificado: usamos la primera encontrada o una config global)
        # Idealmente, buscaríamos el tenant asociado al pago.
        try:
            # 1. Recuperar el sale_id (external_reference) desde MP API
            # Para esto necesitamos el tenant_id de la orden y su API Key
            with db_session_factory() as session:
                # Primero buscamos la orden para saber a qué tenant pertenece
                # Como el IPN solo nos da el payment_id, primero consultamos MP con una key temporal o general 
                # para obtener el external_reference, LUEGO buscamos el tenant.
                # Pero para ser estrictos, usaremos la MP_API_KEY global solo para el primer salto.
                
                sdk = mercadopago.SDK(os.getenv("MP_API_KEY", "")) 
                payment_info = sdk.payment().get(payment_id)
                sale_id = payment_info["response"].get("external_reference")
                status = payment_info["response"].get("status")

                if not sale_id:
                    logger.error(f"No external_reference found for payment {payment_id}")
                    return {"status": "no_reference"}

                if status == "approved":
                    logger.info(f"Payment approved for sale {sale_id}. Triggering confirmation.")
                    
                    # Ahora buscamos el tenant y su credencial específica
                    order = session.execute(
                        text("SELECT tenant_id FROM sales_orders WHERE id = :id"),
                        {"id": sale_id}
                    ).mappings().first()
                    
                    if not order:
                        logger.error(f"Order {sale_id} not found in database")
                        return {"status": "order_not_found"}
                    
                    tenant_id = order['tenant_id']
                    
                    # Usamos el dispatcher con el contexto del tenant
                    from core.context import TenantContext
                    import uuid
                    
                    ctx = TenantContext(
                        tenant_id=tenant_id,
                        user_id=uuid.UUID('00000000-0000-0000-0000-000000000000'),
                        role='system',
                        plan='pro'
                    )
                    
                    dispatcher.execute(
                        "sales.confirm_payment", 
                        {"sale_id": sale_id}, 
                        ctx
                    )
                    logger.info(f"Sale {sale_id} confirmed and stock updated.")

        except Exception as e:
            logger.error(f"Error processing MP IPN: {e}")
            return {"status": "error", "message": str(e)}

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

        if event_type == "whatsapp":
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
                
                # Extraer phone_number_id del payload de Meta
                phone_number_id_from_meta = value.get("metadata", {}).get("phone_number_id")
                if not phone_number_id_from_meta:
                    logger.error(f"No se encontró phone_number_id en el payload de Meta: {payload}")
                    return
                
                logger.info(f"Mensaje de WhatsApp recibido para phone_number_id: {phone_number_id_from_meta}")

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

                bot = BotEngine()
                bot.process_message(session, tenant_id, sender, message, phone_number_id_from_meta)
            except (IndexError, KeyError, TypeError) as e:
                logger.error(f"Error parsing Meta payload: {e}")
                logger.error(f"Payload: {payload}")
                return
        else:
            logger.warning(f"Unhandled event type: {event_type}") # Cambiado 'secret' a 'event_type'
            return
