import json
import logging
import sys


class SafeFormatter(logging.Formatter):
    """Formateador robusto que asegura que los campos de contexto existan y no causen errores."""

    def format(self, record):
        # Asegurar que los atributos de contexto existan para evitar KeyError en el formateador
        record.tenant_id = getattr(record, "tenant_id", "SYSTEM")
        record.user_id = getattr(record, "user_id", "N/A")

        # Manejar el caso donde el mensaje sea un diccionario o objeto
        if isinstance(record.msg, dict):
            record.msg = json.dumps(record.msg, default=str)

        return super().format(record)


def setup_logging():
    # Usar sys.stdout para asegurar compatibilidad con logs de contenedores/Railway
    handler = logging.StreamHandler(sys.stdout)

    # Formato detallado con archivo y línea para debug rápido en Railway
    log_format = "%(asctime)s - %(name)s - %(levelname)s - [%(tenant_id)s] [%(user_id)s] - %(message)s (%(filename)s:%(lineno)d)"
    formatter = SafeFormatter(log_format)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Limpiar manejadores existentes para evitar logs duplicados
    for h in root_logger.handlers[:]:
        root_logger.removeHandler(h)

    root_logger.addHandler(handler)

    return logging.getLogger("OmniCore")


logger = setup_logging()
