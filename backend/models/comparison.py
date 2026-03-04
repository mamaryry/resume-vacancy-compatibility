"""
Модель ResumeComparison для хранения сохранённых представлений сравнения резюме
"""
from typing import Optional
from uuid import UUID

from sqlalchemy import ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, UUIDMixin


class ResumeComparison(Base, UUIDMixin, TimestampMixin):
    """
    Модель ResumeComparison для хранения сохранённых представлений сравнения нескольких резюме

    Attributes:
        id: Первичный ключ UUID
        vacancy_id: Внешний ключ к JobVacancy
        resume_ids: JSON-массив ID сравниваемых резюме
        filters: JSON-объект с настройками фильтров (диапазон совпадения, поле сортировки и т.д.)
        created_by: Идентификатор пользователя, создавшего сравнение
        shared_with: JSON-массив ID пользователей/email, с которыми поделено сравнение
        created_at: Временная метка создания сравнения (унаследовано)
        updated_at: Временная метка последнего обновления сравнения (унаследовано)
    """

    __tablename__ = "resume_comparisons"

    vacancy_id: Mapped[UUID] = mapped_column(
        ForeignKey("job_vacancies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    resume_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    filters: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    shared_with: Mapped[Optional[list]] = mapped_column(JSON, nullable=True, default=list)

    def __repr__(self) -> str:
        return f"<ResumeComparison(id={self.id}, vacancy_id={self.vacancy_id}, resumes={len(self.resume_ids)})>"
