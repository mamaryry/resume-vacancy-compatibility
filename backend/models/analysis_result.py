"""
Модель AnalysisResult для хранения результатов анализа резюме
"""
from typing import Optional
from uuid import UUID

from sqlalchemy import ForeignKey, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, UUIDMixin


class AnalysisResult(Base, UUIDMixin, TimestampMixin):
    """
    Модель AnalysisResult для хранения результатов NLP/ML анализа

    Attributes:
        id: Первичный ключ UUID
        resume_id: Внешний ключ к Resume
        errors: JSON-массив обнаруженных ошибок (грамматика, орфография, отсутствующие элементы)
        skills: JSON-массив извлечённых навыков
        experience_summary: JSON-объект с общим опытом и разбивкой по навыкам
        recommendations: JSON-массив рекомендаций по улучшению
        keywords: JSON-массив извлечённых ключевых слов с оценками
        entities: JSON-объект с именованными сущностями (организации, даты, образование)
        created_at: Временная метка создания анализа (унаследовано)
    """

    __tablename__ = "analysis_results"

    resume_id: Mapped[UUID] = mapped_column(
        ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    errors: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    skills: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    experience_summary: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    recommendations: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    keywords: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    entities: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    def __repr__(self) -> str:
        return f"<AnalysisResult(id={self.id}, resume_id={self.resume_id})>"
