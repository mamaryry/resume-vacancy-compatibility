"""
Конфигурация приложения с использованием переменных окружения.

Этот модуль использует pydantic-settings для загрузки и проверки конфигурации
из переменных окружения с разумными значениями по умолчанию.
"""
import logging
from pathlib import Path
from typing import List, Optional

from pydantic import AnyUrl, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """
    Настройки приложения, загружаемые из переменных окружения.

    Attributes:
        database_url: URL подключения к базе данных PostgreSQL
        redis_url: URL подключения к Redis для Celery
        backend_host: Хост для привязки сервера FastAPI
        backend_port: Порт для привязки сервера FastAPI
        frontend_url: URL фронтенда для настройки CORS
        models_cache_path: Путь к кэшу ML-моделей
        languagetool_server: URL сервера LanguageTool для проверки грамматики
        max_upload_size_mb: Максимальный размер загружаемого файла в мегабайтах
        allowed_file_types: Список разрешённых расширений файлов через запятую
        analysis_timeout_seconds: Максимальное время анализа резюме
        log_level: Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        celery_broker_url: URL брокера Celery
        celery_result_backend: URL бэкенда результатов Celery
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Конфигурация базы данных
    database_url: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/resume_analysis",
        description="URL подключения к базе данных PostgreSQL",
    )

    # Конфигурация Redis
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="URL подключения к Redis для кэширования и Celery",
    )

    # Конфигурация сервера бэкенда
    backend_host: str = Field(
        default="0.0.0.0",
        description="Хост для привязки сервера FastAPI",
    )
    backend_port: int = Field(
        default=8000,
        description="Порт для привязки сервера FastAPI",
    )

    # Конфигурация фронтенда для CORS
    frontend_url: str = Field(
        default="http://localhost:5173",
        description="URL фронтенда для настройки CORS",
    )

    # Конфигурация ML-моделей
    models_cache_path: Path = Field(
        default=Path("./models_cache"),
        description="Путь к кэшу ML-моделей",
    )

    # Конфигурация сервера LanguageTool
    languagetool_server: Optional[str] = Field(
        default=None,
        description="URL сервера LanguageTool для проверки грамматики",
    )

    # Конфигурация загрузки файлов
    max_upload_size_mb: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Максимальный размер загружаемого файла в мегабайтах",
    )

    allowed_file_types: str = Field(
        default=".pdf,.docx",
        description="Разрешённые расширения файлов для загрузки (через запятую)",
    )

    # Конфигурация анализа
    analysis_timeout_seconds: int = Field(
        default=300,
        ge=30,
        le=600,
        description="Максимальное время анализа резюме в секундах",
    )

    # Конфигурация логирования
    log_level: str = Field(
        default="INFO",
        description="Уровень логирования",
    )

    # Конфигурация Celery
    celery_broker_url: str = Field(
        default="redis://localhost:6379/0",
        description="URL брокера Celery",
    )

    celery_result_backend: str = Field(
        default="redis://localhost:6379/0",
        description="URL бэкенда результатов Celery",
    )

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Проверить формат URL базы данных."""
        if not v.startswith(("postgresql://", "postgresql+async://")):
            logger.warning(
                f"URL базы данных должен начинаться с 'postgresql://' или 'postgresql+async://', получено: {v[:20]}..."
            )
        return v

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Проверить и привести уровень логирования к верхнему регистру."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in valid_levels:
            logger.warning(f"Неверный уровень логирования '{v}', используется значение по умолчанию INFO")
            return "INFO"
        return v_upper

    @property
    def max_upload_size_bytes(self) -> int:
        """Преобразовать max_upload_size_mb в байты."""
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def cors_origins(self) -> List[str]:
        """Получить список разрешённых источников CORS."""
        return [
            self.frontend_url,
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]

    def get_db_url_async(self) -> str:
        """
        Получить асинхронный URL базы данных для асинхронного движка SQLAlchemy.

        Returns:
            Асинхронный URL базы данных с драйвером asyncpg
        """
        if self.database_url.startswith("postgresql://"):
            return self.database_url.replace("postgresql://", "postgresql+asyncpg://")
        return self.database_url


# Глобальный экземпляр настроек
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """
    Получить или создать глобальный экземпляр настроек.

    Returns:
        Экземпляр настроек приложения

    Example:
        >>> settings = get_settings()
        >>> print(settings.database_url)
    """
    global _settings
    if _settings is None:
        _settings = Settings()
        logger.info(f"Загружена конфигурация приложения (log_level={_settings.log_level})")
    return _settings
