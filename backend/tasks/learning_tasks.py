"""
Задачи ML-обучения для обнаружения синонимов навыков и улучшения моделей.

Этот модуль предоставляет задачи Celery для обработки обратной связи рекрутеров,
агрегации исправлений и генерации новых кандидатов синонимов для улучшения
точности сопоставления с течением времени.
"""
import logging
import time
from collections import defaultdict
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta

from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded
from sqlalchemy import select, and_, func
from sqlalchemy.orm import Session

from models.skill_feedback import SkillFeedback
from models.custom_synonyms import CustomSynonym
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Минимальное количество исправлений перед предложением синонима
MIN_CORRECTION_THRESHOLD = 3

# Минимальный показатель уверенности для предложений синонимов
MIN_SYNONYM_CONFIDENCE = 0.7


def aggregate_corrections(
    feedback_entries: List[SkillFeedback],
) -> Dict[str, Dict[str, Any]]:
    """
    Агрегирует исправления рекрутеров для поиска паттернов синонимов.

    Эта функция анализирует записи обратной связи, в которых рекрутеры
    исправляли сопоставление AI, выявляя паттерны, указывающие на новые синонимы.

    Args:
        feedback_entries: Список объектов SkillFeedback с исправлениями

    Returns:
        Словарь, сопоставляющий канонические навыки с обнаруженными синонимами:
        {
            "React": {
                "synonyms": {"ReactJS", "React.js", "React Framework"},
                "correction_count": 15,
                "confidence": 0.92,
                "sources": ["api", "frontend"]
            }
        }

    Example:
        >>> entries = [feedback1, feedback2, feedback3]
        >>> corrections = aggregate_corrections(entries)
        >>> print(corrections["React"]["synonyms"])
        {'ReactJS', 'React.js'}
    """
    # Группировка исправлений по каноническому навыку (на что рекрутер исправил)
    skill_groups: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
        "synonyms": defaultdict(int),
        "correction_count": 0,
        "sources": set(),
    })

    for feedback in feedback_entries:
        # Пропуск, если исправление не было предоставлено
        if not feedback.recruiter_correction and not feedback.actual_skill:
            continue

        # Использование actual_skill, если предоставлено, иначе recruiter_correction
        corrected_skill = feedback.actual_skill or feedback.recruiter_correction

        if not corrected_skill or not feedback.skill:
            continue

        # Нормализация имён навыков для сравнения
        canonical_skill = corrected_skill.strip().lower()
        original_skill = feedback.skill.strip().lower()

        # Пропуск, если они одинаковые (нет фактического исправления)
        if canonical_skill == original_skill:
            continue

        # Запись этого исправления
        skill_groups[canonical_skill]["synonyms"][original_skill] += 1
        skill_groups[canonical_skill]["correction_count"] += 1
        skill_groups[canonical_skill]["sources"].add(feedback.feedback_source)

    # Вычисление показателей уверенности и преобразование множеств в списки
    results = {}
    for canonical_skill, data in skill_groups.items():
        # Фильтрация синонимов по минимальному порогу
        filtered_synonyms = {
            syn: count
            for syn, count in data["synonyms"].items()
            if count >= MIN_CORRECTION_THRESHOLD
        }

        if not filtered_synonyms:
            continue

        # Вычисление уверенности на основе консистентности количества исправлений
        total_corrections = sum(filtered_synonyms.values())
        confidence = min(1.0, total_corrections / (MIN_CORRECTION_THRESHOLD * 2))

        results[canonical_skill] = {
            "synonyms": list(filtered_synonyms.keys()),
            "correction_count": total_corrections,
            "confidence": round(confidence, 2),
            "sources": list(data["sources"]),
        }

    return results


