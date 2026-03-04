"""
Модель HiringStage для отслеживания прогресса резюме через воронку найма
"""
import enum
from typing import Optional
from uuid import UUID

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, UUIDMixin


class HiringStageName(str, enum.Enum):
    """Этапы воронки найма"""

    APPLIED = "applied"
    SCREENING = "screening"
    INTERVIEW = "interview"
    TECHNICAL = "technical"
    OFFER = "offer"
    HIRED = "hired"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class HiringStage(Base, UUIDMixin, TimestampMixin):
    """
    Модель HiringStage для отслеживания прогресса резюме через воронку найма

    Эта модель позволяет аналитику воронки и метрикам time-to-hire,
    записывая каждый этап, через который проходит резюме в процессе найма.

    Attributes:
        id: Первичный ключ UUID
        resume_id: Внешний ключ к Resume
        vacancy_id: Опциональный внешний ключ к JobVacancy
        stage_name: Текущий этап найма
        notes: Опциональные заметки о переходе этапа
        created_at: Временная метка создания записи этапа (унаследовано)
        updated_at: Временная метка последнего обновления записи этапа (унаследовано)
    """

    __tablename__ = "hiring_stages"

    resume_id: Mapped[UUID] = mapped_column(
        ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    vacancy_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("job_vacancies.id", ondelete="SET NULL"), nullable=True, index=True
    )
    stage_name: Mapped[HiringStageName] = mapped_column(
        Enum(HiringStageName), default=HiringStageName.APPLIED, nullable=False, index=True
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<HiringStage(id={self.id}, resume_id={self.resume_id}, stage={self.stage_name})>"
