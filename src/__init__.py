"""
Dropbox Public Link Explorer.

Recursively explores Dropbox shared links and exports metadata to JSON.

This package provides tools for exploring Dropbox public/shared links,
handling session-based resumption, and exporting complete folder structures
with file metadata.

Key Features:
- Automatic session system with resumable operations
- Token auto-refresh to prevent expiration
- Hierarchical JSON export with statistics
- Graceful handling of restricted content

Exports:
    __version__: Package version string (from VCS or fallback)
    logger: Pre-configured loguru logger instance
"""

try:
    from src._version import __version__
except ImportError:
    # Fallback version for development installs without VCS
    __version__ = "0.0.0+unknown"

# Import logger for easy access across all modules
from src.logger import get_logger

logger = get_logger()

__all__ = ["__version__", "logger"]
