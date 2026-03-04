"""
Приложение Celery для асинхронной обработки задач.

Этот модуль инициализирует приложение Celery с брокером Redis и предоставляет
определения задач для длительных операций, таких как анализ резюме.
"""
import logging
from typing import Dict, Any, Optional

from celery import Celery, shared_task
from celery.result import AsyncResult

from celery_config import get_celery_config
from config import get_settings
from tasks import (
    analyze_resume_async,
    batch_analyze_resumes,
    generate_scheduled_reports,
    process_all_pending_reports,
)

logger = logging.getLogger(__name__)
settings = get_settings()

# Создание экземпляра приложения Celery
# Используем 'backend.tasks' как имя основного модуля
celery_app = Celery(
    "backend.tasks",
    config_source=get_celery_config(),
)

# Опционально: явная установка конфигурации из словаря
celery_app.conf.update(get_celery_config())

# Логирование информации о запуске
logger.info("Приложение Celery инициализировано")
logger.info(f"URL брокера: {settings.celery_broker_url}")
logger.info(f"Бэкенд результатов: {settings.celery_result_backend}")


@shared_task(
    name="tasks.health_check",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def health_check_task(self) -> Dict[str, Any]:
    """
    Простая задача проверки работоспособности для проверки функционирования worker Celery.

    Эта задача выполняет базовые проверки и возвращает информацию о статусе.
    Полезна для мониторинга работоспособности и подключения worker Celery.

    Args:
        self: Экземпляр задачи Celery (bind=True)

    Returns:
        Словарь с информацией о состоянии работоспособности

    Example:
        >>> from tasks import health_check_task
        >>> result = health_check_task.delay()
        >>> print(result.get())
        {'status': 'healthy', 'worker': 'celery@hostname'}
    """
    logger.info("Задача проверки работоспособности выполнена")
    return {
        "status": "healthy",
        "worker": self.request.hostname,
        "task_id": self.request.id,
        "message": "Worker Celery работает",
    }


@shared_task(
    name="tasks.add_numbers",
    bind=True,
    max_retries=3,
)
def add_numbers_task(self, x: int, y: int) -> int:
    """
    Простая задача сложения для тестирования функциональности Celery.

    Это базовая задача, которая складывает два числа. Полезна для
    тестирования настройки Celery, выполнения задач и получения результатов.

    Args:
        self: Экземпляр задачи Celery (bind=True)
        x: Первое число для сложения
        y: Второе число для сложения

    Returns:
        Сумма x и y

    Raises:
        ValueError: Если входные данные не являются целыми числами

    Example:
        >>> from tasks import add_numbers_task
        >>> result = add_numbers_task.delay(5, 3)
        >>> print(result.get())
        8
    """
    if not isinstance(x, int) or not isinstance(y, int):
        error_msg = f"Оба входных значения должны быть целыми числами, получено {type(x)} и {type(y)}"
        logger.error(error_msg)
        raise ValueError(error_msg)

    result = x + y
    logger.info(f"Задача {self.request.id}: {x} + {y} = {result}")
    return result


@shared_task(
    name="tasks.long_running_task",
    bind=True,
    max_retries=2,
)
def long_running_task(
    self,
    duration_seconds: int = 10,
    progress_updates: bool = True,
) -> Dict[str, Any]:
    """
    Имитация длительной задачи для тестирования асинхронной обработки.

    Эта задача имитирует длительную операцию с опциональными обновлениями
    прогресса. Полезна для тестирования выполнения фоновых задач, мониторинга
    и отслеживания прогресса.

    Args:
        self: Экземпляр задачи Celery (bind=True)
        duration_seconds: Как долго задача должна выполняться (по умолчанию: 10 секунд)
        progress_updates: Отправлять ли обновления прогресса (по умолчанию: True)

    Returns:
        Словарь, содержащий статус завершения задачи и информацию о времени

    Example:
        >>> from tasks import long_running_task
        >>> result = long_running_task.delay(duration_seconds=5)
        >>> # Можно проверить result.status для обновлений 'PROGRESS'
        >>> print(result.get())
        {'status': 'completed', 'duration': 5, 'steps': 5}
    """
    import time

    logger.info(
        f"Длительная задача {self.request.id} запущена (длительность: {duration_seconds}с)"
    )

    steps = 5
    step_duration = duration_seconds / steps

    for i in range(steps):
        # Имитация работы
        time.sleep(step_duration)

        # Обновление прогресса, если включено
        if progress_updates:
            progress = {
                "current": i + 1,
                "total": steps,
                "percentage": int((i + 1) / steps * 100),
                "status": "in_progress",
            }
            self.update_state(state="PROGRESS", meta=progress)
            logger.info(f"Задача {self.request.id} прогресс: {progress['percentage']}%")

    logger.info(f"Длительная задача {self.request.id} завершена")

    return {
        "status": "completed",
        "task_id": self.request.id,
        "duration_seconds": duration_seconds,
        "steps_completed": steps,
        "message": "Длительная задача успешно завершена",
    }


def get_task_status(task_id: str) -> Dict[str, Any]:
    """
    Получить статус задачи Celery по её ID.

    Эта функция извлекает текущий статус, результат и метаданные
    для указанного ID задачи. Полезна для проверки прогресса и результатов задач.

    Args:
        task_id: ID задачи Celery для проверки

    Returns:
        Словарь, содержащий информацию о статусе задачи:
        - task_id: ID задачи
        - state: Текущее состояние задачи (PENDING, STARTED, SUCCESS, FAILURE и т.д.)
        - result: Результат задачи (если успешно)
        - error: Сообщение об ошибке (если не удалось)
        - info: Дополнительные метаданные задачи (для состояния PROGRESS)

    Example:
        >>> from tasks import get_task_status
        >>> status = get_task_status('abc-123-def')
        >>> print(status['state'])
        'SUCCESS'
    """
    result = AsyncResult(task_id, app=celery_app)

    status_info = {
        "task_id": task_id,
        "state": result.state,
    }

    if result.state == "PENDING":
        status_info["status"] = "Задача ожидает выполнения"
        status_info["result"] = None

    elif result.state == "STARTED":
        status_info["status"] = "Задача запущена"
        status_info["result"] = None

    elif result.state == "SUCCESS":
        status_info["status"] = "Задача успешно завершена"
        status_info["result"] = result.result

    elif result.state == "FAILURE":
        status_info["status"] = "Задача не удалась"
        status_info["error"] = str(result.info)
        status_info["result"] = None

    elif result.state == "PROGRESS":
        status_info["status"] = "Задача в процессе выполнения"
        status_info["result"] = None
        if isinstance(result.info, dict):
            status_info["progress"] = result.info

    else:
        status_info["status"] = f"Неизвестное состояние: {result.state}"
        status_info["result"] = result.result if result.result else None

    return status_info


def revoke_task(task_id: str, terminate: bool = False) -> Dict[str, Any]:
    """
    Отменить или завершить выполняющуюся задачу Celery.

    Эта функция пытается отменить или завершить задачу по её ID.
    Terminate принудительно убьёт задачу, а cancel попытается
    остановить её корректно.

    Args:
        task_id: ID задачи Celery для отмены
        terminate: Принудительно завершить задачу (по умолчанию: False)

    Returns:
        Словарь, содержащий статус отмены

    Example:
        >>> from tasks import revoke_task
        >>> result = revoke_task('abc-123-def', terminate=True)
        >>> print(result['status'])
        'cancelled'
    """
    celery_app.control.revoke(task_id, terminate=terminate)

    logger.info(f"Задача {task_id} отменена (terminate={terminate})")

    return {
        "task_id": task_id,
        "status": "cancelled" if terminate else "revoked",
        "terminated": terminate,
    }


# Экспорт приложения Celery для использования workers
__all__ = [
    "celery_app",
    "health_check_task",
    "add_numbers_task",
    "long_running_task",
    "analyze_resume_async",
    "batch_analyze_resumes",
    "generate_scheduled_reports",
    "process_all_pending_reports",
    "get_task_status",
    "revoke_task",
]
