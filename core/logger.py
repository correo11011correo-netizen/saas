import logging


class SafeFormatter(logging.Formatter):
    """Formateador que maneja campos faltantes en el record."""

    def format(self, record):
        if not hasattr(record, "tenant_id"):
            record.tenant_id = "SYSTEM"
        if not hasattr(record, "user_id"):
            record.user_id = "N/A"
        return super().format(record)


def setup_logging():
    # Crear un manejador que imprima a stdout
    handler = logging.StreamHandler()

    # Formato seguro
    formatter = SafeFormatter(
        "%(asctime)s - %(name)s - %(levelname)s - [%(tenant_id)s] [%(user_id)s] - %(message)s"
    )
    handler.setFormatter(formatter)

    # Configurar el logger raíz
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Limpiar manejadores existentes para evitar duplicados
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    root_logger.addHandler(handler)

    return logging.getLogger("OmniCore")


logger = setup_logging()
