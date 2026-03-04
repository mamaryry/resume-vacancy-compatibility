"""
Модель SkillTaxonomy для хранения отраслевых таксономий навыков
"""
from typing import Optional

from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, UUIDMixin


class SkillTaxonomy(Base, UUIDMixin, TimestampMixin):
    """
    Модель SkillTaxonomy для хранения отраслевых таксономий навыков

    Attributes:
        id: Первичный ключ UUID
        industry: Отрасль (tech, healthcare, finance и т.д.)
        skill_name: Каноническое имя навыка
        context: Категория контекста (например, web_framework, language, database)
        variants: JSON-массив альтернативных имён/написаний для этого навыка
        extra_metadata: JSON-объект с дополнительными метаданными навыка (description, category и т.д.)
        is_active: Активна ли эта запись таксономии
        created_at: Временная метка создания записи (унаследовано)
        updated_at: Временная метка последнего обновления записи (унаследовано)
    """

    __tablename__ = "skill_taxonomies"

    industry: Mapped[str] = mapped_column(nullable=False, index=True)
    skill_name: Mapped[str] = mapped_column(nullable=False, index=True)
    context: Mapped[Optional[str]] = mapped_column(nullable=True)
    variants: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    extra_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)

    def __repr__(self) -> str:
        return f"<SkillTaxonomy(id={self.id}, industry={self.industry}, skill={self.skill_name})>"
