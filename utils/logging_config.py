"""Configurazione centralizzata del logging applicativo."""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


LOGGER_NAME = "my_skill_agent"
LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_FILE = LOG_DIR / "app.log"
_configured = False


def setup_logging() -> logging.Logger:
    """Inizializza log console e file rotante una sola volta."""
    global _configured

    logger = logging.getLogger(LOGGER_NAME)
    if _configured:
        return logger

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=2 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    _configured = True
    logger.info("Logging inizializzato. File: %s", LOG_FILE)
    return logger


def get_logger(component: str) -> logging.Logger:
    """Ritorna un logger applicativo per il componente richiesto."""
    setup_logging()
    return logging.getLogger(f"{LOGGER_NAME}.{component}")
