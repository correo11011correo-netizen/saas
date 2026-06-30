from typing import Any

from sqlalchemy.orm import Session

from db_engine.provisioning.templates import get_blueprint
from db_engine.repositories.bot_repo import BotRepository
from db_engine.repositories.tenant_repo import TenantRepository
from whatsapp.models import BotNode, BotOption, BotProfile, BotSettings


class TenantProvisioner:
    """
    Orquestador de Onboarding.
    Se encarga de crear todo el ecosistema de un nuevo cliente en una sola transacción atómica.
    """

    def __init__(self, session: Session):
        self.session = session
        self.tenant_repo = TenantRepository(session)
        self.bot_repo = BotRepository(session)

    def provision_new_tenant(
        self, business_name: str, owner_email: str, owner_password_hash: str, plan: str = "free"
    ) -> dict[str, Any]:
        """
        Crea un Tenant y despliega su infraestructura básica basada en la plantilla del plan.
        """
        blueprint = get_blueprint(plan)

        try:
            # 1. Crear el Tenant
            tenant = self.tenant_repo.create(
                {
                    "name": business_name,
                    "status": "active",
                    "metadata_json": {
                        "plan": plan,
                        "onboarding_completed": False,
                        "panel_theme": "default",
                    },
                }
            )
            tenant_id = tenant.id

            # 2. Crear el Usuario Propietario (Admin)
            user = self.tenant_repo.create_user(
                {
                    "email": owner_email,
                    "password_hash": owner_password_hash,
                    "role": "admin",
                    "tenant_id": tenant_id,
                }
            )

            # 3. Crear Perfil de Bot
            bot_profile = BotProfile(
                tenant_id=tenant_id,
                name=f"Bot de {business_name}",
                capabilities=blueprint["capabilities"],
                is_active=True,
            )
            self.session.add(bot_profile)
            self.session.flush()

            # 4. Aplicar Ajustes del Bot
            bot_settings = BotSettings(
                tenant_id=tenant_id,
                bot_profile_id=bot_profile.id,
                welcome_message=blueprint["bot_config"]["welcome_message"],
                farewell_message=blueprint["bot_config"]["farewell_message"],
                handoff_message=blueprint["bot_config"]["handoff_message"],
            )
            self.session.add(bot_settings)

            # 5. Desplegar Nodos y Opciones Iniciales
            for node_data in blueprint["initial_nodes"]:
                node = BotNode(
                    tenant_id=tenant_id,
                    bot_profile_id=bot_profile.id,
                    name=node_data["name"],
                    prompt=node_data["prompt"],
                )
                self.session.add(node)
                self.session.flush()

                # Vincular opciones que apunten a este nodo (si existen en el blueprint)
                # Nota: En una implementación real, mapearíamos IDs dinámicamente.
                # Aquí simplificamos la lógica de plantillas.

            # 6. Crear Opciones del Bot
            for opt_data in blueprint["initial_options"]:
                # Buscar el ID del nodo destino basado en el nombre del blueprint
                target_node = (
                    self.session.query(BotNode)
                    .filter(BotNode.tenant_id == tenant_id, BotNode.name == opt_data["node_id"])
                    .first()
                )

                if target_node:
                    option = BotOption(
                        tenant_id=tenant_id,
                        node_id=target_node.id,
                        bot_profile_id=bot_profile.id,
                        label=opt_data["label"],
                        action=opt_data["action"],
                    )
                    self.session.add(option)

            self.session.flush()

            return {
                "status": "success",
                "tenant_id": tenant_id,
                "user_id": user.id,
                "bot_profile_id": bot_profile.id,
                "plan": plan,
            }

        except Exception as e:
            # El contexto de sesión del motor manejará el rollback,
            # pero aquí capturamos para reportar el error de provisionamiento.
            raise Exception(f"Provisioning failed: {str(e)}")
