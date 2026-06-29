import json
import logging
import uuid
from collections.abc import Callable
from typing import Any

from .context import TenantContext
from core.logger import logger as system_logger

logger = system_logger.getChild("Dispatcher")


class CommandDispatcher:
    def __init__(self, db_session_factory=None):
        self.registry: dict[str, Callable] = {}
        self.db_session_factory = db_session_factory

    def set_db_session_factory(self, factory):
        self.db_session_factory = factory

    def register_handler(self, handler: Any):
        """
        Scans a handler object for methods decorated with @command
        and registers them.
        """
        for attr_name in dir(handler):
            attr = getattr(handler, attr_name)
            if hasattr(attr, "_is_command"):
                cmd_name = attr._command_name
                self.register(cmd_name, attr)

    def register(self, name: str, func: Callable):
        self.registry[name] = func

    def execute(self, command_name: str, params: dict[str, Any], context: TenantContext) -> Any:
        # Añadimos contexto al log para esta ejecución
        extra = {"tenant_id": str(context.tenant_id), "user_id": str(context.user_id)}
        
        if command_name not in self.registry:
            logger.warning(
                f"Command {command_name} not found in registry.", extra=extra
            )
            return {
                "success": False,
                "error": f"Command {command_name} not found",
                "code": "CMD_NOT_FOUND",
            }

        func = self.registry[command_name]
        required_plan = getattr(func, "_required_plan", "free")

        # Plan-Based Access Control (PBAC) & SuperAdmin Bypass
        if context.role != "superadmin":
            if required_plan == "pro" and context.plan != "pro":
                return {
                    "success": False,
                    "error": "This command requires a PRO plan.",
                    "code": "PLAN_REQUIRED",
                }
        
        with self.db_session_factory() as session:
            try:
                # Inject context and session as first arguments
                # The commands are expected to be: func(session, context, **params)
                result = func(session, context, **params)

                # Commit the business transaction before auditing
                session.commit()

                # Automatic Audit Log (Independent transaction)
                try:
                    self._audit(context, command_name, params)
                except Exception as audit_err:
                    logger.error(f"Audit failed for {command_name}: {audit_err}", extra=extra)

                return result
            except Exception as e:
                session.rollback()
                logger.exception(f"Error executing {command_name}: {e}", extra=extra)
                return {"success": False, "error": str(e), "code": "EXECUTION_ERROR"}

    def _audit(self, context: TenantContext, command: str, params: dict):
        import time

        from sqlalchemy import text

        class UUIDEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, uuid.UUID):
                    return str(obj)
                return super().default(obj)

        max_retries = 3
        for attempt in range(max_retries):
            session = None
            try:
                session = self.db_session_factory()
                session.execute(
                    text(
                        "INSERT INTO audit_log (tenant_id, user_id, command, params) VALUES (:tid, :uid, :cmd, :p)"
                    ),
                    {
                        "tid": context.tenant_id,
                        "uid": context.user_id,
                        "cmd": command,
                        "p": json.dumps(params, cls=UUIDEncoder),
                    },
                )
                session.commit()
                return  # Éxito, salimos del bucle
            except Exception as e:
                if session:
                    session.rollback()

                # Si es el último intento, lanzamos el error
                if attempt == max_retries - 1:
                    raise e

                # Espera exponencial breve antes del reintento (0.1s, 0.2s...)
                wait_time = (attempt + 1) * 0.1
                logger.warning(
                    f"Audit connection failed. Retrying in {wait_time}s... (Attempt {attempt + 1}/{max_retries})"
                )
                time.sleep(wait_time)
            finally:
                if session:
                    session.close()


# Singleton instance to be used by the API
# The session factory will be provided during app startup
dispatcher = CommandDispatcher(db_session_factory=None)
