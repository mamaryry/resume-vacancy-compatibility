"""
Эндпоинты управления пользовательскими настройками.

Этот модуль предоставляет эндпоинты для управления пользовательскими настройками,
включая языковые предпочтения для локализации интерфейса.
"""
import logging
from typing import Dict, Literal

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter()

# Поддерживаемые языки
SupportedLanguage = Literal["en", "ru"]
DEFAULT_LANGUAGE: SupportedLanguage = "en"

# In-memory хранилище для языковых предпочтений (будет заменено на базу данных в будущем)
# Пока это простое глобальное состояние, которое можно расширить до пользовательских предпочтений
_current_language: SupportedLanguage = DEFAULT_LANGUAGE


class LanguagePreferenceResponse(BaseModel):
    """Модель ответа для эндпоинта языковых предпочтений."""

    language: SupportedLanguage = Field(..., description="Current language preference (en or ru)")


class LanguagePreferenceUpdate(BaseModel):
    """Модель запроса для обновления языковых предпочтений."""

    language: SupportedLanguage = Field(..., description="Language preference to set (en or ru)")


def validate_language(language: str) -> SupportedLanguage:
    """
    Проверить, что язык поддерживается.

    Args:
        language: Код языка для проверки

    Raises:
        HTTPException: Если язык не поддерживается
    """
    if language not in ["en", "ru"]:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported language '{language}'. Supported languages: en, ru",
        )
    return language  # type: ignore


@router.get(
    "/language",
    response_model=LanguagePreferenceResponse,
    status_code=status.HTTP_200_OK,
    tags=["Preferences"],
)
async def get_language_preference() -> JSONResponse:
    """
    Получить текущее языковое предпочтение.

    Возвращает текущий выбранный язык для интерфейса.
    По умолчанию 'en' (английский), если ранее не был установлен.

    Returns:
        JSON-ответ с текущим языковым предпочтением

    Raises:
        HTTPException(500): Если произошла внутренняя ошибка

    Examples:
        >>> import requests
        >>> response = requests.get("http://localhost:8000/api/preferences/language")
        >>> response.json()
        {
            "language": "en"
        }
    """
    try:
        logger.info(f"Retrieving language preference: {_current_language}")

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"language": _current_language},
        )

    except Exception as e:
        logger.error(f"Error retrieving language preference: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve language preference: {str(e)}",
        ) from e


@router.put(
    "/language",
    response_model=LanguagePreferenceResponse,
    status_code=status.HTTP_200_OK,
    tags=["Preferences"],
)
async def update_language_preference(request: LanguagePreferenceUpdate) -> JSONResponse:
    """
    Обновить языковое предпочтение.

    Устанавливает языковое предпочтение для интерфейса. Поддерживаемые языки:
    - 'en' (английский)
    - 'ru' (русский)

    Args:
        request: Тело запроса, содержащее язык для установки

    Returns:
        JSON-ответ с обновлённым языковым предпочтением

    Raises:
        HTTPException(422): Если язык не поддерживается
        HTTPException(500): Если произошла внутренняя ошибка

    Examples:
        >>> import requests
        >>> response = requests.put(
        ...     "http://localhost:8000/api/preferences/language",
        ...     json={"language": "ru"}
        ... )
        >>> response.json()
        {
            "language": "ru"
        }
    """
    global _current_language

    try:
        # Проверка языка
        language = validate_language(request.language)

        logger.info(f"Updating language preference from {_current_language} to {language}")

        # Обновление языкового предпочтения
        _current_language = language

        logger.info(f"Language preference updated successfully: {_current_language}")

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"language": _current_language},
        )

    except HTTPException:
        # Перебрасываем HTTP-исключения (ошибки валидации)
        raise
    except Exception as e:
        logger.error(f"Error updating language preference: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update language preference: {str(e)}",
        ) from e
