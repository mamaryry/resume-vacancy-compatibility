"""
Подключение к базе данных и управление сессиями для асинхронного SQLAlchemy.

Этот модуль предоставляет движок базы данных, фабрику сессий и внедрение
зависимостей для эндпоинтов FastAPI.
"""
import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import text

from config import get_settings
from models.base import Base

logger = logging.getLogger(__name__)
settings = get_settings()

# Создание асинхронного движка с драйвером asyncpg
engine = create_async_engine(
    settings.get_db_url_async(),
    echo=settings.log_level == "DEBUG",
    future=True,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

# Создание фабрики асинхронных сессий
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Внедрение зависимостей для сессий базы данных.

    Эта функция используется как зависимость FastAPI для предоставления
    сессий базы данных эндпоинтам. Автоматически обрабатывает очистку сессий.

    Yields:
        AsyncSession: Асинхронная сессия SQLAlchemy

    Example:
        @router.get("/")
        async def get_items(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Item))
            return result.scalars().all()
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db(create_tables: bool = True) -> None:
    """
    Инициализация подключения к базе данных и создание таблиц при необходимости.

    Эта функция может быть вызвана при запуске приложения для проверки
    подключения к базе данных и выполнения необходимых настроек.

    Args:
        create_tables: Если True, создать все таблицы. Установите в False для пропуска.
    """
    try:
        async with engine.begin() as conn:
            # Тестовое подключение
            await conn.execute(text("SELECT 1"))

            # Создание таблиц при необходимости
            if create_tables:
                # Импорт всех моделей, чтобы они были зарегистрированы в Base
                from models import (
                    Resume,
                    ResumeAnalysis,
                    AnalysisResult,
                    ResumeComparison,
                    JobVacancy,
                    MatchResult,
                    SkillTaxonomy,
                    CustomSynonym,
                    SkillFeedback,
                    MLModelVersion,
                    UserPreferences,
                    HiringStage,
                    AnalyticsEvent,
                    Recruiter,
                    Report,
                    ScheduledReport,
                )
                # Создание всех таблиц
                await conn.run_sync(Base.metadata.create_all)
                logger.info("Таблицы базы данных успешно созданы")

        logger.info("Подключение к базе данных успешно установлено")
    except Exception as e:
        logger.error(f"Не удалось подключиться к базе данных: {e}")
        raise


async def close_db() -> None:
    """
    Закрыть пул подключений к базе данных.

    Эта функция должна вызываться при остановке приложения.
    """
    try:
        await engine.dispose()
        logger.info("Пул подключений к базе данных закрыт")
    except Exception as e:
        logger.error(f"Ошибка закрытия базы данных: {e}")
