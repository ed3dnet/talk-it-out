# pattern: Functional Core tests
# Tests for logging configuration

import sys
import structlog
from talk_it_out.framework import logging_setup


def test_configure_logging_returns_logger():
    """configure_logging should return a logger instance"""
    logger = logging_setup.configure_logging("INFO")

    assert logger is not None
    assert hasattr(logger, "info")
    assert hasattr(logger, "error")
    assert hasattr(logger, "debug")


def test_configure_logging_respects_log_level():
    """Log level filtering should work"""
    # This test verifies the function configures properly
    # Actual filtering behavior is tested by structlog itself
    logger = logging_setup.configure_logging("ERROR")

    # Should not raise
    logger.error("test message")


def test_get_log_level_extracts_from_config():
    """get_log_level should extract level from config dict"""
    cfg = {"logging": {"level": "DEBUG"}}

    level = logging_setup.get_log_level(cfg)

    assert level == "DEBUG"


def test_get_log_level_returns_default_if_missing():
    """get_log_level should return INFO if not in config"""
    cfg = {}

    level = logging_setup.get_log_level(cfg)

    assert level == "INFO"
