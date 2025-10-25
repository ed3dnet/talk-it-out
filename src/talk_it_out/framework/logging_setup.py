# pattern: Functional Core
# Pure functions for logging configuration

import sys
import logging
import structlog


def get_log_level(cfg: dict) -> str:
    """Extract log level from config.

    Args:
        cfg: Configuration dictionary

    Returns:
        Log level string (DEBUG/INFO/WARNING/ERROR), defaults to INFO
    """
    try:
        return cfg["logging"]["level"]
    except KeyError:
        return "INFO"


def configure_logging(log_level: str = "INFO") -> structlog.BoundLogger:
    """Configure structured logging to stderr.

    Args:
        log_level: Logging level (DEBUG/INFO/WARNING/ERROR)

    Returns:
        Configured structlog logger
    """
    # Map string level to logging constant
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
    }
    level = level_map.get(log_level, logging.INFO)

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),  # Colored, human-readable output
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
        cache_logger_on_first_use=False,
    )

    return structlog.get_logger()
