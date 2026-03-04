"""
Модуль задач Celery для асинхронной обработки.

Этот модуль предоставляет определения задач Celery для длительных операций,
таких как анализ резюме, сопоставление вакансий, пакетная обработка,
задачи ML-обучения и генерация отчётов.
"""
from .analysis_task import analyze_resume_async, batch_analyze_resumes
from .learning_tasks import (
    aggregate_feedback_and_generate_synonyms,
    review_and_activate_synonyms,
    periodic_feedback_aggregation,
    retrain_skill_matching_model,
)
from .report_generation import (
    generate_scheduled_reports,
    process_all_pending_reports,
)

__all__ = [
    "analyze_resume_async",
    "batch_analyze_resumes",
    "aggregate_feedback_and_generate_synonyms",
    "review_and_activate_synonyms",
    "periodic_feedback_aggregation",
    "retrain_skill_matching_model",
    "generate_scheduled_reports",
    "process_all_pending_reports",
]
