"""
Custom logging classes for Archy
"""
import logging
from typing import Dict

__all__ = ['ExtraStreamHandler']




class ExtraStreamHandler(logging.StreamHandler):
    """
    Wrapper around StreamHandler to permit parsing `extra` parameters
    """
    LOGGING_RESERVED_ATTRS = (
        'args', 'asctime', 'created', 'exc_info', 'exc_text', 'filename',
        'funcName', 'level', 'levelname', 'levelno', 'lineno', 'module',
        'msecs', 'message', 'msg', 'name', 'pathname', 'process',
        'processName', 'relativeCreated', 'stack_info', 'thread', 'threadName',
    )
    SEPARATOR = ' | '

    def _format_extra(self, extra: Dict) -> str:
        items = [
            f'{key}: {value}'
            for key, value in extra.items()
        ]
        if items:
            return self.SEPARATOR + self.SEPARATOR.join(items)
        return ''

    def _get_extra(self, record: logging.LogRecord) -> Dict:
        extras = {}
        for key, value in record.__dict__.items():
            if (key not in self.LOGGING_RESERVED_ATTRS and
                not (hasattr(key, 'startswith') and key.startswith('_'))):
                extras[key] = value
        return extras

    def format(self, record: logging.LogRecord) -> str:
        base = super().format(record)
        extra = self._get_extra(record)
        return base + self._format_extra(extra)
