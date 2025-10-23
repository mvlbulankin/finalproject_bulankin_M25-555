import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from .core.utils import ensure_dir


def setup_logging(
        log_path: str = "logs",
        level: str = "INFO",
        log_file: str = "actions.log",
        console: bool = True,
    ):
    ensure_dir(log_path)
    file_path = Path(log_path) / log_file
    file_handler = RotatingFileHandler(
        file_path, maxBytes=5*1024*1024, backupCount=5, encoding="utf-8"
    )
    formatter = logging.Formatter('%(levelname)s: %(message)s')
    file_handler.setFormatter(formatter)

    logger_name = "ValutaTrade" if "parser" not in log_file else "ValutaTrade.Parser"
    logger = logging.getLogger(logger_name)
    logger.setLevel(getattr(logging, level))

    logger.handlers.clear()
    logger.propagate = False
    logger.addHandler(file_handler)

    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    return logger
