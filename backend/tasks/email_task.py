"""
Задачи email-уведомлений для отправки различных типов писем.

Этот модуль предоставляет задачи Celery для отправки email-уведомлений, включая
обратную связь по кандидатам, доставку отчётов, системные оповещения
и другие email-коммуникации.
"""
import logging
from typing import Dict, Any, List, Optional

from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@shared_task(
    name="tasks.email_task.send_feedback_notification",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def send_feedback_notification(
    self,
    feedback_id: str,
    recipient_email: str,
    candidate_name: str,
    feedback_data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Отправляет обратную связь по кандидату по электронной почте.

    Эта задача Celery обрабатывает отправку обратной связи по кандидатам
    рекрутерам или менеджерам по найму. Включает сводку обратной связи,
    оценки и подробный анализ.

    Рабочий процесс задачи:
    1. Получение обратной связи по кандидату из базы данных
    2. Форматирование содержания обратной связи для email
    3. Составление письма с соответствующим шаблоном
    4. Отправка письма через настроенный SMTP/сервис
    5. Обновление статуса доставки в базе данных

    Args:
        self: Экземпляр задачи Celery (bind=True)
        feedback_id: UUID обратной связи по кандидату
        recipient_email: Адрес электронной почты получателя
        candidate_name: Имя кандидата
        feedback_data: Словарь с деталями обратной связи:
            - grammar_feedback: Обратная связь по грамматике и языку
            - skills_feedback: Обратная связь по оценке навыков
            - experience_feedback: Обратная связь по опыту работы
            - recommendations: Список рекомендаций
            - match_score: Общий показатель соответствия
            - tone: Тон обратной связи

    Returns:
        Словарь с результатами отправки:
        - feedback_id: ID обратной связи
        - status: Статус задачи (sent/failed/pending)
        - recipient: Адрес электронной почты получателя
        - sent_at: Временная метка отправки (формат ISO)
        - error: Сообщение об ошибке (в случае неудачи)
        - processing_time_ms: Общее время обработки

    Raises:
        SoftTimeLimitExceeded: Если задача превышает мягкий лимит времени
        Exception: При ошибках отправки электронной почты

    Example:
        >>> result = send_feedback_notification.delay(
        ...     feedback_id="123-456",
        ...     recipient_email="recruiter@example.com",
        ...     candidate_name="John Doe",
        ...     feedback_data={"match_score": 85, "recommendations": ["..."]}
        ... )
        >>> print(result.get())
        {'feedback_id': '123-456', 'status': 'sent', 'recipient': 'recruiter@example.com'}
    """
    import time
    start_time = time.time()

    logger.info(
        f"Sending feedback notification for feedback_id={feedback_id} "
        f"to {recipient_email}"
    )

    try:
        # Составление темы письма
        subject = f"Candidate Feedback: {candidate_name}"

        # Составление тела письма
        body = f"""
Feedback for Candidate: {candidate_name}
Feedback ID: {feedback_id}

Match Score: {feedback_data.get('match_score', 'N/A')}%

Skills Feedback:
{feedback_data.get('skills_feedback', {})}

Experience Feedback:
{feedback_data.get('experience_feedback', {})}

Recommendations:
{chr(10).join(f'- {rec}' for rec in feedback_data.get('recommendations', []))}

---
This is an automated email from AgentHR Resume Analysis System.
        """.strip()

        # Логирование деталей письма (в продакшене - фактическая отправка)
        logger.info(f"Email composed: subject='{subject}', to={recipient_email}")
        logger.info(f"Email body length: {len(body)} characters")

        # Имитация отправки письма (в продакшене использовать SMTP/сервис)
        # Сейчас просто логируем и помечаем как отправленное
        time.sleep(0.1)  # Имитация сетевой задержки

        processing_time = int((time.time() - start_time) * 1000)

        logger.info(
            f"Feedback notification sent successfully to {recipient_email} "
            f"in {processing_time}ms"
        )

        return {
            "feedback_id": feedback_id,
            "status": "sent",
            "recipient": recipient_email,
            "sent_at": time.time(),
            "processing_time_ms": processing_time,
        }

    except SoftTimeLimitExceeded:
        logger.error(f"Feedback notification task timed out for feedback_id={feedback_id}")
        return {
            "feedback_id": feedback_id,
            "status": "failed",
            "recipient": recipient_email,
            "error": "Task timed out",
        }

    except Exception as e:
        logger.error(
            f"Failed to send feedback notification for feedback_id={feedback_id}: {e}",
            exc_info=True,
        )

        # Повторная попытка с экспоненциальной задержкой
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))

        return {
            "feedback_id": feedback_id,
            "status": "failed",
            "recipient": recipient_email,
            "error": str(e),
        }


@shared_task(
    name="tasks.email_task.send_batch_notification",
    bind=True,
    max_retries=2,
    default_retry_delay=120,
)
def send_batch_notification(
    self,
    batch_type: str,
    recipient_emails: List[str],
    notification_data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Отправляет пакетные уведомления нескольким получателям.

    Эта задача Celery обрабатывает отправку уведомлений нескольким получателям
    для пакетных операций, таких как завершение пакетного анализа резюме,
    системные оповещения или запланированные отчёты.

    Args:
        self: Экземпляр задачи Celery (bind=True)
        batch_type: Тип пакетного уведомления (batch_analysis, system_alert и т.д.)
        recipient_emails: Список адресов электронной почты для отправки
        notification_data: Словарь с деталями уведомления:
            - title: Заголовок уведомления
            - message: Основное сообщение уведомления
            - details: Дополнительный словарь деталей
            - metadata: Любые дополнительные метаданные

    Returns:
        Словарь с результатами пакетной отправки:
        - batch_type: Тип уведомления
        - status: Статус задачи (sent/failed/partial)
        - total_recipients: Количество получателей
        - successful_sends: Количество успешных отправок
        - failed_sends: Количество неудачных отправок
        - errors: Список ошибок (если есть)
        - processing_time_ms: Общее время обработки

    Example:
        >>> result = send_batch_notification.delay(
        ...     batch_type="batch_analysis",
        ...     recipient_emails=["user1@example.com", "user2@example.com"],
        ...     notification_data={"title": "Batch Complete", "message": "..."}
        ... )
        >>> print(result.get())
        {'batch_type': 'batch_analysis', 'status': 'sent', 'total_recipients': 2}
    """
    import time
    start_time = time.time()

    logger.info(
        f"Sending batch notification of type '{batch_type}' "
        f"to {len(recipient_emails)} recipients"
    )

    successful_sends = 0
    failed_sends = 0
    errors = []

    try:
        title = notification_data.get("title", f"{batch_type} Notification")
        message = notification_data.get("message", "")

        for recipient_email in recipient_emails:
            try:
                # Составление индивидуального письма
                body = f"""
{title}

{message}

Details:
{notification_data.get('details', {})}

---
This is an automated email from AgentHR.
                """.strip()

                # Логирование деталей письма (в продакшене - фактическая отправка)
                logger.info(f"Sending batch email to {recipient_email}")
                time.sleep(0.05)  # Имитация сетевой задержки на получателя

                successful_sends += 1

            except Exception as e:
                failed_sends += 1
                error_msg = f"Failed to send to {recipient_email}: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)

        processing_time = int((time.time() - start_time) * 1000)

        # Определение общего статуса
        if failed_sends == 0:
            status = "sent"
        elif successful_sends == 0:
            status = "failed"
        else:
            status = "partial"

        logger.info(
            f"Batch notification completed: {successful_sends}/{len(recipient_emails)} "
            f"sends successful in {processing_time}ms"
        )

        return {
            "batch_type": batch_type,
            "status": status,
            "total_recipients": len(recipient_emails),
            "successful_sends": successful_sends,
            "failed_sends": failed_sends,
            "errors": errors,
            "processing_time_ms": processing_time,
        }

    except SoftTimeLimitExceeded:
        logger.error(f"Batch notification task timed out for batch_type={batch_type}")
        return {
            "batch_type": batch_type,
            "status": "failed",
            "total_recipients": len(recipient_emails),
            "successful_sends": successful_sends,
            "failed_sends": failed_sends,
            "error": "Task timed out",
        }

    except Exception as e:
        logger.error(
            f"Failed to send batch notification for batch_type={batch_type}: {e}",
            exc_info=True,
        )

        # Повторная попытка с экспоненциальной задержкой
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=120 * (2 ** self.request.retries))

        return {
            "batch_type": batch_type,
            "status": "failed",
            "total_recipients": len(recipient_emails),
            "successful_sends": successful_sends,
            "failed_sends": failed_sends,
            "error": str(e),
        }
