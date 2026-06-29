from permissions_mock import ACCESS_MATRIX, MODULE_DEFINITIONS


def generate_layout_manifest(user_role):
    """
    Genera el JSON de configuración de la UI basado en el rol del usuario.
    """
    # Si el rol no existe en la matriz, devolvemos un layout mínimo de seguridad
    if user_role not in ACCESS_MATRIX:
        return {"user": {"role": "guest", "name": "Invitado"}, "hub": [], "modules": {}}

    allowed_modules = ACCESS_MATRIX[user_role]

    # 1. Construir el Hub (Iconos principales)
    hub = []
    for mod_id in allowed_modules:
        # Solo agregamos al hub si el módulo tiene al menos un panel permitido
        # o si es un módulo base.
        if mod_id in MODULE_DEFINITIONS:
            hub.append(
                {
                    "id": mod_id,
                    "icon": MODULE_DEFINITIONS[mod_id]["icon"],
                    "label": MODULE_DEFINITIONS[mod_id]["label"],
                }
            )

    # 2. Construir la estructura de Módulos (Dock y Menú)
    modules_config = {}
    for mod_id, allowed_panels in allowed_modules.items():
        if mod_id not in MODULE_DEFINITIONS:
            continue

        mod_def = MODULE_DEFINITIONS[mod_id]

        # Construir el Dock (Botones de acción rápida)
        dock = []
        for panel_id in allowed_panels:
            if panel_id in mod_def["panels"]:
                panel_def = mod_def["panels"][panel_id]
                dock.append(
                    {"id": panel_id, "icon": panel_def["icon"], "label": panel_def["label"]}
                )

        # En este PoC, el menú se mantiene simple o vacío
        menu = []
        if mod_id == "user":
            menu.append({"id": "logout", "icon": "log-out", "label": "Cerrar Sesión"})

        modules_config[mod_id] = {"dock": dock, "menu": menu}

    return {
        "user": {"role": user_role, "name": f"Usuario {user_role.capitalize()}"},
        "hub": hub,
        "modules": modules_config,
    }
