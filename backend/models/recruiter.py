"""
Модель Recruiter для отслеживания атрибуции и производительности рекрутёров
"""
from typing import Optional

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, UUIDMixin


class Recruiter(Base, UUIDMixin, TimestampMixin):
    """
    Модель Recruiter для отслеживания атрибуции и производительности рекрутёров

    Эта модель обеспечивает аналитику производительности рекрутёров,
    отслеживая отдельных рекрутёров и связанные с ними метрики,
    такие как time-to-hire, показатели размещения и уровни активности.

    Attributes:
        id: Первичный ключ UUID
        name: Полное имя рекрутёра
        email: Контактный email рекрутёра (уникальный)
        department: Опциональное название отдела или команды
        is_active: Активен ли рекрутёр в настоящее время
        created_at: Временная метка создания рекрутёра (унаследовано от TimestampMixin)
        updated_at: Временная метка последнего обновления рекрутёра (унаследовано от TimestampMixin)
    """

    __tablename__ = "recruiters"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    department: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    def __repr__(self) -> str:
        return f"<Recruiter(id={self.id}, name={self.name}, email={self.email})>"
