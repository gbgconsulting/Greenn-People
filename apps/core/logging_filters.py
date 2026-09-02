"""Filtros de logging para reduzir vazamento de credenciais em logs."""

from __future__ import annotations

import logging
import re

_REDACT_PATTERNS = (
    re.compile(r'(password["\']?\s*[:=]\s*)[^\s&"\']+', re.IGNORECASE),
    re.compile(r'(token["\']?\s*[:=]\s*)[^\s&"\']+', re.IGNORECASE),
    re.compile(r'(secret["\']?\s*[:=]\s*)[^\s&"\']+', re.IGNORECASE),
    re.compile(r'(authorization:\s*)[^\s]+', re.IGNORECASE),
)


class RedactSensitiveFilter(logging.Filter):
    """Substitui valores sensíveis em mensagens de log."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            message = record.getMessage()
        except Exception:
            return True
        redacted = message
        for pattern in _REDACT_PATTERNS:
            redacted = pattern.sub(r'\1[REDACTED]', redacted)
        if redacted != message:
            record.msg = redacted
            record.args = ()
        return True
