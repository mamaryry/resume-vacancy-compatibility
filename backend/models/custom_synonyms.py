"""
Модель CustomSynonym для хранения специфичных для организации синонимов навыков
"""
from typing import Optional

from sqlalchemy import ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, UUIDMixin


class CustomSynonym(Base, UUIDMixin, TimestampMixin):
    """
    Модель CustomSynonym для хранения специфичных для организации синонимов навыков

    Attributes:
        id: Первичный ключ UUID
        organization_id: Внешний ключ или ссылка на организацию
        canonical_skill: Каноническое/стандартное имя навыка
        custom_synonyms: JSON-массив специфичных для организации синонимов
        context: Опциональный контекст использования этих синонимов
        created_by: ID пользователя, создавшего отображение синонимов
        is_active: Активно ли это отображение синонимов
        created_at: Временная метка создания записи (унаследовано)
        updated_at: Временная метка последнего обновления записи (унаследовано)
    """

    __tablename__ = "custom_synonyms"

    organization_id: Mapped[str] = mapped_column(nullable=False, index=True)
    canonical_skill: Mapped[str] = mapped_column(nullable=False)
    custom_synonyms: Mapped[list] = mapped_column(JSON, nullable=False)
    context: Mapped[Optional[str]] = mapped_column(nullable=True)
    created_by: Mapped[Optional[str]] = mapped_column(nullable=True)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)

    def __repr__(self) -> str:
        return f"<CustomSynonym(id={self.id}, org={self.organization_id}, skill={self.canonical_skill})>"
