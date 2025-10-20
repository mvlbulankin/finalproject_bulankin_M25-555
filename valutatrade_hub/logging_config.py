import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from .core.utils import ensure_dir


def setup_logging(log_path: str = "logs", level: str = "INFO"):
    ensure_dir(log_path)
    log_file = Path(log_path) / "actions.log"
    handler = RotatingFileHandler(
        log_file, maxBytes=5*1024*1024, backupCount=5, encoding="utf-8"
    )
    formatter = logging.Formatter(
        '%(asctime)s %(levelname)s %(message)s',
        datefmt='%Y-%m-%dT%H:%M:%S'
    )
    handler.setFormatter(formatter)
    logger = logging.getLogger("ValutaTrade")
    logger.setLevel(getattr(logging, level))
    logger.addHandler(handler)
    logger.addHandler(logging.StreamHandler(sys.stdout))  # Для консоли
    return logger
