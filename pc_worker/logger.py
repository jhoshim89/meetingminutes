"""
Structured Logging Module
Provides consistent, rotating logs with proper formatting
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from datetime import datetime
from typing import Optional


class StructuredLogger:
    """Structured logger with file rotation and console output"""

    def __init__(
        self,
        name: str,
        log_dir: str = "./logs",
        level: str = "INFO",
        max_bytes: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5
    ):
        self.name = name
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Create logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.upper()))

        # Remove existing handlers to avoid duplicates
        self.logger.handlers.clear()

        # Create formatters
        detailed_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        console_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )

        # File handler with rotation
        log_file = self.log_dir / f"{name}.log"
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(detailed_formatter)
        self.logger.addHandler(file_handler)

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, level.upper()))
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)

        # Error file handler (separate file for errors)
        error_log_file = self.log_dir / f"{name}_errors.log"
        error_handler = RotatingFileHandler(
            error_log_file,
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(detailed_formatter)
        self.logger.addHandler(error_handler)

    def debug(self, message: str, **kwargs):
        """Log debug message with optional structured data"""
        self._log(logging.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs):
        """Log info message with optional structured data"""
        self._log(logging.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs):
        """Log warning message with optional structured data"""
        self._log(logging.WARNING, message, **kwargs)

    def error(self, message: str, exc_info: bool = False, **kwargs):
        """Log error message with optional exception info and structured data"""
        self._log(logging.ERROR, message, exc_info=exc_info, **kwargs)

    def critical(self, message: str, exc_info: bool = False, **kwargs):
        """Log critical message with optional exception info and structured data"""
        self._log(logging.CRITICAL, message, exc_info=exc_info, **kwargs)

    def _log(self, level: int, message: str, exc_info: bool = False, **kwargs):
        """Internal logging method with structured data support"""
        if kwargs:
            # Add structured data to message
            structured_data = " | ".join([f"{k}={v}" for k, v in kwargs.items()])
            message = f"{message} | {structured_data}"

        self.logger.log(level, message, exc_info=exc_info)

    def log_operation_start(self, operation: str, **context):
        """Log the start of an operation with context"""
        self.info(f"Starting operation: {operation}", **context)

    def log_operation_success(self, operation: str, duration_ms: Optional[float] = None, **context):
        """Log successful completion of an operation"""
        if duration_ms is not None:
            context['duration_ms'] = f"{duration_ms:.2f}"
        self.info(f"Completed operation: {operation}", **context)

    def log_operation_failure(self, operation: str, error: Exception, **context):
        """Log operation failure with error details"""
        context['error_type'] = type(error).__name__
        self.error(
            f"Failed operation: {operation} - {str(error)}",
            exc_info=True,
            **context
        )

    def log_meeting_event(self, meeting_id: str, event: str, **details):
        """Log meeting-specific events"""
        self.info(f"Meeting event: {event}", meeting_id=meeting_id, **details)


def get_logger(
    name: str,
    log_dir: str = "./logs",
    level: str = "INFO"
) -> StructuredLogger:
    """Factory function to get or create a structured logger"""
    return StructuredLogger(name, log_dir, level)


# Create default worker logger
default_logger = get_logger("pc_worker", level="INFO")
