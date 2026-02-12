"""
Конфигурация Celery для асинхронной обработки задач.

Этот модуль предоставляет конфигурацию Celery, используя настройки из модуля
конфигурации приложения. Он настраивает брокер, бэкенд результатов и поведение задач.
"""
import logging
from typing import Dict, Any

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


# Словарь конфигурации Celery
# Эта конфигурация используется приложением Celery в tasks.py
celery_config: Dict[str, Any] = {
    # Настройки брокера
    "broker_url": settings.celery_broker_url,
    "result_backend": settings.celery_result_backend,
    "broker_connection_retry_on_startup": True,

    # Настройки задач
    "task_serializer": "json",
    "result_serializer": "json",
    "accept_content": ["json"],
    "timezone": "UTC",
    "enable_utc": True,

    # Настройки выполнения задач
    "task_acks_late": True,  # Подтверждение задачи после выполнения (надёжность)
    "task_reject_on_worker_lost": True,  # Повторная постановка задачи при смерти воркера
    "task_track_started": True,  # Отслеживание начала задач
    "task_time_limit": 3600,  # Жёсткий лимит: 1 час (60 минут * 60 секунд)
    "task_soft_time_limit": 3300,  # Мягкий лимит: 55 минут (позволяет корректное завершение)

    # Настройки результатов
    "result_expires": 86400,  # Результаты истекают через 24 часа (в секундах)
    "result_compression": "gzip",  # Сжатие результатов для экономии места

    # Настройки воркеров
    "worker_prefetch_multiplier": 1,  # Отключение префетчинга для долгих задач
    "worker_max_tasks_per_child": 100,  # Перезапуск воркера после 100 задач (управление памятью)

    # Маршрутизация задач (можно расширить для специфических очередей)
    "task_routes": {
        "tasks.analysis_task.analyze_resume_async": {"queue": "analysis"},
        "tasks.analysis_task.*": {"queue": "analysis"},
        "tasks.learning_tasks.aggregate_feedback_and_generate_synonyms": {"queue": "learning"},
        "tasks.learning_tasks.review_and_activate_synonyms": {"queue": "learning"},
        "tasks.learning_tasks.periodic_feedback_aggregation": {"queue": "learning"},
        "tasks.learning_tasks.*": {"queue": "learning"},
    },

    # Приоритет задач (если понадобится в будущем)
    "task_default_priority": 5,
    "worker_disable_rate_limits": False,

    # Мониторинг
    "worker_send_task_events": True,  # Включение событий задач для мониторинга Flower
    "task_send_sent_event": True,  # Отправка событий отправки задач

    # Обработка ошибок
    "task_autoretry_for": (Exception,),  # Автоматическая повторная попытка при исключениях
    "task_retry_kwargs": {"max_retries": 3, "countdown": 60},  # Настройки повторных попыток

    # Оптимизация производительности
    "broker_connection_retry": True,
    "broker_connection_max_retries": 10,
}


def get_celery_config() -> Dict[str, Any]:
    """
    Получить словарь конфигурации Celery.

    Эта функция возвращает конфигурацию Celery, загруженную из настроек
    приложения. Она предоставляет централизованную точку для доступа к конфигурации Celery.

    Returns:
        Словарь, содержащий настройки конфигурации Celery

    Example:
        >>> from celery_config import get_celery_config
        >>> config = get_celery_config()
        >>> print(config['broker_url'])
        'redis://localhost:6379/0'
    """
    return celery_config


def update_celery_config(**kwargs: Any) -> None:
    """
    Обновить конфигурацию Celery во время выполнения.

    Эта функция позволяет обновлять конкретные значения конфигурации Celery
    во время выполнения. Полезно для тестирования или динамических изменений конфигурации.

    Args:
        **kwargs: Configuration key-value pairs to update

    Example:
        >>> update_celery_config(task_time_limit=1800)
        >>> # Updates task_time_limit to 30 minutes
    """
    for key, value in kwargs.items():
        if key in celery_config:
            old_value = celery_config[key]
            celery_config[key] = value
            logger.info(f"Updated Celery config: {key} = {old_value} -> {value}")
        else:
            logger.warning(f"Attempted to update non-existent config key: {key}")


# Log configuration on import
logger.info(f"Celery broker URL: {settings.celery_broker_url}")
logger.info(f"Celery result backend: {settings.celery_result_backend}")
logger.info("Celery configuration loaded successfully")
