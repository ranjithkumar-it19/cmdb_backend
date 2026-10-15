import logging
import re
import sys
from typing import Any, Dict


# Sensitive patterns to redact
SENSITIVE_PATTERNS = [
    re.compile(r'(password|passwd|secret|token|api[_-]?key|private[_-]?key|credential)\s*[:=]\s*["\']?([^"\'\s]+)["\']?', re.IGNORECASE),
    re.compile(r'(authorization\s*:\s*bearer\s+)([\w\.-]+)', re.IGNORECASE),
]


class RedactingFormatter(logging.Formatter):
    """Custom formatter that scrubs sensitive credentials from log records."""

    def format(self, record: logging.LogRecord) -> str:
        msg = super().format(record)
        for pattern in SENSITIVE_PATTERNS:
            msg = pattern.sub(r'\1=********', msg)
        return msg


def setup_logging(debug: bool = False) -> logging.Logger:
    """Setup centralized structured logging for Atlas Discovery."""
    level = logging.DEBUG if debug else logging.INFO
    logger = logging.getLogger("atlas")
    logger.setLevel(level)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        formatter = RedactingFormatter(
            fmt="%(asctime)s [%(levelname)s] [%(name)s] [%(filename)s:%(lineno)d] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    # Configure root logger as well
    logging.basicConfig(level=level, handlers=[handler])
    return logger


logger = setup_logging()
