# server/src/server/core/logging.py
"""
Logging Configuration

Sets up structured logging for the server.
"""

import logging
import sys

import structlog
from structlog.stdlib import LoggerFactory

from server.core.config import get_settings


def setup_logging():
    """Configure structured logging."""
    settings = get_settings()

    # Configure Python's logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level),
    )

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            (
                structlog.dev.ConsoleRenderer(colors=True)
                if settings.debug
                else structlog.processors.JSONRenderer()
            ),
        ],
        context_class=dict,
        logger_factory=LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
