import datetime
import logging
import uuid

from sqlalchemy.orm import Session

from core.context import TenantContext
from core.decorators import command
from core.types import ServiceResponse
from core.data_commands import data_commands
from employees.engine import employee_engine

logger = logging.getLogger("OmniCore.EmployeeCommands")


class EmployeeCommandHandler:
    """
    Gestión Administrativa de OmniStaff.
    CONFIGURACIÓN TOTAL. Permite definir el negocio antes de asignar empleados.
    """

    @command(
        name="staff.define_business_term",
        description="Defines a custom term (permission, goal_type, or task) for the business.",
        params_model={"def_type": "string", "def_key": "string", "def_label": "string"},
    )
    def define_term(
        self, session: Session, context: TenantContext, def_type: str, def_key: str, def_label: str
    ) -> ServiceResponse:
        try:
            if def_type not in ["permission", "goal_type", "task"]:
                return ServiceResponse.error_res(
                    "Invalid type. Must be 'permission', 'goal_type', or 'task'.", "INVALID_TYPE"
                )

            res = data_commands.upsert_data(
                session, 
                context, 
                entity="business_definitions", 
                conflict_keys=["tenant_id", "def_type", "def_key"], 
                data={"def_type": def_type, "def_key": def_key, "def_label": def_label}, 
                update_columns=["def_label"]
            )
            if not res.success:
                return res

            return ServiceResponse.success_res(
                message=f"Term {def_label} ({def_type}) defined successfully."
            )
        except Exception as e:
            session.rollback()
            return ServiceResponse.error_res(str(e), "DEF_TERM_ERROR")

    @command(
        name="staff.create",
        description="Creates an employee record (Human or Bot).",
        params_model={
            "name": "string",
            "role": "string",
            "type": "string",
            "user_id": "string",
            "bot_profile_id": "string",
        },
    )
    def create_employee(
        self,
        session: Session,
        context: TenantContext,
        name: str,
        role: str,
        type: str,
        user_id: str = None,
        bot_profile_id: str = None,
    ) -> ServiceResponse:
        try:
            if type not in ["human", "bot"]:
                return ServiceResponse.error_res(
                    "Invalid type. Must be 'human' or 'bot'.", "INVALID_TYPE"
                )

            employee_id = uuid.uuid4()
            res = data_commands.insert_data(
                session, 
                context, 
                entity="employees", 
                data={
                    "id": employee_id, 
                    "user_id": uuid.UUID(user_id) if user_id else None, 
                    "bot_profile_id": uuid.UUID(bot_profile_id) if bot_profile_id else None, 
                    "name": name, 
                    "role": role, 
                    "type": type
                }
            )
            if not res.success:
                return res

            return ServiceResponse.success_res(
                data={"employee_id": str(employee_id)},
                message=f"Employee {name} created successfully as {type}.",
            )
        except Exception as e:
            session.rollback()
            return ServiceResponse.error_res(str(e), "STAFF_CREATE_ERROR")

    @command(
        name="staff.set_permission",
        description="Grants or revokes a specific permission for an employee.",
        params_model={"employee_id": "string", "permission_key": "string", "granted": "boolean"},
    )
    def set_permission(
        self,
        session: Session,
        context: TenantContext,
        employee_id: str,
        permission_key: str,
        granted: bool,
    ) -> ServiceResponse:
        try:
            # Validar que el empleado existe y obtener su tenant_id
            emp_res = data_commands.query_data(
                session, context, entity="employees", filters={"id": employee_id}
            )
            if not emp_res.success or not emp_res.data:
                return ServiceResponse.error_res("Employee not found", "EMPLOYEE_NOT_FOUND")
            
            tenant_id = emp_res.data[0]["tenant_id"]

            # Validar que el permiso existe en las definiciones del negocio
            def_res = data_commands.query_data(
                session, 
                context, 
                entity="business_definitions", 
                filters={"def_type": "permission", "def_key": permission_key}
            )

            if not def_res.success or not def_res.data:
                return ServiceResponse.error_res(
                    f"Permission '{permission_key}' is not defined for this business. Use 'staff.define_business_term' first.",
                    "UNDEFINED_PERMISSION",
                )

            # Upsert del permiso
            res = data_commands.upsert_data(
                session, 
                context, 
                entity="employee_permissions", 
                conflict_keys=["employee_id", "permission_key"], 
                data={"employee_id": uuid.UUID(employee_id), "permission_key": permission_key, "granted": granted}, 
                update_columns=["granted"]
            )
            if not res.success:
                return res

            return ServiceResponse.success_res(
                message=f"Permission {permission_key} updated for employee."
            )
        except Exception as e:
            session.rollback()
            return ServiceResponse.error_res(str(e), "PERM_SET_ERROR")

    @command(
        name="staff.set_goal",
        description="Sets a performance goal for an employee.",
        params_model={
            "employee_id": "string",
            "goal_type": "string",
            "target": "float",
            "start_date": "string",
            "end_date": "string",
        },
    )
    def set_goal(
        self,
        session: Session,
        context: TenantContext,
        employee_id: str,
        goal_type: str,
        target: float,
        start_date: str,
        end_date: str,
    ) -> ServiceResponse:
        try:
            # Validar que el empleado existe y obtener su tenant_id
            emp_res = data_commands.query_data(
                session, context, entity="employees", filters={"id": employee_id}
            )
            if not emp_res.success or not emp_res.data:
                return ServiceResponse.error_res("Employee not found", "EMPLOYEE_NOT_FOUND")
            
            tenant_id = emp_res.data[0]["tenant_id"]

            # Validar que el tipo de meta existe en las definiciones del negocio
            def_res = data_commands.query_data(
                session, 
                context, 
                entity="business_definitions", 
                filters={"def_type": "goal_type", "def_key": goal_type}
            )

            if not def_res.success or not def_res.data:
                return ServiceResponse.error_res(
                    f"Goal type '{goal_type}' is not defined for this business. Use 'staff.define_business_term' first.",
                    "UNDEFINED_GOAL",
                )

            # Insertar la meta
            res = data_commands.insert_data(
                session, 
                context, 
                entity="employee_goals", 
                data={
                    "employee_id": uuid.UUID(employee_id), 
                    "goal_type": goal_type, 
                    "target_value": target, 
                    "start_date": datetime.date.fromisoformat(start_date), 
                    "end_date": datetime.date.fromisoformat(end_date)
                }
            )
            if not res.success:
                return res

            return ServiceResponse.success_res(message="Performance goal set successfully.")
        except Exception as e:
            session.rollback()
            return ServiceResponse.error_res(str(e), "GOAL_SET_ERROR")

    @command(
        name="staff.report",
        description="Retrieves the general performance report for all staff.",
        params_model={},
    )
    def get_report(self, session: Session, context: TenantContext) -> ServiceResponse:
        try:
            report = employee_engine.get_performance_report(session, context.tenant_id)
            return ServiceResponse.success_res(
                data=report, message="Staff performance report retrieved."
            )
        except Exception as e:
            session.rollback()
            return ServiceResponse.error_res(str(e), "REPORT_ERROR")


employee_commands = EmployeeCommandHandler()
