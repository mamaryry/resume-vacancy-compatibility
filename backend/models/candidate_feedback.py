"""
Модель CandidateFeedback для хранения конструктивной обратной связи для кандидатов
"""
from typing import Optional
from uuid import UUID

from sqlalchemy import ForeignKey, JSON, String, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, UUIDMixin


class CandidateFeedback(Base, UUIDMixin, TimestampMixin):
    """
    Модель CandidateFeedback для хранения конструктивной обратной связи для кандидатов

    Attributes:
        id: Первичный ключ UUID
        resume_id: Внешний ключ к Resume
        vacancy_id: Внешний ключ к JobVacancy
        match_result_id: Внешний ключ к MatchResult
        template_id: Внешний ключ к FeedbackTemplate
        language: Код языка для обратной связи (например, 'en', 'ru')
        grammar_feedback: JSON-объект с обратной связью по грамматике
        skills_feedback: JSON-объект с обратной связью по навыкам
        experience_feedback: JSON-объект с обратной связью по опыту
        recommendations: JSON-массив с рекомендациями
        match_score: Общий балл соответствия
        tone: Тон обратной связи
        feedback_source: Источник обратной связи (автоматическая, ручная)
        viewed_by_candidate: Просмотрел ли кандидат обратную связь
        downloaded: Была ли скачана обратная связь
        extra_metadata: Дополнительные метаданные в формате JSON
        created_at: Время создания обратной связи (унаследовано)
        updated_at: Время последнего обновления обратной связи (унаследовано)
    """

    __tablename__ = "candidate_feedback"

    resume_id: Mapped[UUID] = mapped_column(
        ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    vacancy_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("job_vacancies.id", ondelete="SET NULL"), nullable=True, index=True
    )
    match_result_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("match_results.id", ondelete="SET NULL"), nullable=True
    )
    template_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("feedback_templates.id", ondelete="SET NULL"), nullable=True
    )
    language: Mapped[str] = mapped_column(String(10), nullable=False, server_default="en")
    grammar_feedback: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    skills_feedback: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    experience_feedback: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    recommendations: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    match_score: Mapped[Optional[int]] = mapped_column(nullable=True)
    tone: Mapped[str] = mapped_column(String(50), nullable=False, server_default="constructive")
    feedback_source: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default="automated"
    )
    viewed_by_candidate: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    downloaded: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    extra_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    def __repr__(self) -> str:
        return f"<CandidateFeedback(id={self.id}, resume_id={self.resume_id}, language={self.language})>"
