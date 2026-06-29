import logging
import sys


class SafeFormatter(logging.Formatter):
    """Formateador que asegura que los campos de contexto existan."""

    def format(self, record):
        if not hasattr(record, "tenant_id"):
            record.tenant_id = "SYSTEM"
        if not hasattr(record, "user_id"):
            record.user_id = "N/A"
        return super().format(record)


def setup_logging():
    # Usar sys.stdout para asegurar compatibilidad con logs de contenedores/Railway
    handler = logging.StreamHandler(sys.stdout)

    # Formato con detalle adicional de archivo y línea para facilitar debug
    formatter = SafeFormatter(
        "%(asctime)s - %(name)s - %(levelname)s - [%(tenant_id)s] [%(user_id)s] - %(message)s (%(filename)s:%(lineno)d)"
    )
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()

    # Nivel INFO para producción, pero con capacidad de subir a DEBUG si se necesita
    root_logger.setLevel(logging.INFO)

    # Limpiar manejadores existentes
    for h in root_logger.handlers[:]:
        root_logger.removeHandler(h)

    root_logger.addHandler(handler)

    return logging.getLogger("OmniCore")


logger = setup_logging()
