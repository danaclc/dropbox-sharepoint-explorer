"""
Logging configuration using loguru.
Provides colored console output and file logging with UTC timestamps.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from loguru import logger


def utc_timestamp(record: dict[str, Any]) -> None:
    """
    Custom formatter to add UTC timestamp to log records.

    This ensures all timestamps are in UTC regardless of system timezone.
    Called by loguru's patcher system to inject custom fields into log records.

    Args:
        record: Loguru log record dictionary containing log event information
    """
    record["extra"]["utc_time"] = datetime.now(timezone.utc)


def configure_logging(
    console_level: str = "INFO",
    file_level: str = "DEBUG",
    log_dir: str = "logs",
) -> None:
    """
    Configure loguru logging with console and file handlers.

    Args:
        console_level: Log level for console output (NONE, DEBUG, INFO, WARNING, ERROR, CRITICAL)
        file_level: Log level for file output (NONE, DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory to store log files

    Features:
        - UTC timestamps
        - Colored console output
        - File logging with rotation
        - Configurable log levels
        - Support for NONE level (disables logging)
    """
    # Remove default handler
    logger.remove()

    # Normalize log levels
    console_level = console_level.upper().strip()
    file_level = file_level.upper().strip()

    # Configure logger to use UTC
    logger.configure(patcher=utc_timestamp)

    # Console handler with colors (if not NONE)
    if console_level != "NONE":
        logger.add(
            sys.stderr,
            format="<green>{extra[utc_time]:%Y-%m-%d %H:%M:%S.%f}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            level=console_level,
            colorize=True,
            enqueue=True,  # Thread-safe
        )

    # File handler (if not NONE)
    if file_level != "NONE":
        # Create log directory if it doesn't exist
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)

        # Generate log filename with current UTC timestamp
        utc_now = datetime.now(timezone.utc)
        log_filename = utc_now.strftime("%Y%m%d-%H%M%S.log")
        log_file = log_path / log_filename

        logger.add(
            log_file,
            format="{extra[utc_time]:%Y-%m-%d %H:%M:%S.%f} | {level: <8} | {name}:{function}:{line} - {message}",
            level=file_level,
            rotation="100 MB",  # Rotate when file reaches 100MB
            retention="30 days",  # Keep logs for 30 days
            compression="zip",  # Compress rotated logs
            enqueue=True,  # Thread-safe
            encoding="utf-8",
        )

        # Log the file location at startup
        logger.info(f"Logging to file: {log_file}")


def get_logger() -> "logger":
    """
    Get the configured logger instance.

    Returns the global loguru logger instance which should be configured
    via configure_logging() before use. This function provides a consistent
    way to access the logger across the application.

    Returns:
        loguru.logger: The configured logger instance with all handlers

    Example:
        >>> from src.logger import get_logger
        >>> logger = get_logger()
        >>> logger.info("Application started")
    """
    return logger
