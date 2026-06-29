from permissions_matrix import ACCESS_MATRIX, MODULE_DEFINITIONS


def handle_get_layout_manifest(params):
    """
    Lógica del comando system.get_layout_manifest
    """
    role = params.get("role", "employee")

    if role not in ACCESS_MATRIX:
        return {"error": "Rol no válido"}, 400

    allowed_modules = ACCESS_MATRIX[role]

    # 1. Generar Hub
    hub = []
    for mod_id in allowed_modules:
        if mod_id in MODULE_DEFINITIONS:
            hub.append(
                {
                    "id": mod_id,
                    "icon": MODULE_DEFINITIONS[mod_id]["icon"],
                    "label": MODULE_DEFINITIONS[mod_id]["label"],
                }
            )

    # 2. Generar Configuración de Módulos (Dock y Menú)
    modules_config = {}
    for mod_id, allowed_panels in allowed_modules.items():
        if mod_id not in MODULE_DEFINITIONS:
            continue

        mod_def = MODULE_DEFINITIONS[mod_id]

        dock = []
        for panel_id in allowed_panels:
            if panel_id in mod_def["panels"]:
                panel_def = mod_def["panels"][panel_id]
                dock.append(
                    {"id": panel_id, "icon": panel_def["icon"], "label": panel_def["label"]}
                )

        modules_config[mod_id] = {
            "dock": dock,
            "menu": [],  # Expandible según sea necesario
        }

    return {
        "user": {"role": role, "name": f"Usuario Demo {role.capitalize()}"},
        "hub": hub,
        "modules": modules_config,
    }, 200
