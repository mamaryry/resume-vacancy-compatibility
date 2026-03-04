"""
Модели Report и ScheduledReport для пользовательских конфигураций отчётов
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, UUIDMixin


class Report(Base, UUIDMixin, TimestampMixin):
    """
    Модель Report для хранения пользовательских конфигураций отчётов

    Attributes:
        id: Первичный ключ UUID
        organization_id: Внешний ключ или ссылка на организацию
        name: Человекочитаемое имя отчёта
        description: Опциональное описание цели отчёта
        report_type: Тип отчёта (hiring_pipeline, skill_demand, source_effectiveness, diversity_metrics, custom)
        configuration: JSON-объект, содержащий фильтры, измерения, метрики и настройки визуализации
        created_by: ID пользователя, создавшего конфигурацию отчёта
        is_active: Активна ли эта конфигурация отчёта
        created_at: Временная метка создания записи (унаследовано)
        updated_at: Временная метка последнего обновления записи (унаследовано)
    """

    __tablename__ = "reports"

    organization_id: Mapped[str] = mapped_column(nullable=False, index=True)
    name: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[Optional[str]] = mapped_column(nullable=True)
    report_type: Mapped[str] = mapped_column(nullable=False, index=True)
    configuration: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_by: Mapped[Optional[str]] = mapped_column(nullable=True)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)

    def __repr__(self) -> str:
        return f"<Report(id={self.id}, org={self.organization_id}, name={self.name}, type={self.report_type})>"


class ScheduledReport(Base, UUIDMixin, TimestampMixin):
    """
    Модель ScheduledReport для планирования автоматической генерации и доставки отчётов

    Attributes:
        id: Первичный ключ UUID
        organization_id: Внешний ключ или ссылка на организацию
        report_id: Ссылка на конфигурацию Report для использования
        name: Человекочитаемое имя запланированного отчёта
        schedule_config: JSON-объект, содержащий частоту, часовой пояс и настройки расписания
        delivery_config: JSON-объект, содержащий способ доставки (email, Slack и т.д.) и настройки
        recipients: JSON-массив ID пользователей или email-адресов для получения отчёта
        created_by: ID пользователя, создавшего запланированный отчёт
        is_active: Активен ли этот запланированный отчёт
        next_run_at: Временная метка следующей генерации отчёта
        last_run_at: Временная метка последней генерации отчёта
        created_at: Временная метка создания записи (унаследовано)
        updated_at: Временная метка последнего обновления записи (унаследовано)
    """

    __tablename__ = "scheduled_reports"

    organization_id: Mapped[str] = mapped_column(nullable=False, index=True)
    report_id: Mapped[str] = mapped_column(ForeignKey("reports.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(nullable=False)
    schedule_config: Mapped[dict] = mapped_column(JSON, nullable=False)
    delivery_config: Mapped[dict] = mapped_column(JSON, nullable=False)
    recipients: Mapped[list] = mapped_column(JSON, nullable=False)
    created_by: Mapped[Optional[str]] = mapped_column(nullable=True)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)
    next_run_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    last_run_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    def __repr__(self) -> str:
        return f"<ScheduledReport(id={self.id}, org={self.organization_id}, name={self.name}, report_id={self.report_id})>"
