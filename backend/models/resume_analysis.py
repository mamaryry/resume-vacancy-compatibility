"""
Модель ResumeAnalysis для хранения результатов NLP/ML анализа

Эта таблица хранит извлечённую информацию из резюме, включая:
- Навыки и ключевые слова
- Именованные сущности (организации, даты, локации)
- Грамматические проблемы
- Расчёт опыта работы
- Метаданные анализа
"""
from typing import Optional
from uuid import UUID

from sqlalchemy import ForeignKey, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, UUIDMixin


class ResumeAnalysis(Base, UUIDMixin, TimestampMixin):
    """
    Модель ResumeAnalysis для хранения полных результатов анализа

    Эта таблица хранит результаты NLP/ML анализа, выполненного над резюме,
    что позволяет избежать повторного извлечения информации из
    исходного текста при каждом запросе.

    Attributes:
        id: Первичный ключ UUID
        resume_id: Внешний ключ к Resume
        language: Обнаруженный язык (en, ru и т.д.)
        raw_text: Извлеченный текст из резюме

        # Извлечённые данные
        skills: Список извлечённых технических навыков
        keywords: Список ключевых фраз с оценками релевантности
        entities: Именованные сущности (лица, организации, даты, локации)

        # Результаты анализа
        total_experience_months: Общий стаж работы в месяцах
        education: Извлечённая информация об образовании
        contact_info: Извлечённые email, телефон, ссылки

        # Метрики качества
        grammar_issues: Список найденных грамматических/орфографических ошибок
        warnings: Список обнаруженных проблем (отсутствие информации и т.д.)
        quality_score: Общая оценка качества резюме (0-100)

        # Метаданные обработки
        processing_time_seconds: Время, затраченное на анализ
        analyzer_version: Версия использованного анализатора
    """

    __tablename__ = "resume_analyses"

    # Ссылка на резюме
    resume_id: Mapped[UUID] = mapped_column(
        ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )

    # Язык и текст
    language: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    raw_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Извлечённые данные (JSON-поля для гибкости)
    skills: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    keywords: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    entities: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Результаты анализа
    total_experience_months: Mapped[Optional[int]] = mapped_column(nullable=True)
    education: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    contact_info: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Метрики качества
    grammar_issues: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    warnings: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    quality_score: Mapped[Optional[int]] = mapped_column(nullable=True)

    # Метаданные обработки
    processing_time_seconds: Mapped[Optional[float]] = mapped_column(nullable=True)
    analyzer_version: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<ResumeAnalysis(id={self.id}, resume_id={self.resume_id}, language={self.language})>"
