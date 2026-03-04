"""
Модель SkillFeedback для хранения отзывов рекрутёров о сопоставлении навыков
"""
from typing import Optional
from uuid import UUID

from sqlalchemy import ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, UUIDMixin


class SkillFeedback(Base, UUIDMixin, TimestampMixin):
    """
    Модель SkillFeedback для хранения отзывов рекрутёров о сопоставлении навыков

    Attributes:
        id: Первичный ключ UUID
        resume_id: Внешний ключ к Resume
        vacancy_id: Внешний ключ к JobVacancy
        match_result_id: Опциональный внешний ключ к MatchResult
        skill: Имя навыка, который был сопоставлен
        was_correct: Было ли сопоставление ИИ корректным
        confidence_score: Оценка уверенности, назначенная ИИ (0-1)
        recruiter_correction: На что рекрутёр исправил значение (если неверно)
        actual_skill: Фактический навык, найденный рекрутёром
        feedback_source: Источник отзыва (api, frontend, bulk_import)
        processed: Был ли отзыв обработан ML-конвейером
        extra_metadata: JSON-объект с дополнительными метаданными отзыва
        created_at: Временная метка отправки отзыва (унаследовано)
        updated_at: Временная метка последнего обновления отзыва (унаследовано)
    """

    __tablename__ = "skill_feedback"

    resume_id: Mapped[UUID] = mapped_column(
        ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    vacancy_id: Mapped[UUID] = mapped_column(
        ForeignKey("job_vacancies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    match_result_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("match_results.id", ondelete="SET NULL"), nullable=True
    )
    skill: Mapped[str] = mapped_column(String(255), nullable=False)
    was_correct: Mapped[bool] = mapped_column(nullable=False)
    confidence_score: Mapped[Optional[float]] = mapped_column(nullable=True)
    recruiter_correction: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    actual_skill: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    feedback_source: Mapped[str] = mapped_column(
        String(50), nullable=False, default="api"
    )
    processed: Mapped[bool] = mapped_column(nullable=False, default=False)
    extra_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    def __repr__(self) -> str:
        return f"<SkillFeedback(id={self.id}, skill={self.skill}, correct={self.was_correct})>"
