import logging

from sqlalchemy import text

from db_engine.core.engine import nexus_db

logger = logging.getLogger("OmniCore.PanelSeed")


def seed_initial_panels():
    """
    Carga los paneles básicos del sistema para evitar que la app inicie vacía.
    """
    logger.info("🌱 Seeding initial UI panels...")

    initial_panels = [
        # --- PANELES GLOBALES (Para todos) ---
        {
            "panel_id": "core.profile",
            "name": "Mi Perfil",
            "config_json": {"icon": "user", "color": "blue"},
            "required_role": None,
            "priority": "10",
        },
        # --- PANELES DE EMPLEADO/ADMIN ---
        {
            "panel_id": "sales.pos",
            "name": "Punto de Venta",
            "config_json": {"icon": "shopping_cart", "color": "green"},
            "required_role": "employee",
            "priority": "1",
        },
        {
            "panel_id": "stock.inventory",
            "name": "Inventario",
            "config_json": {"icon": "box", "color": "orange"},
            "required_role": "employee",
            "priority": "2",
        },
        # --- PANELES DE DUEÑO (ADMIN) ---
        {
            "panel_id": "admin.dashboard",
            "name": "Panel de Control",
            "config_json": {"icon": "insights", "color": "purple"},
            "required_role": "admin",
            "priority": "1",
        },
        {
            "panel_id": "admin.staff",
            "name": "Gestión de Personal",
            "config_json": {"icon": "group", "color": "indigo"},
            "required_role": "admin",
            "priority": "2",
        },
        # --- PANELES DE SOPORTE ---
        {
            "panel_id": "support.clients",
            "name": "Clientes",
            "config_json": {"icon": "business", "color": "teal"},
            "required_role": "support",
            "priority": "1",
        },
        {
            "panel_id": "support.bots",
            "name": "Diagnóstico Bots",
            "config_json": {"icon": "bug_report", "color": "red"},
            "required_role": "support",
            "priority": "2",
        },
        # --- PANELES DE SUPERADMIN (Tú) ---
        {
            "panel_id": "saas.tenants",
            "name": "Gestión SaaS",
            "config_json": {"icon": "admin_panel_settings", "color": "black"},
            "required_role": "superadmin",
            "priority": "1",
        },
        {
            "panel_id": "saas.panels",
            "name": "Configurador de UI",
            "config_json": {"icon": "palette", "color": "pink"},
            "required_role": "superadmin",
            "priority": "2",
        },
    ]

    with nexus_db.session() as session:
        for p in initial_panels:
            # Usamos ON CONFLICT para no duplicar en reinicios
            session.execute(
                text("""
                    INSERT INTO panel_definitions (panel_id, name, config_json, required_role, priority)
                    VALUES (:pid, :name, :conf, :role, :prio)
                    ON CONFLICT (panel_id) DO UPDATE SET
                        name = EXCLUDED.name,
                        config_json = EXCLUDED.config_json,
                        required_role = EXCLUDED.required_role,
                        priority = EXCLUDED.priority
                """),
                {
                    "pid": p["panel_id"],
                    "name": p["name"],
                    "conf": p["config_json"],
                    "role": p["required_role"],
                    "prio": p["priority"],
                },
            )
        session.commit()
        logger.info(f"✅ Successfully seeded {len(initial_panels)} base panels.")


if __name__ == "__main__":
    seed_initial_panels()
