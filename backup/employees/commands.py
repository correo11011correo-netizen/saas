import datetime
import logging
import uuid

from sqlalchemy import text
from sqlalchemy.orm import Session

from core.context import TenantContext
from core.decorators import command
from core.types import ServiceResponse
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

            session.execute(
                text(
                    """
                    INSERT INTO business_definitions (tenant_id, def_type, def_key, def_label)
                    VALUES (:tid, :type, :key, :label)
                    ON CONFLICT (tenant_id, def_type, def_key) DO UPDATE SET def_label = EXCLUDED.def_label
                    """
                ),
                {"tid": context.tenant_id, "type": def_type, "key": def_key, "label": def_label},
            )
            session.commit()
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
            session.execute(
                text(
                    """
                    INSERT INTO employees (id, tenant_id, user_id, bot_profile_id, name, role, type)
                    VALUES (:id, :tid, :uid, :bid, :name, :role, :type)
                    """
                ),
                {
                    "id": employee_id,
                    "tid": context.tenant_id,
                    "uid": uuid.UUID(user_id) if user_id else None,
                    "bid": uuid.UUID(bot_profile_id) if bot_profile_id else None,
                    "name": name,
                    "role": role,
                    "type": type,
                },
            )
            session.commit()
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
            # Validar que el permiso existe en las definiciones del negocio
            tenant_id = session.execute(
                text("SELECT tenant_id FROM employees WHERE id = :eid"),
                {"eid": uuid.UUID(employee_id)},
            ).scalar()

            exists = session.execute(
                text(
                    "SELECT 1 FROM business_definitions WHERE tenant_id = :tid AND def_type = 'permission' AND def_key = :key"
                ),
                {"tid": tenant_id, "key": permission_key},
            ).first()

            if not exists:
                return ServiceResponse.error_res(
                    f"Permission '{permission_key}' is not defined for this business. Use 'staff.define_business_term' first.",
                    "UNDEFINED_PERMISSION",
                )

            session.execute(
                text(
                    """
                    INSERT INTO employee_permissions (employee_id, permission_key, granted)
                    VALUES (:eid, :key, :granted)
                    ON CONFLICT (employee_id, permission_key) DO UPDATE SET granted = EXCLUDED.granted
                    """
                ),
                {"eid": uuid.UUID(employee_id), "key": permission_key, "granted": granted},
            )
            session.commit()
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
            # Validar que el tipo de meta existe en las definiciones del negocio
            tenant_id = session.execute(
                text("SELECT tenant_id FROM employees WHERE id = :eid"),
                {"eid": uuid.UUID(employee_id)},
            ).scalar()

            exists = session.execute(
                text(
                    "SELECT 1 FROM business_definitions WHERE tenant_id = :tid AND def_type = 'goal_type' AND def_key = :key"
                ),
                {"tid": tenant_id, "key": goal_type},
            ).first()

            if not exists:
                return ServiceResponse.error_res(
                    f"Goal type '{goal_type}' is not defined for this business. Use 'staff.define_business_term' first.",
                    "UNDEFINED_GOAL",
                )

            session.execute(
                text(
                    """
                    INSERT INTO employee_goals (employee_id, goal_type, target_value, start_date, end_date, tenant_id)
                    VALUES (:eid, :type, :target, :start, :end, :tid)
                    """
                ),
                {
                    "eid": uuid.UUID(employee_id),
                    "type": goal_type,
                    "target": target,
                    "start": datetime.date.fromisoformat(start_date),
                    "end": datetime.date.fromisoformat(end_date),
                    "tid": context.tenant_id,
                },
            )
            session.commit()
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
