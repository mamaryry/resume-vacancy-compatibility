"""
Модель SearchAlert для уведомлений, когда новые резюме совпадают с сохранёнными поисками
"""
from typing import Optional
from uuid import UUID

from sqlalchemy import ForeignKey, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, UUIDMixin


class SearchAlert(Base, UUIDMixin, TimestampMixin):
    """
    Модель SearchAlert для уведомлений, когда новые резюме совпадают с сохранёнными поисками

    Attributes:
        id: Первичный ключ UUID
        saved_search_id: Внешний ключ к SavedSearch
        resume_id: Внешний ключ к Resume
        is_sent: Было ли отправлено уведомление
        sent_at: Время отправки уведомления
        error_message: Сообщение об ошибке, если отправка уведомления не удалась
        created_at: Время создания оповещения (унаследовано)
        updated_at: Время последнего обновления оповещения (унаследовано)
    """

    __tablename__ = "search_alerts"

    saved_search_id: Mapped[UUID] = mapped_column(
        ForeignKey("saved_searches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    resume_id: Mapped[UUID] = mapped_column(
        ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    is_sent: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false", index=True)
    sent_at: Mapped[Optional[object]] = mapped_column(
        nullable=True
    )  # DateTime timezone=True type
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<SearchAlert(id={self.id}, saved_search_id={self.saved_search_id}, is_sent={self.is_sent})>"
