from typing import Any, List, Optional, Dict
from uuid import UUID, uuid4
from motor.application.state import state
from motor.domain.entities import User
from motor.infrastructure.providers.base import BaseProvider

class StaffService:
    """
    Servicio de Staff: Gestión de empleados, permisos dinámicos y metas.
    Sustituye a EmployeeCommandHandler y EmployeeEngine.
    """

    def __init__(self):
        self.state = state

    def _get_provider(self, name: str) -> BaseProvider:
        provider = self.state.get_provider(name)
        if not provider:
            raise Exception(f"Provider '{name}' not connected.")
        return provider

    def define_business_term(self, tenant_id: UUID, def_type: str, key: str, label: str):
        if def_type not in ["permission", "goal_type", "task"]:
            raise ValueError("Invalid definition type")
            
        def_provider = self._get_provider("business_definitions")
        # Lógica de Upsert
        definition = def_provider.get(key, tenant_id)
        if definition:
            definition.label = label
        else:
            from motor.domain.entities import BusinessDefinition
            definition = BusinessDefinition(
                tenant_id=tenant_id,
                def_type=def_type,
                def_key=key,
                def_label=label
            )
        return def_provider.save(definition)

    def create_employee(self, tenant_id: UUID, name: str, role: str, emp_type: str, user_id: Optional[UUID] = None, bot_id: Optional[UUID] = None):
        if emp_type not in ["human", "bot"]:
            raise ValueError("Employee type must be human or bot")
            
        emp_provider = self._get_provider("employees")
        employee = Employee(
            tenant_id=tenant_id,
            name=name,
            role=role,
            type=emp_type,
            user_id=user_id,
            bot_profile_id=bot_id
        )
        return emp_provider.save(employee)

    def set_permission(self, employee_id: UUID, permission_key: str, granted: bool):
        def_provider = self._get_provider("business_definitions")
        emp_provider = self._get_provider("employees")
        
        # 1. Validar que el permiso existe para el tenant
        employee = emp_provider.get(employee_id)
        if not employee:
            raise ValueError("Employee not found")
            
        definition = def_provider.get(permission_key, employee.tenant_id)
        if not definition or definition.def_type != "permission":
            raise ValueError(f"Permission {permission_key} not defined for this business")

        # 2. Asignar permiso
        perm_provider = self._get_provider("employee_permissions")
        permission = EmployeePermission(
            employee_id=employee_id,
            permission_key=permission_key,
            granted=granted
        )
        return perm_provider.save(permission)

    def record_achievement(self, employee_id: UUID, amount: float, goal_type: str):
        emp_provider = self._get_provider("employees")
        def_provider = self._get_provider("business_definitions")
        
        employee = emp_provider.get(employee_id)
        definition = def_provider.get(goal_type, employee.tenant_id)
        
        if not definition or definition.def_type != "goal_type":
            raise ValueError(f"Goal type {goal_type} not defined")

        goal_provider = self._get_provider("employee_goals")
        goal = goal_provider.get_active_goal(employee_id, goal_type)
        if goal:
            goal.current_value += amount
            goal_provider.save(goal)

# Singleton instance
staff_service = StaffService()
