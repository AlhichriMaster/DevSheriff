import logging
import json
from datetime import datetime, timezone

from app.config import settings


class StructuredFormatter(logging.Formatter):
    """JSON structured log formatter for Cloud Logging compatibility."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "severity": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }

        # Merge any extra fields passed via extra={}
        if hasattr(record, "__dict__"):
            for key, value in record.__dict__.items():
                if key not in (
                    "name", "msg", "args", "levelname", "levelno", "pathname",
                    "filename", "module", "exc_info", "exc_text", "stack_info",
                    "lineno", "funcName", "created", "msecs", "relativeCreated",
                    "thread", "threadName", "processName", "process", "message",
                    "taskName",
                ):
                    log_entry[key] = value

        return json.dumps(log_entry, default=str)


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler()
        if settings.ENVIRONMENT == "production":
            handler.setFormatter(StructuredFormatter())
        else:
            handler.setFormatter(
                logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
            )
        logger.addHandler(handler)

    logger.setLevel(logging.INFO)
    return logger
