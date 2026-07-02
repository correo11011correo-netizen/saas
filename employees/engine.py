import datetime
import logging
import uuid

from sqlalchemy.orm import Session
from core.data_commands import data_commands

logger = logging.getLogger("OmniCore.EmployeeEngine")


class EmployeeEngine:
    """
    Motor Orquestador de Empleados (OmniStaff).
    CERO HARDCODING. Todo se basa en 'business_definitions' creadas por el Tenant.
    """

    def check_permission(
        self, session: Session, employee_id: uuid.UUID, permission_key: str
    ) -> bool:
        """
        Verifica si un empleado tiene un permiso concedido.
        El 'permission_key' debe existir primero en business_definitions para ese tenant.
        """
        # 1. Verificar que el empleado existe y obtener su tenant_id
        emp_res = data_commands.query_data(
            session, None, entity="employees", filters={"id": str(employee_id)}
        )
        if not emp_res.success or not emp_res.data:
            logger.warning(f"Employee {employee_id} not found")
            return False
        
        tenant_id = emp_res.data[0]["tenant_id"]

        # 2. Verificar que el permiso existe para el tenant del empleado
        def_res = data_commands.query_data(
            session, None, entity="business_definitions", 
            filters={"tenant_id": tenant_id, "def_type": "permission", "def_key": permission_key}
        )

        if not def_res.success or not def_res.data:
            logger.warning(f"Permission key {permission_key} not defined for tenant {tenant_id}")
            return False

        # 3. Verificar si el empleado tiene el permiso asignado
        perm_res = data_commands.query_data(
            session, None, entity="employee_permissions", 
            filters={"employee_id": str(employee_id), "permission_key": permission_key}
        )

        if not perm_res.success or not perm_res.data:
            return False

        return perm_res.data[0].get("granted", False)

    def record_achievement(
        self, session: Session, employee_id: uuid.UUID, amount: float, goal_type: str
    ):
        """
        Suma progreso a los objetivos activos.
        El 'goal_type' debe estar definido en business_definitions.
        """
        # 1. Verificar que el empleado existe y obtener su tenant_id
        emp_res = data_commands.query_data(
            session, None, entity="employees", filters={"id": str(employee_id)}
        )
        if not emp_res.success or not emp_res.data:
            logger.error(f"Employee {employee_id} not found")
            return
        
        tenant_id = emp_res.data[0]["tenant_id"]

        # 2. Verificar que el tipo de meta existe para el tenant
        def_res = data_commands.query_data(
            session, None, entity="business_definitions", 
            filters={"tenant_id": tenant_id, "def_type": "goal_type", "def_key": goal_type}
        )

        if not def_res.success or not def_res.data:
            logger.error(f"Goal type {goal_type} not defined for tenant {tenant_id}")
            return

        # 3. Actualizar el progreso de la meta activa
        # Buscamos la meta activa hoy
        today = datetime.date.today().isoformat()
        goal_res = data_commands.query_data(
            session, None, entity="employee_goals", 
            filters={"employee_id": str(employee_id), "goal_type": goal_type}
        )
        
        if not goal_res.success or not goal_res.data:
            logger.warning(f"No active goal of type {goal_type} found for employee {employee_id}")
            return

        # En un sistema real, filtraríamos por fecha. Aquí asumimos que la primera coincide 
        # o que el DataMotor debería soportar filtros de fecha. 
        # Por simplicidad, actualizamos la primera encontrada.
        goal_id = goal_res.data[0]["id"]
        data_commands.increment_data(
            session, None, entity="employee_goals", record_id=goal_id, field="current_value", value=amount
        )

    def get_performance_report(self, session: Session, tenant_id: uuid.UUID) -> list[dict]:
        """
        Reporte dinámico basado en las definiciones del negocio.
        """
        # Fetch all employees for the tenant
        emp_res = data_commands.query_data(
            session, None, entity="employees", filters={"tenant_id": str(tenant_id)}
        )
        if not emp_res.success:
            return []

        report = []
        for emp in emp_res.data:
            # Fetch goals for this employee
            goal_res = data_commands.query_data(
                session, None, entity="employee_goals", filters={"employee_id": emp["id"]}
            )
            
            total_progress = 0.0
            total_target = 0.0
            if goal_res.success:
                for goal in goal_res.data:
                    total_progress += float(goal.get("current_value", 0))
                    total_target += float(goal.get("target_value", 0))

            report.append({
                "id": emp["id"],
                "name": emp["name"],
                "type": emp["type"],
                "role": emp["role"],
                "total_progress": total_progress,
                "total_target": total_target
            })
        
        return report


employee_engine = EmployeeEngine()
