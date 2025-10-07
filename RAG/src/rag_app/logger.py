import logging
from logging.handlers import RotatingFileHandler
import os
from datetime import datetime
from typing import Optional
from .core.utils.context import get_request_id
from rag_app.private_config import private_settings

class RequestIdFilter(logging.Filter):
    def filter(self, record):
        try:
            record.request_id = get_request_id() or 'startup'
        except Exception:
            record.request_id = 'startup'
        return True

def setup_logging():
    """
    Sets up unified logging configuration with rotation capabilities.
    
    Log Rotation Configuration:
    - Size-based: Rotates when file reaches LOG_MAX_BYTES
    - Keeps up to LOG_BACKUP_COUNT backup files
    - Naming format: 
        - Current: rag_port_{port}_{timestamp}.log
        - Backups: rag_port_{port}_{timestamp}.log.1, .log.2, etc.
    
    Log Format:
    - Includes timestamp, request ID, logger name, level, and message
    - Example: 2024-03-21 10:00:00,000 - [request_id] - logger_name - LEVEL - message
    """
    # Create log directory if it doesn't exist
    log_dir = private_settings.LOG_DIR
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Create a single log file name with port
    log_file = os.path.join(
        log_dir, 
        f"rag_port_{private_settings.BACKEND_PORT}.log"
    )

    # Create formatter with request_id
    formatter = logging.Formatter(
        '%(asctime)s - [%(request_id)s] - %(name)s - %(levelname)s - %(message)s'
    )

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, private_settings.LOG_LEVEL))

    # Remove any existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create and configure handlers
    handlers = [
        # Rotating handler for the log file
        RotatingFileHandler(
            log_file,
            maxBytes=private_settings.LOG_MAX_BYTES,  # e.g., 10 * 1024 * 1024 for 10MB
            backupCount=private_settings.LOG_BACKUP_COUNT,  # Number of backup files to keep
            encoding='utf-8'
        ),
        # Console output
        logging.StreamHandler()
    ]

    # Configure all handlers with formatter and filter
    request_id_filter = RequestIdFilter()
    for handler in handlers:
        handler.setFormatter(formatter)
        handler.addFilter(request_id_filter)
        root_logger.addHandler(handler)

    # Disable uvicorn access logs
    logging.getLogger("uvicorn.access").disabled = True

    logger = logging.getLogger(__name__)
    logger.info("Logging setup completed.")
    logger.info(f"Log file: {log_file}")
    logger.info(f"Log rotation: max_bytes={private_settings.LOG_MAX_BYTES}, "
                f"backup_count={private_settings.LOG_BACKUP_COUNT}")
