import logging

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger("OmniCore.PanelSeeder")


def seed_ui_panels(session: Session):
    """
    Carga los paneles básicos del sistema.
    Es idempotente: usa ON CONFLICT para no duplicar datos.
    """
    logger.info("🌱 Sincronizando paneles básicos de UI...")

    initial_panels = [
        {
            "panel_id": "core.profile",
            "name": "Mi Perfil",
            "config_json": {"icon": "user", "color": "blue"},
            "required_role": None,
            "priority": "10",
        },
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

    for p in initial_panels:
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
    logger.info(f"✅ Sincronización de {len(initial_panels)} paneles completada.")
