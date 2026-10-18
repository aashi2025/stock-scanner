"""
Secure Logging Configuration with Secret Redaction for Indian Market Intelligence Terminal.
Ensures API keys, tokens, passwords, and sensitive credentials are never leaked to logs or console.
"""

import logging
import re
import sys
from typing import List

# Patterns matching sensitive keys and tokens
SENSITIVE_PATTERNS = [
    re.compile(r"(api[_-]?key\s*[:=]\s*)(['\"]?[a-zA-Z0-9_\-]{8,}['\"]?)", re.IGNORECASE),
    re.compile(r"(api[_-]?secret\s*[:=]\s*)(['\"]?[a-zA-Z0-9_\-]{8,}['\"]?)", re.IGNORECASE),
    re.compile(r"(access[_-]?token\s*[:=]\s*)(['\"]?[a-zA-Z0-9_\.\-]{15,}['\"]?)", re.IGNORECASE),
    re.compile(r"(bot[_-]?token\s*[:=]\s*)(['\"]?[0-9]{8,}:[a-zA-Z0-9_\-]{20,}['\"]?)", re.IGNORECASE),
    re.compile(r"(Bearer\s+)([a-zA-Z0-9_\.\-]{15,})", re.IGNORECASE),
    re.compile(r"(password\s*[:=]\s*)(['\"]?[^\s'\"]+['\"]?)", re.IGNORECASE),
]

class RedactingFormatter(logging.Formatter):
    """Custom logging formatter that scrubs sensitive credentials from output."""

    def format(self, record: logging.LogRecord) -> str:
        original = super().format(record)
        redacted = original
        for pattern in SENSITIVE_PATTERNS:
            redacted = pattern.sub(r"\1[REDACTED]", redacted)
        return redacted


def setup_terminal_logging(log_level: int = logging.INFO) -> logging.Logger:
    """Configures application-wide logging with automatic credential scrubbing."""
    logger = logging.getLogger("MarketIntelligenceTerminal")
    logger.setLevel(log_level)

    # Avoid duplicate handlers on reloads
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = RedactingFormatter(
            fmt="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger

logger = setup_terminal_logging()
