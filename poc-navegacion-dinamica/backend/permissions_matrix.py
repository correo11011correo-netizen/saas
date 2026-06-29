# Matriz de Permisos Realista
# Basada en el análisis del frontend actual.

ROLES = {"SUPER_ADMIN": "superadmin", "OWNER": "owner", "EMPLOYEE": "employee"}

# Definición completa de módulos y paneles (Lo que antes estaba en los .config de los módulos)
MODULE_DEFINITIONS = {
    "stock": {
        "label": "Gestión de Stock",
        "icon": "box",
        "panels": {
            "inventory": {"label": "Inventario", "icon": "list"},
            "pos": {"label": "Cobrar (POS)", "icon": "shopping-cart"},
            "load": {"label": "Carga Masiva", "icon": "upload"},
            "reports": {"label": "Reportes de Ventas", "icon": "bar-chart"},
        },
    },
    "whatsapp": {
        "label": "WhatsApp Bot",
        "icon": "message-square",
        "panels": {
            "chats": {"label": "Conversaciones", "icon": "message-circle"},
            "bot_config": {"label": "Configuración Bot", "icon": "settings"},
            "broadcast": {"label": "Envío Masivo", "icon": "send"},
        },
    },
    "bot_manager": {
        "label": "Bot Manager",
        "icon": "cpu",
        "panels": {
            "scripts": {"label": "Scripts de Respuesta", "icon": "code"},
            "webhooks": {"label": "Webhooks", "icon": "link"},
            "logs": {"label": "Logs de Bot", "icon": "terminal"},
        },
    },
    "profile": {
        "label": "Mi Perfil",
        "icon": "user",
        "panels": {
            "settings": {"label": "Ajustes de Cuenta", "icon": "user-cog"},
            "permissions": {"label": "Gestión de Permisos", "icon": "shield-check"},
        },
    },
}

# Matriz de Acceso: El corazón de la navegación dinámica
ACCESS_MATRIX = {
    ROLES["SUPER_ADMIN"]: {
        "stock": ["inventory", "pos", "load", "reports"],
        "whatsapp": ["chats", "bot_config", "broadcast"],
        "bot_manager": ["scripts", "webhooks", "logs"],
        "profile": ["settings", "permissions"],
    },
    ROLES["OWNER"]: {
        "stock": ["inventory", "pos", "load", "reports"],
        "whatsapp": ["chats", "bot_config", "broadcast"],
        "bot_manager": ["scripts", "webhooks"],
        "profile": ["settings", "permissions"],
    },
    ROLES["EMPLOYEE"]: {
        "stock": ["inventory", "pos"],  # No carga masiva ni reportes
        "whatsapp": ["chats"],  # Solo chatear
        "bot_manager": [],  # Sin acceso al manager
        "profile": ["settings"],  # Sin acceso a gestión de permisos
    },
}
