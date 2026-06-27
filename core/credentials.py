import logging
from typing import Any, Dict, Optional
from sqlalchemy import text
from sqlalchemy.orm import Session
from core.types import ServiceResponse
from core.decorators import command
from core.context import TenantContext
import os

logger = logging.getLogger("OmniCore.Credentials")
BASE_URL = os.getenv("BASE_URL")
if not BASE_URL:
    raise Exception("BASE_URL environment variable is required for generating webhook URLs")


class CredentialsCommandHandler:
    """
    Gestión de API Tokens y Secretos por Tenant.
    Permite que cada cliente configure sus propias integraciones.
    """

    @command(
        name="system.list_credentials",
        description="Lists all configured credentials for the current tenant.",
        params_model={},
    )
    def list_credentials(
        self, session: Session, context: TenantContext
    ) -> ServiceResponse:
        try:
            result = (
                session.execute(
                    text(
                        "SELECT service_name, account_alias, api_key, secret, metadata FROM credentials WHERE tenant_id = :tid"
                    ),
                    {"tid": context.tenant_id},
                )
                .mappings()
                .all()
            )
            return ServiceResponse.success_res(
                data=[dict(row) for row in result],
                message="Credentials listed successfully.",
            )
        except Exception as e:
            return ServiceResponse.error_res(
                f"Error listing credentials: {str(e)}", "CRED_LIST_ERROR"
            )

    @command(
        name="system.delete_credential",
        description="Deletes a credential for a specific service account.",
        params_model={"service": "string", "account_alias": "string"},
    )
    def delete_credential(
        self,
        session: Session,
        context: TenantContext,
        service: str,
        account_alias: str,
    ) -> ServiceResponse:
        try:
            session.execute(
                text(
                    "DELETE FROM credentials WHERE service_name = :service AND account_alias = :alias AND tenant_id = :tid"
                ),
                {"service": service, "alias": account_alias, "tid": context.tenant_id},
            )
            session.commit()
            return ServiceResponse.success_res(
                message=f"Credential for {service} ({account_alias}) deleted successfully."
            )
        except Exception as e:
            session.rollback()
            return ServiceResponse.error_res(
                f"Error deleting credential: {str(e)}", "CRED_DELETE_ERROR"
            )

    @command(
        name="system.get_webhook_url",
        description="Returns the webhook URL and Verify Token for a specific service.",
        params_model={"service": "string"},
    )
    def get_webhook_url(
        self, session: Session, context: TenantContext, service: str
    ) -> ServiceResponse:
        try:
            # Get tenant secret
            result = (
                session.execute(
                    text("SELECT webhook_secret FROM tenants WHERE id = :tid"),
                    {"tid": context.tenant_id},
                )
                .mappings()
                .first()
            )

            if not result or not result["webhook_secret"]:
                return ServiceResponse.error_res(
                    "Tenant has no webhook secret configured.", "SECRET_NOT_FOUND"
                )

            webhook_url = f"{BASE_URL}/hooks/{result['webhook_secret']}/{service}"
            return ServiceResponse.success_res(
                data={"url": webhook_url, "verify_token": result["webhook_secret"]},
                message="Webhook details generated successfully.",
            )
        except Exception as e:
            return ServiceResponse.error_res(
                f"Error generating webhook URL: {str(e)}", "URL_GEN_ERROR"
            )

    @command(
        name="system.set_credential",
        description="Sets or updates an API credential for a specific service account.",
        params_model={
            "service": "string",
            "account_alias": "string",
            "api_key": "string",
            "secret": "string",
            "metadata": "string",
        },
    )
    def set_credential(
        self,
        session: Session,
        context: TenantContext,
        service: str,
        account_alias: str,
        api_key: str,
        secret: str = None,
        metadata: str = None,
    ) -> ServiceResponse:
        try:
            logger.info(f"Intentando establecer credencial para tenant {context.tenant_id}, servicio {service}, alias {account_alias}")
            logger.info(f"API Key (parcial): {api_key[:5]}..., Secret: {secret}, Metadata: {metadata}")

            # Upsert credential for this tenant and account alias
            session.execute(
                text(
                    """
                    INSERT INTO credentials (service_name, account_alias, api_key, secret, metadata, tenant_id)
                    VALUES (:service, :alias, :key, :secret, :meta, :tid)
                    ON CONFLICT (tenant_id, service_name, account_alias) DO UPDATE
                    SET api_key = EXCLUDED.api_key, secret = EXCLUDED.secret, metadata = EXCLUDED.metadata
                """
                ),
                {
                    "service": service,
                    "alias": account_alias,
                    "key": api_key,
                    "secret": secret,
                    "meta": metadata,
                    "tid": context.tenant_id,
                },
            )

            # --- AUTO-CONFIGURACIÓN DE BOT DE WHATSAPP ---
            if service == 'whatsapp':
                logger.info(f"Configurando bot de WhatsApp automáticamente para alias {account_alias}")
                # 1. Asegurar configuración básica del Bot
                session.execute(
                    text(
                        """
                        INSERT INTO bot_settings (tenant_id, account_alias, bot_name, welcome_message, farewell_message, handoff_message, support_email, is_global_active)
                        VALUES (:tid, :alias, 'Asistente Virtual', '¡Hola! Bienvenido. 🤖 Soy tu asistente virtual. ¿En qué puedo ayudarte hoy?', 
                                'Gracias por contactarnos. ¡Que tengas un gran día! 👋', 'He desactivado el bot. Un agente humano se pondrá en contacto contigo en breve. 👨‍💻', 
                                'soporte@negocio.com', TRUE)
                        ON CONFLICT (tenant_id, account_alias) DO NOTHING
                        """
                    ),
                    {"tid": context.tenant_id, "alias": account_alias},
                )

                # 2. Asegurar Nodo de Inicio básico
                session.execute(
                    text(
                        """
                        INSERT INTO bot_nodes (tenant_id, account_alias, name, prompt)
                        VALUES (:tid, :alias, 'inicio', 'Hola, ¿en qué puedo ayudarte?')
                        ON CONFLICT (tenant_id, account_alias, name) DO NOTHING
                        """
                    ),
                    {"tid": context.tenant_id, "alias": account_alias},
                )

            session.commit()
            logger.info(f"Credenciales y bot (si aplica) configurados exitosamente para {service} ({account_alias}).")
            return ServiceResponse.success_res(
                message=f"Credentials for {service} ({account_alias}) updated successfully and bot configured."
            )
        except Exception as e:
            session.rollback()
            logger.error(f"Error al establecer credencial para {service} ({account_alias}): {str(e)}", exc_info=True)
            return ServiceResponse.error_res(
                f"Error setting credential: {str(e)}", "CRED_SET_ERROR"
            )

    @command(
        name="system.get_credential",
        description="Retrieves a credential for a specific service account.",
        params_model={"service": "string", "account_alias": "string"},
    )
    def get_credential(
        self,
        session: Session,
        context: TenantContext,
        service: str,
        account_alias: str,
    ) -> ServiceResponse:
        try:
            result = (
                session.execute(
                    text(
                        "SELECT api_key, secret, metadata FROM credentials WHERE service_name = :service AND account_alias = :alias AND tenant_id = :tid"
                    ),
                    {
                        "service": service,
                        "alias": account_alias,
                        "tid": context.tenant_id,
                    },
                )
                .mappings()
                .first()
            )

            if not result:
                return ServiceResponse.error_res(
                    f"No credentials found for {service} ({account_alias})",
                    "CRED_NOT_FOUND",
                )
            return ServiceResponse.success_res(
                data=dict(result), message="Credential retrieved."
            )
        except Exception as e:
            return ServiceResponse.error_res(
                f"Error fetching credential: {str(e)}", "CRED_GET_ERROR"
            )


credentials_commands = CredentialsCommandHandler()
