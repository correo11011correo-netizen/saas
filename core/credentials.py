import logging
import os

from sqlalchemy import text
from sqlalchemy.orm import Session

from core.context import TenantContext
from core.decorators import command
from core.types import ServiceResponse

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
    def list_credentials(self, session: Session, context: TenantContext) -> ServiceResponse:
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
            logger.info(
                f"Intentando establecer credencial para tenant {context.tenant_id}, servicio {service}, alias {account_alias}"
            )

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

            session.commit()
            logger.info(f"Credenciales configuradas exitosamente para {service} ({account_alias}).")
            return ServiceResponse.success_res(
                message=f"Credentials for {service} ({account_alias}) updated successfully."
            )
        except Exception as e:
            session.rollback()
            logger.error(
                f"Error al establecer credencial para {service} ({account_alias}): {str(e)}",
                exc_info=True,
            )
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
            return ServiceResponse.success_res(data=dict(result), message="Credential retrieved.")
        except Exception as e:
            return ServiceResponse.error_res(
                f"Error fetching credential: {str(e)}", "CRED_GET_ERROR"
            )


credentials_commands = CredentialsCommandHandler()
