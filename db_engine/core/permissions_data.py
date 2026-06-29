# Semilla de Permisos del Sistema
# Esta lista define todas las capacidades disponibles en la plataforma.
# Cualquier nuevo comando que requiera permisos debe ser añadido aquí.

SYSTEM_PERMISSIONS = [
    # Módulo de Ventas
    {"code": "sale.create", "description": "Puede crear nuevas ventas", "module": "sales"},
    {"code": "sale.edit", "description": "Puede editar ventas existentes", "module": "sales"},
    {"code": "sale.delete", "description": "Puede anular ventas", "module": "sales"},
    {
        "code": "sale.view_revenue",
        "description": "Puede ver reportes de ingresos",
        "module": "sales",
    },
    # Módulo de Stock
    {"code": "stock.manage", "description": "Puede crear y editar productos", "module": "stock"},
    {
        "code": "stock.update_qty",
        "description": "Puede ajustar cantidades de stock",
        "module": "stock",
    },
    {"code": "stock.import", "description": "Puede cargar stock masivamente", "module": "stock"},
    # Módulo de Bots
    {"code": "bot.configure", "description": "Puede editar el flujo del bot", "module": "bots"},
    {"code": "bot.view_logs", "description": "Puede ver conversaciones del bot", "module": "bots"},
    # Administración
    {
        "code": "admin.manage_users",
        "description": "Puede crear y editar empleados",
        "module": "admin",
    },
    {
        "code": "admin.change_plan",
        "description": "Puede cambiar el plan del tenant",
        "module": "admin",
    },
]

# Mapeo de Permisos por Plan
PLAN_PERMISSIONS_MAP = {
    "free": ["sale.create", "stock.update_qty", "bot.configure"],
    "pro": [
        "sale.create",
        "sale.edit",
        "sale.view_revenue",
        "stock.manage",
        "stock.update_qty",
        "stock.import",
        "bot.configure",
        "bot.view_logs",
        "admin.manage_users",
    ],
    "enterprise": [
        "sale.create",
        "sale.edit",
        "sale.delete",
        "sale.view_revenue",
        "stock.manage",
        "stock.update_qty",
        "stock.import",
        "bot.configure",
        "bot.view_logs",
        "admin.manage_users",
        "admin.change_plan",
    ],
}
