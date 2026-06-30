import logging
import sys

from app.config import get_settings


def setup_logging() -> logging.Logger:
    settings = get_settings()
    logger = logging.getLogger("routewise")
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | trace=%(trace_id)s | %(message)s",
            defaults={"trace_id": "-"},
        )
    )
    logger.addHandler(handler)
    logger.info("Starting %s", settings.app_name)
    return logger


logger = setup_logging()


def log_with_trace(trace_id: str, level: str, message: str, **kwargs) -> None:
    extra = {"trace_id": trace_id}
    getattr(logger, level)(message, extra=extra, **kwargs)
