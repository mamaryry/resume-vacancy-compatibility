"""
Модель MatchResult для хранения результатов сопоставления резюме и вакансии
"""
from typing import Optional
from uuid import UUID

from sqlalchemy import ForeignKey, JSON, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, UUIDMixin


class MatchResult(Base, UUIDMixin, TimestampMixin):
    """
    Модель MatchResult для хранения результатов сопоставления резюме с вакансией

    Attributes:
        id: Первичный ключ UUID
        resume_id: Внешний ключ к Resume
        vacancy_id: Внешний ключ к JobVacancy
        match_percentage: Общая оценка совпадения (0-100) - устаревшее поле
        matched_skills: JSON-массив навыков, найденных в резюме с метаданными
        missing_skills: JSON-массив обязательных навыков, не найденных в резюме
        additional_skills_matched: JSON-массив дополнительных совпавших навыков
        experience_verified: Были ли выполнены требования к опыту
        experience_details: JSON-объект с разбивкой опыта по навыкам

        # Метрики унифицированного сопоставления
        overall_score: Комбинированная оценка от всех методов (0-1)
        keyword_score: Оценка улучшенного сопоставления по ключевым словам (0-1)
        tfidf_score: Взвешенная оценка TF-IDF (0-1)
        vector_score: Оценка семантической схожести (0-1)
        vector_similarity: Сырая косинусная схожесть (-1 до 1)
        recommendation: Рекомендация по найму (excellent/good/maybe/poor)
        keyword_passed: Был ли превышен порог сопоставления по ключевым словам
        tfidf_passed: Был ли превышен порог TF-IDF
        vector_passed: Был ли превышен порог векторного сопоставления
        tfidf_matched: JSON-массив совпавших ключевых слов из TF-IDF
        tfidf_missing: JSON-массив отсутствующих ключевых слов из TF-IDF
        matcher_version: Версия использованного сопоставителя

        created_at: Временная метка вычисления сопоставления (унаследовано)
        updated_at: Временная метка последнего обновления сопоставления (унаследовано)
    """

    __tablename__ = "match_results"

    resume_id: Mapped[UUID] = mapped_column(
        ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    vacancy_id: Mapped[UUID] = mapped_column(
        ForeignKey("job_vacancies.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Устаревшие поля
    match_percentage: Mapped[float] = mapped_column(
        Numeric(5, 2), nullable=False, default=0.0
    )
    matched_skills: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    missing_skills: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    additional_skills_matched: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    experience_verified: Mapped[Optional[bool]] = mapped_column(nullable=True, default=None)
    experience_details: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Метрики унифицированного сопоставления
    overall_score: Mapped[Optional[float]] = mapped_column(
        Numeric(5, 4), nullable=True, default=None
    )
    keyword_score: Mapped[Optional[float]] = mapped_column(
        Numeric(5, 4), nullable=True, default=None
    )
    tfidf_score: Mapped[Optional[float]] = mapped_column(
        Numeric(5, 4), nullable=True, default=None
    )
    vector_score: Mapped[Optional[float]] = mapped_column(
        Numeric(5, 4), nullable=True, default=None
    )
    vector_similarity: Mapped[Optional[float]] = mapped_column(
        Numeric(5, 4), nullable=True, default=None
    )
    recommendation: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True, default=None
    )
    keyword_passed: Mapped[Optional[bool]] = mapped_column(nullable=True, default=None)
    tfidf_passed: Mapped[Optional[bool]] = mapped_column(nullable=True, default=None)
    vector_passed: Mapped[Optional[bool]] = mapped_column(nullable=True, default=None)
    tfidf_matched: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    tfidf_missing: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    matcher_version: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, default="unified-v1"
    )

    def __repr__(self) -> str:
        return (
            f"<MatchResult(id={self.id}, resume_id={self.resume_id}, "
            f"vacancy_id={self.vacancy_id}, overall_score={self.overall_score})>"
        )
