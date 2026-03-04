"""
Модуль интернационализации (i18n) бэкенда.

Этот модуль обеспечивает поддержку перевода для сообщений об ошибках бэкенда
и строк, ориентированных на пользователя, на английском и русском языках.
"""

from .backend_translations import (
    get_error_message,
    get_success_message,
    get_validation_message,
    get_message,
    SUPPORTED_LANGUAGES,
    DEFAULT_LANGUAGE,
)

__all__ = [
    "get_error_message",
    "get_success_message",
    "get_validation_message",
    "get_message",
    "SUPPORTED_LANGUAGES",
    "DEFAULT_LANGUAGE",
]
