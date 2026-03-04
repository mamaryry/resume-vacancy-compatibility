"""
Модель JobVacancy для хранения описаний вакансий
"""
from typing import Optional

from sqlalchemy import JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, UUIDMixin


class JobVacancy(Base, UUIDMixin, TimestampMixin):
    """
    Модель JobVacancy для хранения вакансий для сопоставления с резюме

    Attributes:
        id: Первичный ключ UUID
        title: Должность
        description: Полное описание вакансии
        required_skills: JSON-массив обязательных навыков
        min_experience_months: Минимальный требуемый опыт в месяцах
        additional_requirements: JSON-массив дополнительных (желательных) навыков
        industry: Отрасль
        work_format: Формат работы (удалённо, офис, гибрид)
        location: Требуемая локация (если есть)
        external_id: ID внешней системы (например, из API job-boards)
        source: Источник вакансии (manual, api, scrape)
        created_at: Временная метка создания вакансии (унаследовано)
    """

    __tablename__ = "job_vacancies"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    required_skills: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    min_experience_months: Mapped[Optional[int]] = mapped_column(
        nullable=True, default=None
    )
    additional_requirements: Mapped[Optional[list]] = mapped_column(
        JSON, nullable=True, default=list
    )
    industry: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    work_format: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    salary_min: Mapped[Optional[int]] = mapped_column(
        nullable=True, default=None
    )
    salary_max: Mapped[Optional[int]] = mapped_column(
        nullable=True, default=None
    )
    english_level: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    employment_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    external_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    source: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    def __repr__(self) -> str:
        return f"<JobVacancy(id={self.id}, title={self.title})>"
