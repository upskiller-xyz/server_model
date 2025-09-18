import logging
import sys
from typing import Optional
from ..interfaces import ILogger
from ..enums import LogLevel


class StructuredLogger(ILogger):
    """Structured logging implementation"""

    def __init__(self, name: str = "ModelServer", level: LogLevel = LogLevel.INFO):
        self._logger = logging.getLogger(name)
        self._setup_logger(level)

    def _setup_logger(self, level: LogLevel) -> None:
        """Setup logger configuration"""
        log_levels = {
            LogLevel.DEBUG: logging.DEBUG,
            LogLevel.INFO: logging.INFO,
            LogLevel.WARNING: logging.WARNING,
            LogLevel.ERROR: logging.ERROR
        }

        self._logger.setLevel(log_levels[level])

        if not self._logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self._logger.addHandler(handler)

    def debug(self, message: str) -> None:
        self._logger.debug(message)

    def info(self, message: str) -> None:
        self._logger.info(message)

    def warning(self, message: str) -> None:
        self._logger.warning(message)

    def error(self, message: str) -> None:
        self._logger.error(message)