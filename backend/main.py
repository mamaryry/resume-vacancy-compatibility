"""
Приложение FastAPI для системы анализа резюме.

Этот модуль предоставляет основное приложение FastAPI с middleware CORS,
управлением сессиями базы данных и эндпоинтами проверки работоспособности.
"""
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from config import get_settings
from database import init_db

logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """
    Контекстный менеджер жизненного цикла приложения для запуска и остановки.

    Обрабатывает инициализацию пула подключений к базе данных и его очистку.

    Yields:
        None

    Example:
        Lifespan автоматически вызывается FastAPI при запуске/остановке.
    """
    # Запуск
    logger.info("Запуск API анализа резюме")

    # Инициализация базы данных и создание таблиц
    await init_db(create_tables=True)

    logger.info(f"URL базы данных: {settings.database_url[:30]}...")
    logger.info(f"CORS источники: {settings.cors_origins}")
    logger.info(f"Макс. размер загрузки: {settings.max_upload_size_mb}МБ")
    logger.info(f"Разрешённые типы файлов: {settings.allowed_file_types}")

    # Инициализация директории кэша моделей
    settings.models_cache_path.mkdir(parents=True, exist_ok=True)
    logger.info(f"Директория кэша моделей: {settings.models_cache_path}")

    yield

    # Остановка
    logger.info("Остановка API анализа резюме")


# Создание приложения FastAPI
app = FastAPI(
    title="Resume Analysis API",
    description="API для анализа резюме и подбора вакансий на основе ИИ",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)


# Настройка CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=[
        "Content-Type",
        "Authorization",
        "X-Requested-With",
        "Accept",
        "Origin",
        "Access-Control-Request-Method",
        "Access-Control-Request-Headers",
    ],
)


# Обработчики исключений
@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """
    Обработка ошибок базы данных SQLAlchemy.

    Args:
        request: Входящий запрос
        exc: Исключение SQLAlchemy

    Returns:
        JSON-ответ с деталями ошибки
    """
    logger.error(f"Ошибка базы данных: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Произошла ошибка базы данных",
            "detail": "Возникла ошибка при доступе к базе данных",
            "type": "database_error",
        },
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    """
    Обработка ошибок валидации значений.

    Args:
        request: Входящий запрос
        exc: Исключение ValueError

    Returns:
        JSON-ответ с деталями ошибки
    """
    logger.warning(f"Ошибка валидации: {exc}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Ошибка валидации",
            "detail": str(exc),
            "type": "validation_error",
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Обработка всех остальных исключений.

    Args:
        request: Входящий запрос
        exc: Исключение

    Returns:
        JSON-ответ с деталями ошибки
    """
    logger.error(f"Неожиданная ошибка: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Внутренняя ошибка сервера",
            "detail": "Произошла неожиданная ошибка. Пожалуйста, попробуйте позже.",
            "type": "internal_error",
        },
    )


# Эндпоинты проверки работоспособности
@app.get("/health", tags=["Health"])
async def health_check() -> JSONResponse:
    """
    Эндпоинт проверки работоспособности.

    Возвращает текущий статус API. Этот эндпоинт может использоваться
    инструментами мониторинга для проверки работы API.

    Returns:
        JSON-ответ со статусом работоспособности

    Example:
        >>> curl http://localhost:8000/health
        {"status":"healthy","service":"resume-analysis-api","version":"1.0.0"}
    """
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": "healthy",
            "service": "resume-analysis-api",
            "version": "1.0.0",
        },
    )


@app.get("/ready", tags=["Health"])
async def readiness_check() -> JSONResponse:
    """
    Эндпоинт проверки готовности.

    Проверяет, готов ли API обрабатывать запросы. Сейчас проверяется
    базовый статус API. В будущих версиях можно добавить проверки подключения к базе данных.

    Returns:
        JSON-ответ со статусом готовности

    Example:
        >>> curl http://localhost:8000/ready
        {"status":"ready"}
    """
    # TODO: Добавить проверку подключения к базе данных
    # TODO: Добавить проверку подключения к Redis
    # TODO: Добавить проверку доступности ML-моделей

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"status": "ready"},
    )


@app.get("/", tags=["Root"])
async def root() -> JSONResponse:
    """
    Корневой эндпоинт с информацией об API.

    Returns:
        JSON-ответ с информацией об API и ссылками

    Example:
        >>> curl http://localhost:8000/
        {
          "message": "Resume Analysis API",
          "version": "1.0.0",
          "docs": "/docs",
          "health": "/health"
        }
    """
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "Resume Analysis API",
            "version": "1.0.0",
            "docs": "/docs",
            "redoc": "/redoc",
            "health": "/health",
            "ready": "/ready",
        },
    )


# Подключение API-роутеров
from api import (
    resumes,
    analysis,
    matching,
    skill_taxonomies,
    custom_synonyms,
    feedback,
    model_versions,
    comparisons,
    analytics,
    reports,
    vacancies,
)

app.include_router(resumes.router, prefix="/api/resumes", tags=["Resumes"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["Analysis"])
app.include_router(matching.router, prefix="/api/matching", tags=["Matching"])
app.include_router(skill_taxonomies.router, prefix="/api/skill-taxonomies", tags=["Skill Taxonomies"])
app.include_router(custom_synonyms.router, prefix="/api/custom-synonyms", tags=["Custom Synonyms"])
app.include_router(feedback.router, prefix="/api/feedback", tags=["Feedback"])
app.include_router(model_versions.router, prefix="/api/model-versions", tags=["Model Versions"])
app.include_router(comparisons.router, prefix="/api/comparisons", tags=["Comparisons"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])
app.include_router(reports.router, prefix="/api/reports", tags=["Reports"])
app.include_router(vacancies.router, prefix="/api/vacancies", tags=["Vacancies"])


if __name__ == "__main__":
    import uvicorn

    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    uvicorn.run(
        "main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=True,
        log_level=settings.log_level.lower(),
    )
