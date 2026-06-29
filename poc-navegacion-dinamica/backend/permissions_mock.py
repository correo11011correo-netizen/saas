# Matriz de Permisos Mock
# Este archivo define qué roles tienen acceso a qué módulos y paneles.

ROLES = {"SUPER_ADMIN": "superadmin", "OWNER": "owner", "EMPLOYEE": "employee"}

# Definición de módulos y sus paneles disponibles
# Cada panel tiene un id, un icono y una etiqueta.
MODULE_DEFINITIONS = {
    "stock": {
        "label": "Stock",
        "icon": "box",
        "panels": {
            "inventory": {"label": "Inventario", "icon": "list"},
            "pos": {"label": "Cobrar (POS)", "icon": "shopping-cart"},
            "load": {"label": "Carga Masiva", "icon": "upload"},
            "reports": {"label": "Reportes Stock", "icon": "chart-bar"},
        },
    },
    "whatsapp": {
        "label": "WhatsApp",
        "icon": "whatsapp",
        "panels": {
            "chats": {"label": "Mensajes", "icon": "message-circle"},
            "bot_config": {"label": "Configurar Bot", "icon": "settings"},
            "broadcast": {"label": "Envío Masivo", "icon": "send"},
        },
    },
    "system": {
        "label": "Sistema",
        "icon": "cpu",
        "panels": {
            "billing": {"label": "Facturación", "icon": "credit-card"},
            "tenants": {"label": "Gestión de Clientes", "icon": "users"},
            "logs": {"label": "Logs del Sistema", "icon": "terminal"},
        },
    },
    "user": {
        "label": "Mi Perfil",
        "icon": "user",
        "panels": {
            "profile": {"label": "Perfil", "icon": "user-check"},
            "permissions": {"label": "Mis Permisos", "icon": "shield"},
        },
    },
}

# Matriz de Acceso: Define qué paneles puede ver cada rol
# Si un módulo no está en la lista del rol, el módulo entero desaparece del Hub.
# Si un panel no está en la lista del módulo, el botón desaparece del Dock.
ACCESS_MATRIX = {
    ROLES["SUPER_ADMIN"]: {
        "stock": ["inventory", "pos", "load", "reports"],
        "whatsapp": ["chats", "bot_config", "broadcast"],
        "system": ["billing", "tenants", "logs"],
        "user": ["profile", "permissions"],
    },
    ROLES["OWNER"]: {
        "stock": ["inventory", "pos", "load", "reports"],
        "whatsapp": ["chats", "bot_config", "broadcast"],
        "system": [],  # El dueño no accede a gestión de tenants global
        "user": ["profile", "permissions"],
    },
    ROLES["EMPLOYEE"]: {
        "stock": ["inventory", "pos"],  # No puede cargar stock ni ver reportes
        "whatsapp": ["chats"],  # Solo puede chatear, no configurar bot
        "system": [],
        "user": ["profile"],  # Solo ve su perfil, no sus permisos
    },
}
