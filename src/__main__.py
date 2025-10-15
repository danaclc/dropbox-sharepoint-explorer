#!/usr/bin/env python3
"""
Main entry point for the Dropbox Explorer application.
This allows the package to be run with: python -m src

This module handles application-level setup including:
- Logging configuration
- Version information
- Environment variable loading
"""

import os
from dotenv import load_dotenv

from src import __version__, logger
from src.logger import configure_logging

# Load environment variables from .env file
load_dotenv()


def setup_application() -> None:
    """Configure application-level settings like logging."""
    # Configure logging from environment variables
    console_level = os.getenv("LOG_LEVEL_CONSOLE", "INFO")
    file_level = os.getenv("LOG_LEVEL_FILE", "DEBUG")
    log_dir = os.getenv("LOG_DIR", "logs")

    configure_logging(
        console_level=console_level,
        file_level=file_level,
        log_dir=log_dir,
    )

    # Log application startup information
    logger.info(f"Dropbox Public Link Explorer v{__version__}")
    logger.debug(f"Console log level: {console_level}")
    logger.debug(f"File log level: {file_level}")
    logger.debug(f"Log directory: {log_dir}")


if __name__ == "__main__":
    # Setup application-level configuration
    setup_application()

    # Import and run main function
    from src.explore import main

    main()
