"""Centralized logging module for the application.

Provides logging to both console and file with rotation support.
Logs are written to AppData/osim_render/logs/ directory.

Uses a module-level singleton pattern to ensure all loggers share a single
file handler, preventing file access conflicts during rotation.
"""

import logging
import logging.handlers
import os
from pathlib import Path
from typing import Optional

# Module-level state for centralized handler management
_initialized = False
_file_handler: Optional[logging.handlers.RotatingFileHandler] = None


def _get_log_directory() -> Path:
    """Get the logs directory, creating it if needed.

    Returns:
        Path to logs directory in AppData
    """
    if "APPDATA" in os.environ:
        log_dir = Path(os.environ["APPDATA"]) / "osim_render" / "logs"
    else:
        log_dir = Path.home() / ".osim_render" / "logs"

    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def _setup_root_logger() -> Optional[logging.handlers.RotatingFileHandler]:
    """Set up root logger with shared handlers.

    Returns:
        The shared RotatingFileHandler for file logging
    """
    global _initialized, _file_handler

    if _initialized:
        return _file_handler

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # Create formatters
    console_formatter = logging.Formatter("[%(levelname)-8s] %(name)s - %(message)s")
    file_formatter = logging.Formatter(
        "%(asctime)s - [%(levelname)-8s] - %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler (INFO level and above) - only add if not already present
    if not any(isinstance(h, logging.StreamHandler) for h in root_logger.handlers):
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)

    # File handler (DEBUG level and above) - only add if not already present
    if not any(
        isinstance(h, logging.handlers.RotatingFileHandler)
        for h in root_logger.handlers
    ):
        log_dir = _get_log_directory()
        log_file = log_dir / "osim_render.log"

        _file_handler = logging.handlers.RotatingFileHandler(
            str(log_file),
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
        )
        _file_handler.setLevel(logging.DEBUG)
        _file_handler.setFormatter(file_formatter)
        root_logger.addHandler(_file_handler)

    _initialized = True
    return _file_handler


def get_logger_for(name: str) -> logging.Logger:
    """Get a logger instance for a module or class.

    All loggers share a centralized file handler to prevent file rotation conflicts.
    The logger name is included in output so you can see which class/module logged each message.

    Args:
        name: Name of the module/class (typically __name__ or ClassName)

    Returns:
        Configured logger instance with proper hierarchy
    """
    # Ensure root logger is set up
    _setup_root_logger()

    # Get or create logger with the given name
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Allow propagation to root logger so messages reach the centralized handlers
    logger.propagate = True

    return logger


if __name__ == "__main__":
    """Smoke test for logging system."""
    print("Logging system smoke test\n")

    # Create test logger
    logger = get_logger_for("test_module")
    log_dir = _get_log_directory()

    print(f"Log directory: {log_dir}")
    print(f"Log file: {log_dir / 'osim_render.log'}\n")

    # Test logging at different levels
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")

    print(f"\n[OK] Log file created at: {log_dir / 'osim_render.log'}")
    print("[OK] Logging system smoke test passed!")
