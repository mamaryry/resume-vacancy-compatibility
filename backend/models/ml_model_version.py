"""
Модель MLModelVersion для хранения информации о версионности ML-моделей
"""
from typing import Optional

from sqlalchemy import JSON, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, UUIDMixin


class MLModelVersion(Base, UUIDMixin, TimestampMixin):
    """
    Модель MLModelVersion для хранения версионности ML-моделей и информации A/B-тестирования

    Attributes:
        id: Первичный ключ UUID
        model_name: Имя модели (например, skill_matching, resume_parser)
        version: Идентификатор версии (например, v1.0.0, v2.1.3)
        is_active: Активна ли эта версия модели
        is_experiment: Является ли это экспериментальной моделью для A/B-тестирования
        experiment_config: JSON-объект с конфигурацией A/B-тестирования (traffic_percentage и т.д.)
        model_metadata: JSON-объект с метаданными обучения модели (algorithm, training_date и т.д.)
        accuracy_metrics: JSON-объект с метриками точности (precision, recall, f1_score и т.д.)
        file_path: Путь к файлу модели в хранилище
        performance_score: Общая оценка производительности (0-100)
        created_at: Временная метка создания версии модели (унаследовано)
        updated_at: Временная метка последнего обновления версии модели (унаследовано)
    """

    __tablename__ = "ml_model_versions"

    model_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=False)
    is_experiment: Mapped[bool] = mapped_column(nullable=False, default=False)
    experiment_config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    model_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    accuracy_metrics: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    performance_score: Mapped[Optional[float]] = mapped_column(
        Numeric(5, 2), nullable=True
    )

    def __repr__(self) -> str:
        status = "active" if self.is_active else "inactive"
        exp = " [experiment]" if self.is_experiment else ""
        return f"<MLModelVersion(id={self.id}, name={self.model_name}, version={self.version}, status={status}{exp})>"
