"""
Модель AnalyticsEvent для отслеживания событий аналитики по времени
"""
import enum
from typing import Optional
from uuid import UUID

from sqlalchemy import ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, UUIDMixin


class AnalyticsEventType(str, enum.Enum):
    """Типы событий аналитики, которые можно отслеживать"""

    RESUME_UPLOADED = "resume_uploaded"
    RESUME_PROCESSED = "resume_processed"
    STAGE_CHANGED = "stage_changed"
    MATCH_CREATED = "match_created"
    MATCH_VIEWED = "match_viewed"
    VACANCY_CREATED = "vacancy_created"
    VACANCY_FILLED = "vacancy_filled"
    FEEDBACK_SUBMITTED = "feedback_submitted"
    REPORT_GENERATED = "report_generated"
    REPORT_EXPORTED = "report_exported"


class AnalyticsEvent(Base, UUIDMixin, TimestampMixin):
    """
    Модель AnalyticsEvent для отслеживания событий аналитики по времени

    Эта модель обеспечивает комплексную аналитику, записывая события,
    происходящие в системе, что позволяет метрикам time-to-hire,
    визуализации воронки, отслеживанию источников, анализу спроса на навыки
    и метрикам производительности рекрутёров.

    Attributes:
        id: Первичный ключ UUID
        event_type: Тип события аналитики
        entity_type: Тип сущности, к которой относится событие (resume, vacancy, match и т.д.)
        entity_id: ID связанной сущности
        user_id: Опциональный внешний ключ к пользователю, инициировавшему событие
        recruiter_id: Опциональный внешний ключ к Recruiter
        session_id: Опциональный ID сессии для группировки связанных событий
        event_data: JSON-объект со специфичными для события данными
        created_at: Временная метка записи события (унаследовано)
        updated_at: Временная метка последнего обновления события (унаследовано)
    """

    __tablename__ = "analytics_events"

    event_type: Mapped[AnalyticsEventType] = mapped_column(
        String(50), nullable=False, index=True
    )
    entity_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    entity_id: Mapped[Optional[UUID]] = mapped_column(nullable=True, index=True)
    user_id: Mapped[Optional[UUID]] = mapped_column(nullable=True, index=True)
    recruiter_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("recruiters.id", ondelete="SET NULL"), nullable=True, index=True
    )
    session_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    event_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    def __repr__(self) -> str:
        return f"<AnalyticsEvent(id={self.id}, type={self.event_type}, entity={self.entity_type})>"
