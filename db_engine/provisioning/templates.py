from typing import Any

# Definiciones de "Blueprints" para diferentes niveles de plan.
# Esto permite que el sistema crezca sin cambiar el código de creación,
# solo añadiendo nuevas plantillas aquí.

PLAN_BLUEPRINTS = {
    "free": {
        "capabilities": {
            "can_sell": True,
            "can_manage_stock": True,
            "can_process_payments": False,
            "custom_panels": False,
            "advanced_bots": False,
        },
        "bot_config": {
            "welcome_message": "Hola! Bienvenido a nuestro catálogo. ¿En qué puedo ayudarte?",
            "farewell_message": "Gracias por contactarnos. ¡Que tengas un gran día!",
            "handoff_message": "Te estoy comunicando con un agente humano. Por favor espera.",
        },
        "initial_nodes": [
            {
                "name": "main_menu",
                "prompt": """Selecciona una opción:
1. Ver Catálogo
2. Hablar con Ventas
3. Horarios""",
            },
            {
                "name": "catalog",
                "prompt": "Aquí tienes nuestros productos disponibles. ¿Buscas algo en especial?",
            },
        ],
        "initial_options": [
            {"label": "1. Ver Catálogo", "node_id": "catalog", "action": "show_catalog"},
            {"label": "2. Hablar con Ventas", "node_id": "human", "action": "handoff"},
        ],
    },
    "pro": {
        "capabilities": {
            "can_sell": True,
            "can_manage_stock": True,
            "can_process_payments": True,
            "custom_panels": True,
            "advanced_bots": True,
        },
        "bot_config": {
            "welcome_message": "🌟 Bienvenido al servicio Premium. ¿Cómo podemos potenciar tu negocio hoy?",
            "farewell_message": "Gracias por confiar en nosotros. ¡Hasta pronto!",
            "handoff_message": "Un asesor especializado se unirá al chat en breve.",
        },
        "initial_nodes": [
            {
                "name": "main_menu",
                "prompt": """Menú Corporativo:
        1. Ventas y Pedidos
        2. Inventario
        3. Soporte Técnico
        4. Administración""",
            },
            {
                "name": "sales_hub",
                "prompt": "Centro de Ventas: Puedes realizar pedidos o consultar el estado de su envío.",
            },
        ],
        "initial_options": [
            {"label": "1. Ventas", "node_id": "sales_hub", "action": "start_sale"},
            {"label": "2. Inventario", "node_id": "stock_menu", "action": "manage_stock"},
        ],
    },
    "enterprise": {
        "capabilities": {
            "can_sell": True,
            "can_manage_stock": True,
            "can_process_payments": True,
            "custom_panels": True,
            "advanced_bots": True,
            "api_access": True,
            "multi_bot": True,
        },
        "bot_config": {
            "welcome_message": "Bienvenido al ecosistema Enterprise. Gestión automatizada activa.",
            "farewell_message": "Sesión finalizada. Gracias por usar nuestro sistema.",
            "handoff_message": "Sincronizando con el departamento correspondiente...",
        },
        "initial_nodes": [],  # Se configuran a medida por el equipo de despliegue
        "initial_options": [],
    },
}


def get_blueprint(plan_name: str) -> dict[str, Any]:
    """Retorna el blueprint para un plan dado, o el plan 'free' por defecto."""
    return PLAN_BLUEPRINTS.get(plan_name.lower(), PLAN_BLUEPRINTS["free"])
