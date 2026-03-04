"""
Модель UserPreferences для хранения языковых и локальных настроек пользователя
"""
from typing import Optional

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, UUIDMixin


class UserPreferences(Base, UUIDMixin, TimestampMixin):
    """
    Модель UserPreferences для хранения языковых настроек и локали пользователя

    Attributes:
        id: Первичный ключ UUID
        language: Код предпочитаемого языка пользователя (en, ru и т.д.)
        timezone: Предпочитаемый часовой пояс (опционально)
        created_at: Временная метка создания предпочтения (унаследовано от TimestampMixin)
        updated_at: Временная метка последнего обновления предпочтения (унаследовано от TimestampMixin)
    """

    __tablename__ = "user_preferences"

    language: Mapped[str] = mapped_column(String(10), nullable=False, default="en", index=True)
    timezone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    def __repr__(self) -> str:
        return f"<UserPreferences(id={self.id}, language={self.language})>"
