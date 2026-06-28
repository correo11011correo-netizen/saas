import logging
from typing import Any, Dict, List, Optional
from sqlalchemy import text
from sqlalchemy.orm import Session
from core.types import ServiceResponse
from core.context import TenantContext
import uuid
import datetime

logger = logging.getLogger("OmniCore.EmployeeEngine")

class EmployeeEngine:
    """
    Motor Orquestador de Empleados (OmniStaff).
    CERO HARDCODING. Todo se basa en 'business_definitions' creadas por el Tenant.
    """
    
    def check_permission(self, session: Session, employee_id: uuid.UUID, permission_key: str) -> bool:
        """
        Verifica si un empleado tiene un permiso concedido. 
        El 'permission_key' debe existir primero en business_definitions para ese tenant.
        """
        # 1. Verificar que el permiso existe para el tenant del empleado
        tenant_id = session.execute(
            text("SELECT tenant_id FROM employees WHERE id = :eid"), {"eid": employee_id}
        ).scalar()
        
        definition = session.execute(
            text("SELECT 1 FROM business_definitions WHERE tenant_id = :tid AND def_type = 'permission' AND def_key = :key"),
            {"tid": tenant_id, "key": permission_key}
        ).first()
        
        if not definition:
            logger.warning(f"Permission key {permission_key} not defined for tenant {tenant_id}")
            return False

        # 2. Verificar si el empleado tiene el permiso asignado
        result = session.execute(
            text("SELECT granted FROM employee_permissions WHERE employee_id = :eid AND permission_key = :key"),
            {"eid": employee_id, "key": permission_key}
        ).mappings().first()
        
        return result["granted"] if result else False

    def record_achievement(self, session: Session, employee_id: uuid.UUID, amount: float, goal_type: str):
        """
        Suma progreso a los objetivos activos.
        El 'goal_type' debe estar definido en business_definitions.
        """
        tenant_id = session.execute(
            text("SELECT tenant_id FROM employees WHERE id = :eid"), {"eid": employee_id}
        ).scalar()

        definition = session.execute(
            text("SELECT 1 FROM business_definitions WHERE tenant_id = :tid AND def_type = 'goal_type' AND def_key = :key"),
            {"tid": tenant_id, "key": goal_type}
        ).first()

        if not definition:
            logger.error(f"Goal type {goal_type} not defined for tenant {tenant_id}")
            return

        today = datetime.date.today()
        session.execute(
            text(
                """
                UPDATE employee_goals 
                SET current_value = current_value + :amount 
                WHERE employee_id = :eid AND goal_type = :type 
                AND start_date <= :today AND end_date >= :today
                """
            ),
            {"amount": amount, "eid": employee_id, "type": goal_type, "today": today}
        )

    def get_performance_report(self, session: Session, tenant_id: uuid.UUID) -> List[Dict]:
        """
        Reporte dinámico basado en las definiciones del negocio.
        """
        query = """
            SELECT e.id, e.name, e.type, e.role, 
                   COALESCE(SUM(eg.current_value), 0) as total_progress,
                   COALESCE(SUM(eg.target_value), 0) as total_target
            FROM employees e
            LEFT JOIN employee_goals eg ON e.id = eg.employee_id
            WHERE e.tenant_id = :tid
            GROUP BY e.id, e.name, e.type, e.role
        """
        result = session.execute(text(query), {"tid": tenant_id}).mappings().all()
        return [dict(row) for row in result]

employee_engine = EmployeeEngine()
