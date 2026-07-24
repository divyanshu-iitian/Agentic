"""
Logging Utility

Centralized logging setup with file rotation and console output
"""

import sys
from pathlib import Path

from loguru import logger

from core.config import get_config


def _safe_console_sink(message) -> None:
    """Write logs without crashing on consoles that cannot encode Unicode."""
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    safe_message = str(message).encode(encoding, errors="replace").decode(encoding)
    sys.stdout.write(safe_message)


def setup_logger():
    """
    Configure loguru logger based on config settings.
    """
    config = get_config()
    log_config = config.logging

    # Remove default handler
    logger.remove()

    # Create logs directory
    log_file = Path(log_config.file)
    log_file.parent.mkdir(parents=True, exist_ok=True)

    # Console output
    if log_config.console_output:
        logger.add(
            _safe_console_sink,
            level=log_config.level,
            format=(
                "<green>{time:HH:mm:ss}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan> - "
                "<level>{message}</level>"
            ),
            colorize=False,
        )

    # File output with rotation
    logger.add(
        log_config.file,
        level=log_config.level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        rotation=f"{log_config.max_size_mb} MB",
        retention=log_config.backup_count,
        compression="zip",
    )

    logger.info("Logger initialized")
    return logger


# Global logger instance
log = setup_logger()
