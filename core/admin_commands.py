import os
import time
import platform
import logging
from typing import Any
from sqlalchemy.orm import Session

from core.context import TenantContext
from core.decorators import command
from core.types import ServiceResponse
from core.db import db_manager

logger = logging.getLogger("OmniCore.Admin")

class AdminCommandHandler:
    """
    Sentry Control Center.
    Provee comandos para el monitoreo, diagnóstico y recuperación
    de la infraestructura del sistema.
    """

    @command(
        name="admin.health_check",
        description="Returns the overall health status of the system and DB.",
        params_model={},
    )
    def health_check(self, session: Session, context: TenantContext) -> ServiceResponse:
        try:
            # 1. Verificar conexión DB
            db_status = "ONLINE" if db_manager.is_connected else "OFFLINE"
            
            # 2. Medir latencia simple
            latency = 0
            if db_manager.is_connected:
                start = time.time()
                session.execute("SELECT 1")
                latency = round((time.time() - start) * 1000, 2)

            return ServiceResponse.success_res(
                data={
                    "db_status": db_status,
                    "latency_ms": latency,
                    "timestamp": time.time(),
                    "system_ok": db_manager.is_connected
                },
                message=f"System health: {db_status}"
            )
        except Exception as e:
            return ServiceResponse.error_res(f"Health check failed: {str(e)}", "HEALTH_ERROR")

    @command(
        name="admin.retry_connection",
        description="Forces a re-initialization of the database connection pool.",
        params_model={},
    )
    def retry_connection(self, session: Session, context: TenantContext) -> ServiceResponse:
        try:
            success = db_manager.reconnect()
            if success:
                return ServiceResponse.success_res(message="Database reconnected successfully.")
            else:
                return ServiceResponse.error_res("Failed to reconnect. Please check DATABASE_URL.", "RECONNECT_FAILED")
        except Exception as e:
            return ServiceResponse.error_res(str(e), "RECONNECT_ERROR")

    @command(
        name="admin.get_logs",
        description="Reads the server logs file. Supports offset for pagination.",
        params_model={"offset": "int", "limit": "int"},
    )
    def get_logs(self, session: Session, context: TenantContext, offset: int = 0, limit: int = 100) -> ServiceResponse:
        try:
            # El log suele estar en el root o definido por el entorno
            log_path = os.getenv("LOG_FILE", "server.log")
            if not os.path.exists(log_path):
                return ServiceResponse.error_res("Log file not found on server.", "LOG_NOT_FOUND")

            with open(log_path, "r") as f:
                lines = f.readlines()
            
            # Retornar el segmento solicitado (últimas líneas primero)
            total = len(lines)
            start = max(0, total - offset - limit)
            end = total - offset
            
            chunk = lines[start:end]
            return ServiceResponse.success_res(
                data={"logs": chunk, "total_lines": total}, 
                message=f"Retrieved {len(chunk)} log lines."
            )
        except Exception as e:
            return ServiceResponse.error_res(f"Error reading logs: {str(e)}", "LOG_READ_ERROR")

    @command(
        name="admin.system_info",
        description="Returns system hardware and environment metadata.",
        params_model={},
    )
    def system_info(self, session: Session, context: TenantContext) -> ServiceResponse:
        try:
            info = {
                "os": platform.system(),
                "os_release": platform.release(),
                "node": platform.node(),
                "python_version": platform.python_version(),
                "db_url_configured": bool(db_manager.url != "Not configured"),
                "uptime": "N/A (Requires external tracking)",
                "env": os.getenv("ENVIRONMENT", "production")
            }
            return ServiceResponse.success_res(data=info, message="System info retrieved.")
        except Exception as e:
            return ServiceResponse.error_res(str(e), "SYS_INFO_ERROR")

    @command(
        name="admin.get_system_errors",
        description="Collects critical errors from the system logs.",
        params_model={},
    )
    def get_system_errors(self, session: Session, context: TenantContext) -> ServiceResponse:
        try:
            log_path = os.getenv("LOG_FILE", "server.log")
            if not os.path.exists(log_path):
                return ServiceResponse.success_res(data=[], message="No logs found.")

            errors = []
            with open(log_path, "r") as f:
                for line in f:
                    if "ERROR" in line or "CRITICAL" in line or "Exception" in line:
                        errors.append(line.strip())
            
            # Retornar los últimos 50 errores
            return ServiceResponse.success_res(data=errors[-50:], message=f"Found {len(errors)} critical entries.")
        except Exception as e:
            return ServiceResponse.error_res(str(e), "ERR_FETCH_ERROR")

admin_commands = AdminCommandHandler()
