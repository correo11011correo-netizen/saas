import logging
import os

# Configure global logging
def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - [%(tenant_id)s] [%(user_id)s] - %(message)s",
        # Custom log record factory to handle tenant_id/user_id in logs
    )

    # Filter to add default tenant_id and user_id to log records
    class ContextFilter(logging.Filter):
        def filter(self, record):
            if not hasattr(record, 'tenant_id'):
                record.tenant_id = 'SYSTEM'
            if not hasattr(record, 'user_id'):
                record.user_id = 'N/A'
            return True

    logger = logging.getLogger("OmniCore")
    logger.addFilter(ContextFilter())
    return logger

logger = setup_logging()
