import logging
import os

from sqlalchemy.orm import Session

from core.context import TenantContext
from core.decorators import command
from core.types import ServiceResponse
from core.data_commands import data_commands

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
            res = data_commands.query_data(
                session, context, entity="credentials"
            )
            if not res.success:
                return res
            
            return ServiceResponse.success_res(
                data=res.data,
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
            # Buscar el ID de la credencial primero
            res_id = data_commands.query_data(
                session, 
                context, 
                entity="credentials", 
                filters={"service_name": service, "account_alias": account_alias}
            )
            if not res_id.success or not res_id.data:
                return ServiceResponse.error_res("Credential not found", "CRED_NOT_FOUND")
            
            cred_id = res_id.data[0]["id"]
            del_res = data_commands.delete_data(
                session, context, entity="credentials", record_id=cred_id
            )
            if not del_res.success:
                return del_res

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
            res_tenant = data_commands.query_data(
                session, context, entity="tenants", filters={"id": context.tenant_id}
            )

            if not res_tenant.success or not res_tenant.data:
                return ServiceResponse.error_res(
                    "Tenant not found.", "TENANT_NOT_FOUND"
                )
            
            tenant = res_tenant.data[0]
            secret = tenant.get("webhook_secret")

            if not secret:
                return ServiceResponse.error_res(
                    "Tenant has no webhook secret configured.", "SECRET_NOT_FOUND"
                )

            webhook_url = f"{BASE_URL}/hooks/{secret}/{service}"
            return ServiceResponse.success_res(
                data={"url": webhook_url, "verify_token": secret},
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

            # Check if exists for Upsert logic
            res_exists = data_commands.query_data(
                session, 
                context, 
                entity="credentials", 
                filters={"service_name": service, "account_alias": account_alias}
            )

            cred_data = {
                "service_name": service,
                "account_alias": account_alias,
                "api_key": api_key,
                "secret": secret,
                "metadata": metadata,
                "tenant_id": context.tenant_id,
            }

            if res_exists.success and res_exists.data:
                # Update existing
                cred_id = res_exists.data[0]["id"]
                data_commands.patch_data(
                    session, context, entity="credentials", record_id=cred_id, updates=cred_data
                )
            else:
                # Insert new
                data_commands.insert_data(
                    session, context, entity="credentials", data=cred_data
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
            res = data_commands.query_data(
                session, 
                context, 
                entity="credentials", 
                filters={"service_name": service, "account_alias": account_alias}
            )

            if not res.success or not res.data:
                return ServiceResponse.error_res(
                    f"No credentials found for {service} ({account_alias})",
                    "CRED_NOT_FOUND",
                )
            
            cred = res.data[0]
            return ServiceResponse.success_res(
                data={
                    "api_key": cred.get("api_key"), 
                    "secret": cred.get("secret"), 
                    "metadata": cred.get("metadata")
                }, 
                message="Credential retrieved."
            )
        except Exception as e:
            return ServiceResponse.error_res(
                f"Error fetching credential: {str(e)}", "CRED_GET_ERROR"
            )


credentials_commands = CredentialsCommandHandler()
