"""
Logging configuration for Vāṇmayam
"""

import logging
import sys
from loguru import logger
from typing import Dict, Any
import json
from datetime import datetime

from app.core.config import settings


class InterceptHandler(logging.Handler):
    """
    Intercept standard logging messages toward loguru
    """
    
    def emit(self, record):
        # Get corresponding Loguru level if it exists
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def format_record(record: Dict[str, Any]) -> str:
    """
    Custom formatter for structured logging
    """
    format_string = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | " \
                   "<level>{level: <8}</level> | " \
                   "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | " \
                   "<level>{message}</level>"
    
    if record["extra"].get("request_id"):
        format_string += " | <yellow>req_id:{extra[request_id]}</yellow>"
    
    if record["exception"]:
        format_string += "\n{exception}"
    
    return format_string


def setup_logging() -> Any:
    """
    Setup logging configuration
    """
    # Remove default loguru handler
    logger.remove()
    
    # Add custom handler based on format preference
    if settings.LOG_FORMAT == "json":
        # JSON structured logging for production
        logger.add(
            sys.stdout,
            format=lambda record: json.dumps({
                "timestamp": datetime.utcnow().isoformat(),
                "level": record["level"].name,
                "logger": record["name"],
                "function": record["function"],
                "line": record["line"],
                "message": record["message"],
                "request_id": record["extra"].get("request_id"),
                "exception": str(record["exception"]) if record["exception"] else None,
            }) + "\n",
            level=settings.LOG_LEVEL,
            serialize=False,
        )
    else:
        # Human-readable format for development
        logger.add(
            sys.stdout,
            format=format_record,
            level=settings.LOG_LEVEL,
            colorize=True,
        )
    
    # Add file logging for production
    if not settings.DEBUG:
        logger.add(
            "logs/vangmayam.log",
            rotation="1 day",
            retention="30 days",
            compression="gzip",
            level="INFO",
            format=lambda record: json.dumps({
                "timestamp": datetime.utcnow().isoformat(),
                "level": record["level"].name,
                "logger": record["name"],
                "function": record["function"],
                "line": record["line"],
                "message": record["message"],
                "request_id": record["extra"].get("request_id"),
                "exception": str(record["exception"]) if record["exception"] else None,
            }) + "\n",
        )
    
    # Intercept standard logging
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    
    # Set specific loggers
    for logger_name in ["uvicorn", "uvicorn.access", "fastapi", "sqlalchemy"]:
        logging_logger = logging.getLogger(logger_name)
        logging_logger.handlers = [InterceptHandler()]
        logging_logger.setLevel(logging.INFO)
    
    return logger


def get_logger(name: str) -> Any:
    """
    Get logger instance with name
    """
    return logger.bind(logger_name=name)