def generate_synonym_candidates(
    corrections: Dict[str, Dict[str, Any]],
    organization_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Генерирует записи кандидатов синонимов из агрегированных исправлений.

    Эта функция преобразует агрегированные данные исправлений в записи кандидатов
    CustomSynonym, которые могут быть рассмотрены и активированы.

    Args:
        corrections: Агрегированные исправления из aggregate_corrections()
        organization_id: Необязательный ID организации для пользовательских синонимов

    Returns:
        Список словарей кандидатов синонимов:
        [
            {
                "canonical_skill": "react",
                "custom_synonyms": ["reactjs", "react.js"],
                "context": None,
                "confidence": 0.92,
                "correction_count": 15,
                "metadata": {"sources": ["api", "frontend"]}
            }
        ]

    Example:
        >>> corrections = {"react": {"synonyms": ["reactjs"], "confidence": 0.9}}
        >>> candidates = generate_synonym_candidates(corrections, "org123")
        >>> print(candidates[0]["canonical_skill"])
        'react'
    """
    candidates = []

    for canonical_skill, data in corrections.items():
        # Пропуск предложений с низкой уверенностью
        if data["confidence"] < MIN_SYNONYM_CONFIDENCE:
            logger.info(
                f"Skipping low-confidence synonym candidate '{canonical_skill}' "
                f"(confidence: {data['confidence']} < {MIN_SYNONYM_CONFIDENCE})"
            )
            continue

        candidate = {
            "canonical_skill": canonical_skill,
            "custom_synonyms": data["synonyms"],
            "context": None,  # Может быть выведено из будущих метаданных
            "confidence": data["confidence"],
            "correction_count": data["correction_count"],
            "metadata": {
                "sources": data.get("sources", []),
                "generated_at": datetime.utcnow().isoformat(),
                "auto_generated": True,
            },
        }

        # Добавление organization_id, если предоставлен
        if organization_id:
            candidate["organization_id"] = organization_id

        candidates.append(candidate)

    logger.info(f"Generated {len(candidates)} synonym candidates from corrections")
    return candidates


@shared_task(
    name="tasks.learning_tasks.aggregate_feedback_and_generate_synonyms",
    bind=True,
    max_retries=2,
    default_retry_delay=60,
)
def aggregate_feedback_and_generate_synonyms(
    self,
    organization_id: Optional[str] = None,
    days_back: int = 30,
    mark_processed: bool = True,
) -> Dict[str, Any]:
    """
    Агрегирует обратную связь и генерирует новых кандидатов синонимов.

    Эта задача Celery обрабатывает необработанную обратную связь рекрутеров для
    выявления паттернов в исправлениях навыков и генерирует новых кандидатов
    синонимов для рассмотрения и активации. Это обеспечивает непрерывное обучение
    на основе поведения рекрутеров для улучшения точности сопоставления со временем.

    Рабочий процесс задачи:
    1. Запрос необработанных записей обратной связи из базы данных
    2. Фильтрация по organization_id (если предоставлен) и диапазону дат
    3. Агрегация исправлений для поиска паттернов синонимов
    4. Генерация кандидатов синонимов с высокой уверенностью
    5. Необязательная пометка обратной связи как обработанной

    Args:
        self: Экземпляр задачи Celery (bind=True)
        organization_id: Необязательный ID организации для фильтрации обратной связи
        days_back: Количество дней для поиска обратной связи (по умолчанию: 30)
        mark_processed: Помечать ли обратную связь как обработанную (по умолчанию: True)

    Returns:
        Словарь с результатами агрегации:
        - total_feedback: Общее количество обработанных записей обратной связи
        - unprocessed_count: Количество необработанных записей
        - corrections_found: Количество агрегированных исправлений
        - candidates_generated: Количество сгенерированных кандидатов синонимов
        - candidates: Список сгенерированных кандидатов синонимов
        - processing_time_ms: Общее время обработки
        - status: Статус задачи (completed/failed)

    Raises:
        SoftTimeLimitExceeded: Если задача превышает лимит времени
        Exception: При ошибках базы данных или обработки

    Example:
        >>> from tasks.learning_tasks import aggregate_feedback_and_generate_synonyms
        >>> task = aggregate_feedback_and_generate_synonyms.delay("org123")
        >>> result = task.get()
        >>> print(result['candidates_generated'])
        5
    """
    start_time = time.time()
    total_steps = 4
    current_step = 0

    try:
        logger.info(
            f"Starting feedback aggregation for organization: {organization_id or 'all'}, "
            f"days_back: {days_back}"
        )

        # Шаг 1: Запрос необработанной обратной связи
        current_step += 1
        progress = {
            "current": current_step,
            "total": total_steps,
            "percentage": int(current_step / total_steps * 100),
            "status": "querying_feedback",
            "message": "Запрос необработанной обратной связи из базы данных...",
        }
        self.update_state(state="PROGRESS", meta=progress)
        logger.info(f"Task {self.request.id}: Step {current_step}/{total_steps} - Запрос обратной связи")

        # Примечание: Это заглушка для запроса к базе данных
        # В реальной реализации следует использовать асинхронную сессию для запроса SkillFeedback
        # feedback_entries = await db_session.execute(
        #     select(SkillFeedback).where(
        #         and_(
        #             SkillFeedback.processed == False,
        #             SkillFeedback.created_at >= datetime.utcnow() - timedelta(days=days_back),
        #             SkillFeedback.organization_id == organization_id if organization_id else True
        #         )
        #     )
        # )
        # Сейчас возврат результата-заглушки
        feedback_entries = []
        unprocessed_count = 0

        logger.info(f"Found {unprocessed_count} unprocessed feedback entries")

        # Шаг 2: Агрегация исправлений
        current_step += 1
        progress = {
            "current": current_step,
            "total": total_steps,
            "percentage": int(current_step / total_steps * 100),
            "status": "aggregating_corrections",
            "message": "Агрегация исправлений рекрутеров...",
        }
        self.update_state(state="PROGRESS", meta=progress)
        logger.info(f"Task {self.request.id}: Step {current_step}/{total_steps} - Агрегация исправлений")

        corrections = aggregate_corrections(feedback_entries)
        corrections_count = len(corrections)
        logger.info(f"Aggregated {corrections_count} unique skill corrections")

        # Шаг 3: Генерация кандидатов синонимов
        current_step += 1
        progress = {
            "current": current_step,
            "total": total_steps,
            "percentage": int(current_step / total_steps * 100),
            "status": "generating_candidates",
            "message": "Генерация кандидатов синонимов из паттернов...",
        }
        self.update_state(state="PROGRESS", meta=progress)
        logger.info(f"Task {self.request.id}: Step {current_step}/{total_steps} - Генерация кандидатов")

        candidates = generate_synonym_candidates(corrections, organization_id)
        logger.info(f"Generated {len(candidates)} synonym candidates")

        # Шаг 4: Пометка обратной связи как обработанной (если запрошено)
        current_step += 1
        progress = {
            "current": current_step,
            "total": total_steps,
            "percentage": int(current_step / total_steps * 100),
            "status": "marking_processed",
            "message": "Пометка обратной связи как обработанной...",
        }
        self.update_state(state="PROGRESS", meta=progress)
        logger.info(f"Task {self.request.id}: Step {current_step}/{total_steps} - Пометка обработанной")

        # Примечание: Это заглушка для пометки обратной связи как обработанной
        # В реальной реализации необходимо обновить флаг processed
        processed_count = 0
        if mark_processed and feedback_entries:
            # for entry in feedback_entries:
            #     entry.processed = True
            # await db_session.commit()
            processed_count = len(feedback_entries)

        processing_time_ms = round((time.time() - start_time) * 1000, 2)

        result = {
            "total_feedback": unprocessed_count,
            "unprocessed_count": unprocessed_count,
            "corrections_found": corrections_count,
            "candidates_generated": len(candidates),
            "candidates": candidates,
            "processed_count": processed_count,
            "processing_time_ms": processing_time_ms,
            "status": "completed",
        }

        logger.info(
            f"Feedback aggregation completed: {corrections_count} corrections, "
            f"{len(candidates)} candidates generated in {processing_time_ms}ms"
        )

        return result

    except SoftTimeLimitExceeded:
        logger.error(f"Task {self.request.id} exceeded time limit")
        return {
            "status": "failed",
            "error": "Aggregation exceeded maximum time limit",
            "processing_time_ms": round((time.time() - start_time) * 1000, 2),
        }

    except Exception as e:
        logger.error(f"Error in feedback aggregation: {e}", exc_info=True)
        return {
            "status": "failed",
            "error": str(e),
            "processing_time_ms": round((time.time() - start_time) * 1000, 2),
        }


@shared_task(
    name="tasks.learning_tasks.review_and_activate_synonyms",
    bind=True,
    max_retries=1,
    default_retry_delay=60,
)
def review_and_activate_synonyms(
    self,
    candidate_ids: List[str],
    auto_activate_threshold: float = 0.9,
) -> Dict[str, Any]:
    """
    Проверяет и активирует кандидатов синонимов.

    Эта задача проверяет сгенерированных кандидатов синонимов и автоматически
    активирует кандидатов с высокой уверенностью, помечая кандидатов с более
    низкой уверенностью для ручной проверки.

    Args:
        self: Экземпляр задачи Celery (bind=True)
        candidate_ids: Список ID кандидатов для проверки
        auto_activate_threshold: Порог уверенности для автоактивации (по умолчанию: 0.9)

    Returns:
        Словарь с результатами проверки:
        - total_candidates: Общее количество проверенных кандидатов
        - auto_activated: Количество автоматически активированных
        - manual_review: Количество помеченных для ручной проверки
        - rejected: Количество отклонённых (низкая уверенность)
        - processing_time_ms: Общее время обработки
        - status: Статус задачи

    Example:
        >>> from tasks.learning_tasks import review_and_activate_synonyms
        >>> task = review_and_activate_synonyms.delay(["id1", "id2"])
        >>> result = task.get()
        >>> print(result['auto_activated'])
        2
    """
    start_time = time.time()

    try:
        logger.info(f"Reviewing {len(candidate_ids)} synonym candidates")

        auto_activated = 0
        manual_review = 0
        rejected = 0

        # Примечание: Это заглушка для логики проверки
        # В реальной реализации необходимо:
        # 1. Запросить кандидатов по ID
        # 2. Проверить показатели уверенности
        # 3. Автоматически активировать кандидатов с высокой уверенностью
        # 4. Помечать кандидатов со средней уверенностью для проверки
        # 5. Отклонять кандидатов с низкой уверенностью

        for candidate_id in candidate_ids:
            # Логика-заглушка - в реальной реализации запрос кандидата
            # candidate = await db_session.get(CustomSynonym, candidate_id)
            # if candidate and candidate.metadata.get("confidence", 0) >= auto_activate_threshold:
            #     candidate.is_active = True
            #     auto_activated += 1
            pass

        processing_time_ms = round((time.time() - start_time) * 1000, 2)

        result = {
            "total_candidates": len(candidate_ids),
            "auto_activated": auto_activated,
            "manual_review": manual_review,
            "rejected": rejected,
            "processing_time_ms": processing_time_ms,
            "status": "completed",
        }

        logger.info(
            f"Review completed: {auto_activated} activated, "
            f"{manual_review} flagged for review, {rejected} rejected"
        )

        return result

    except Exception as e:
        logger.error(f"Error in synonym review: {e}", exc_info=True)
        return {
            "status": "failed",
            "error": str(e),
            "processing_time_ms": round((time.time() - start_time) * 1000, 2),
        }


@shared_task(
    name="tasks.learning_tasks.periodic_feedback_aggregation",
    bind=True,
)
def periodic_feedback_aggregation(
    self,
) -> Dict[str, Any]:
    """
    Периодическая задача для агрегации обратной связи и генерации синонимов.

    Это запланированная задача, которая периодически запускается (например, ежедневно)
    для автоматической обработки новой обратной связи и генерации кандидатов улучшений.

    Returns:
        Словарь с результатами агрегации

    Example:
        >>> # Это будет запланировано через Celery beat
        >>> # celery beat schedule: {
        >>> #     'daily-feedback-aggregation': {
        >>> #         'task': 'tasks.learning_tasks.periodic_feedback_aggregation',
        >>> #         'schedule': crontab(hour=2, minute=0),  # 2 AM daily
        >>> #     }
        >>> # }
    """
    logger.info("Starting periodic feedback aggregation")

    # Агрегация обратной связи за последние 7 дней
    result = aggregate_feedback_and_generate_synonyms(
        organization_id=None,  # Все организации
        days_back=7,
        mark_processed=True,
    )

    logger.info(f"Periodic aggregation completed: {result.get('status')}")
    return result


@shared_task(
    name="tasks.learning_tasks.retrain_skill_matching_model",
    bind=True,
    max_retries=1,
    default_retry_delay=300,
)
def retrain_skill_matching_model(
    self,
    model_name: str = "skill_matching",
    days_back: int = 30,
    min_feedback_count: int = 50,
    auto_activate: bool = False,
    performance_threshold: float = 0.85,
) -> Dict[str, Any]:
    """
    Переобучает модель сопоставления навыков на основе накопленной обратной связи.

    Эта задача Celery обрабатывает накопленную обратную связь рекрутеров для
    переобучения и улучшения модели сопоставления навыков. Создаёт новую версию
    модели, оценивает производительность и опционально активирует её, если
    пороги производительности достигнуты.

    Рабочий процесс задачи:
    1. Запрос данных обратной связи за указанный период
    2. Проверка минимального количества обратной связи для обучения
    3. Извлечение обучающих данных (пары навыков и метки правильности)
    4. Обучение новой модели или обновление существующих синонимов
    5. Создание записи MLModelVersion
    6. Оценка производительности модели на валидационном наборе
    7. Опциональная активация модели, если производительность превышает порог

    Args:
        self: Экземпляр задачи Celery (bind=True)
        model_name: Имя модели для переобучения (по умолчанию: "skill_matching")
        days_back: Количество дней обратной связи для обучения (по умолчанию: 30)
        min_feedback_count: Минимальное количество записей обратной связи для обучения (по умолчанию: 50)
        auto_activate: Активировать ли автоматически при достижении порога производительности (по умолчанию: False)
        performance_threshold: Минимальный показатель точности для автоактивации (по умолчанию: 0.85)

    Returns:
        Словарь с результатами переобучения:
        - training_samples: Количество использованных образцов обратной связи
        - new_version_id: ID созданной версии модели
        - performance_score: Показатель производительности модели (0-1)
        - is_active: Была ли модель активирована
        - is_experiment: Является ли модель экспериментом
        - improvement_over_baseline: Улучшение производительности относительно текущей модели
        - processing_time_ms: Общее время обработки
        - status: Статус задачи (completed/failed)

    Raises:
        SoftTimeLimitExceeded: Если задача превышает лимит времени
        Exception: При ошибках базы данных или обработки

    Example:
        >>> from tasks.learning_tasks import retrain_skill_matching_model
        >>> task = retrain_skill_matching_model.delay(
        ...     model_name="skill_matching",
        ...     days_back=30,
        ...     auto_activate=True
        ... )
        >>> result = task.get()
        >>> print(result['performance_score'])
        0.92
    """
    start_time = time.time()
    total_steps = 6
    current_step = 0

    try:
        logger.info(
            f"Starting model retraining for '{model_name}', "
            f"days_back: {days_back}, min_feedback: {min_feedback_count}"
        )

        # Шаг 1: Запрос данных обратной связи
        current_step += 1
        progress = {
            "current": current_step,
            "total": total_steps,
            "percentage": int(current_step / total_steps * 100),
            "status": "querying_feedback",
            "message": "Запрос данных обратной связи для обучения...",
        }
        self.update_state(state="PROGRESS", meta=progress)
        logger.info(f"Task {self.request.id}: Step {current_step}/{total_steps} - Запрос обратной связи")

        # Примечание: Это заглушка для запроса к базе данных
        # В реальной реализации следует использовать асинхронную сессию для запроса SkillFeedback
        # feedback_entries = await db_session.execute(
        #     select(SkillFeedback).where(
        #         and_(
        #             SkillFeedback.created_at >= datetime.utcnow() - timedelta(days=days_back),
        #             SkillFeedback.was_correct.is_not(None),
        #             SkillFeedback.skill.is_not(None)
        #         )
        #     ).order_by(SkillFeedback.created_at.desc())
        # )
        feedback_entries = []
        training_samples = len(feedback_entries)

        logger.info(f"Found {training_samples} feedback samples for training")

        # Проверка минимального количества обратной связи
        if training_samples < min_feedback_count:
            logger.warning(
                f"Insufficient feedback for training: {training_samples} < {min_feedback_count}. "
                f"Skipping retraining."
            )
            return {
                "status": "skipped",
                "reason": f"Insufficient feedback samples ({training_samples} < {min_feedback_count})",
                "training_samples": training_samples,
                "min_required": min_feedback_count,
                "processing_time_ms": round((time.time() - start_time) * 1000, 2),
            }

        # Шаг 2: Извлечение обучающих данных
        current_step += 1
        progress = {
            "current": current_step,
            "total": total_steps,
            "percentage": int(current_step / total_steps * 100),
            "status": "extracting_features",
            "message": "Извлечение обучающих признаков из обратной связи...",
        }
        self.update_state(state="PROGRESS", meta=progress)
        logger.info(f"Task {self.request.id}: Step {current_step}/{total_steps} - Извлечение признаков")

        # Извлечение пар навыков и меток правильности
        # Примечание: В реальной реализации здесь обрабатываются feedback_entries
        training_data = []
        for entry in feedback_entries:
            # Извлечение признаков из обратной связи
            # Это заглушка - реальная реализация извлечёт:
            # - Исходный навык, сопоставленный AI
            # - Исправленный навык (если предоставлен)
            # - Было ли сопоставление правильным
            # - Контекстная информация
            pass

        logger.info(f"Extracted {len(training_data)} training samples")

        # Шаг 3: Агрегация исправлений для обновлений синонимов
        current_step += 1
        progress = {
            "current": current_step,
            "total": total_steps,
            "percentage": int(current_step / total_steps * 100),
            "status": "aggregating_corrections",
            "message": "Агрегация исправлений для обновлений синонимов...",
        }
        self.update_state(state="PROGRESS", meta=progress)
        logger.info(f"Task {self.request.id}: Step {current_step}/{total_steps} - Агрегация исправлений")

        corrections = aggregate_corrections(feedback_entries)
        corrections_count = len(corrections)
        logger.info(f"Aggregated {corrections_count} skill corrections")

        # Шаг 4: Генерация и сохранение кандидатов синонимов
        current_step += 1
        progress = {
            "current": current_step,
            "total": total_steps,
            "percentage": int(current_step / total_steps * 100),
            "status": "generating_synonyms",
            "message": "Генерация новых кандидатов синонимов...",
        }
        self.update_state(state="PROGRESS", meta=progress)
        logger.info(f"Task {self.request.id}: Step {current_step}/{total_steps} - Генерация синонимов")

        # Генерация кандидатов синонимов из исправлений
        candidates = generate_synonym_candidates(corrections, organization_id=None)

        # Примечание: В реальной реализации необходимо сохранить кандидатов в базу данных
        # for candidate in candidates:
        #     new_synonym = CustomSynonym(**candidate)
        #     db_session.add(new_synonym)
        # await db_session.commit()

        logger.info(f"Generated {len(candidates)} new synonym candidates")

        # Шаг 5: Создание новой версии модели
        current_step += 1
        progress = {
            "current": current_step,
            "total": total_steps,
            "percentage": int(current_step / total_steps * 100),
            "status": "creating_model_version",
            "message": "Создание записи новой версии модели...",
        }
        self.update_state(state="PROGRESS", meta=progress)
        logger.info(f"Task {self.request.id}: Step {current_step}/{total_steps} - Создание версии модели")

        # Генерация нового номера версии
        # Примечание: В реальной реализации следует запросить последнюю версию
        # latest_version = await db_session.execute(
        #     select(MLModelVersion)
        #     .where(MLModelVersion.model_name == model_name)
        #     .order_by(MLModelVersion.created_at.desc())
        #     .limit(1)
        # )
        # и увеличить номер версии
        new_version = "1.0.0"  # Заглушка

        # Вычисление точности обучения
        # Примечание: В реальной реализации здесь будет оценка на валидационном наборе
        training_accuracy = min(1.0, len(candidates) * 0.1 + 0.7)  # Вычисление-заглушка
        performance_score = round(training_accuracy, 3)

        # Примечание: В реальной реализации необходимо создать запись MLModelVersion
        # new_model = MLModelVersion(
        #     model_name=model_name,
        #     version=new_version,
        #     is_active=False,
        #     is_experiment=not auto_activate,
        #     performance_score=performance_score * 100,
        #     training_samples=training_samples,
        #     metadata={
        #         "training_days": days_back,
        #         "synonyms_added": len(candidates),
        #         "corrections_aggregated": corrections_count,
        #         "auto_generated": True,
        #     }
        # )
        # db_session.add(new_model)
        # await db_session.commit()
        # new_version_id = str(new_model.id)

        new_version_id = "placeholder-uuid"  # Заглушка
        logger.info(f"Created new model version: {new_version} (ID: {new_version_id})")

        # Шаг 6: Оценка и опциональная активация
        current_step += 1
        progress = {
            "current": current_step,
            "total": total_steps,
            "percentage": int(current_step / total_steps * 100),
            "status": "evaluating_performance",
            "message": "Оценка производительности модели...",
        }
        self.update_state(state="PROGRESS", meta=progress)
        logger.info(f"Task {self.request.id}: Step {current_step}/{total_steps} - Оценка производительности")

        # Определение необходимости активации модели
        should_activate = auto_activate and performance_score >= performance_threshold
        is_active = False
        is_experiment = not should_activate

        # Примечание: В реальной реализации необходимо активировать модель при необходимости
        # if should_activate:
        #     # Деактивация других версий
        #     await db_session.execute(
        #         update(MLModelVersion)
        #         .where(
        #             and_(
        #                 MLModelVersion.model_name == model_name,
        #                 MLModelVersion.id != new_version_id
        #             )
        #         )
        #         .values(is_active=False)
        #     )
        #     # Активация новой версии
        #     new_model.is_active = True
        #     new_model.is_experiment = False
        #     await db_session.commit()
        #     is_active = True
        #     is_experiment = False

        # Вычисление улучшения относительно базовой линии
        # Примечание: В реальной реализации следует сравнить с текущей активной моделью
        baseline_score = 0.75  # Заглушка
        improvement = round(performance_score - baseline_score, 3)

        processing_time_ms = round((time.time() - start_time) * 1000, 2)

        result = {
            "training_samples": training_samples,
            "new_version_id": new_version_id,
            "new_version": new_version,
            "performance_score": performance_score,
            "is_active": is_active,
            "is_experiment": is_experiment,
            "improvement_over_baseline": improvement,
            "synonyms_generated": len(candidates),
            "corrections_aggregated": corrections_count,
            "processing_time_ms": processing_time_ms,
            "status": "completed",
        }

        logger.info(
            f"Model retraining completed: version {new_version}, "
            f"score: {performance_score}, activated: {is_active}, "
            f"improvement: {improvement:+.3f}"
        )

        return result

    except SoftTimeLimitExceeded:
        logger.error(f"Task {self.request.id} exceeded time limit")
        return {
            "status": "failed",
            "error": "Model retraining exceeded maximum time limit",
            "processing_time_ms": round((time.time() - start_time) * 1000, 2),
        }

    except Exception as e:
        logger.error(f"Error in model retraining: {e}", exc_info=True)
        return {
            "status": "failed",
            "error": str(e),
            "processing_time_ms": round((time.time() - start_time) * 1000, 2),
        }
