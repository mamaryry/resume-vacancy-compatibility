"""
Эндпоинты подбора вакансий с обработкой синонимов навыков и визуальным выделением.

Этот модуль предоставляет эндпоинты для сравнения резюме с вакансиями,
расчёта процента совпадения и визуального выделения совпавших (зелёным)
и отсутствующих (красным) навыков.
"""
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Добавляем родительскую директорию в path для импорта из сервиса data_extractor
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "services" / "data_extractor"))

from database import get_db
from models.match_result import MatchResult

from analyzers import (
    extract_resume_keywords_hf as extract_resume_keywords,
    extract_resume_entities,
    calculate_skill_experience,
    format_experience_summary,
    EnhancedSkillMatcher,
    UnifiedSkillMatcher,
    get_unified_matcher,
)
from i18n.backend_translations import get_error_message, get_success_message

logger = logging.getLogger(__name__)

router = APIRouter()

# Директория, где хранятся загруженные резюме
UPLOAD_DIR = Path("data/uploads")

# Путь к файлу синонимов навыков
SYNONYMS_FILE = Path(__file__).parent.parent / "models" / "skill_synonyms.json"

# Кэш синонимов навыков
_skill_synonyms_cache: Optional[Dict[str, List[str]]] = None


def _extract_locale(request: Optional[Request]) -> str:
    """
    Извлечь заголовок Accept-Language из запроса.

    Args:
        request: Входящий запрос FastAPI (опционально)

    Returns:
        Код языка (например, 'en', 'ru')
    """
    if request is None:
        return "en"
    accept_language = request.headers.get("Accept-Language", "en")
    lang_code = accept_language.split("-")[0].split(",")[0].strip().lower()
    return lang_code


def load_skill_synonyms() -> Dict[str, List[str]]:
    """
    Загрузить синонимы навыков из JSON-файла.

    Возвращает словарь, сопоставляющий канонические имена навыков со списками синонимов.

    Структура файла синонимов организует навыки по категориям (базы данных,
    языки программирования, веб-фреймворки и т.д.), где каждый навык имеет
    каноническое имя и список эквивалентных терминов.

    Returns:
        Словарь, сопоставляющий имена навыков их синонимам

    Example:
        >>> synonyms = load_skill_synonyms()
        >>> synonyms["PostgreSQL"]
        ["PostgreSQL", "Postgres", "Postgres SQL"]
    """
    global _skill_synonyms_cache

    if _skill_synonyms_cache is not None:
        return _skill_synonyms_cache

    try:
        with open(SYNONYMS_FILE, "r", encoding="utf-8") as f:
            synonyms_data = json.load(f)

        # Выравниваем структуру категорий в один словарь
        # Вход: {"databases": {"SQL": ["SQL", "PostgreSQL", ...]}}
        # Выход: {"SQL": ["SQL", "PostgreSQL", ...]}
        flat_synonyms: Dict[str, List[str]] = {}

        for category in synonyms_data.values():
            if isinstance(category, dict):
                for canonical_name, synonyms_list in category.items():
                    if isinstance(synonyms_list, list):
                        # Убеждаемся, что каноническое имя тоже в списке
                        all_synonyms = set(synonyms_list + [canonical_name])
                        flat_synonyms[canonical_name] = list(all_synonyms)

        _skill_synonyms_cache = flat_synonyms
        logger.info(f"Загружено {len(flat_synonyms)} отображений синонимов навыков")
        return flat_synonyms

    except FileNotFoundError:
        logger.warning(f"Файл синонимов навыков не найден: {SYNONYMS_FILE}")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"Ошибка парсинга JSON синонимов навыков: {e}")
        return {}
    except Exception as e:
        logger.error(f"Ошибка загрузки синонимов навыков: {e}", exc_info=True)
        return {}


def normalize_skill_name(skill: str) -> str:
    """
    Нормализовать имя навыка для корректного сравнения.

    Удаляет лишние пробелы, преобразует в нижний регистр и обрабатывает
    распространённые вариации капитализации и интервалов.

    Args:
        skill: Имя навыка для нормализации

    Returns:
        Нормализованное имя навыка

    Example:
        >>> normalize_skill_name("  React JS  ")
        "react js"
    """
    return " ".join(skill.strip().lower().split())


def check_skill_match(
    resume_skills: List[str], required_skill: str, synonyms_map: Dict[str, List[str]]
) -> bool:
    """
    Проверить, соответствует ли требуемый навык какому-либо навыку в резюме.

    Выполняет сравнение без учёта регистра и проверяет синонимы навыков.
    Например, если вакансия требует "SQL", а в резюме есть "PostgreSQL",
    будет совпадение, если "PostgreSQL" есть в списке синонимов для "SQL".

    Args:
        resume_skills: Список навыков, извлечённых из резюме
        required_skill: Навык, требуемый вакансией
        synonyms_map: Словарь синонимов навыков

    Returns:
        True, если навык найден в навыках резюме (прямое совпадение или синоним)

    Example:
        >>> synonyms = {"SQL": ["SQL", "PostgreSQL", "MySQL"]}
        >>> check_skill_match(["Java", "PostgreSQL"], "SQL", synonyms)
        True
    """
    normalized_required = normalize_skill_name(required_skill)

    # Сначала проверяем прямое совпадение
    for resume_skill in resume_skills:
        if normalize_skill_name(resume_skill) == normalized_required:
            return True

    # Затем проверяем совпадения по синонимам
    # Получаем все синонимы для требуемого навыка
    all_required_variants = [normalized_required]

    for canonical_name, synonym_list in synonyms_map.items():
        normalized_canonical = normalize_skill_name(canonical_name)
        # Если это каноническое имя соответствует требуемому навыку
        if normalized_canonical == normalized_required:
            # Добавляем все его синонимы
            all_required_variants.extend(
                [normalize_skill_name(s) for s in synonym_list]
            )
        # Также проверяем, соответствует ли какой-либо синоним
        for synonym in synonym_list:
            if normalize_skill_name(synonym) == normalized_required:
                all_required_variants.extend(
                    [normalize_skill_name(canonical_name)] +
                    [normalize_skill_name(s) for s in synonym_list]
                )
                break

    # Проверяем, соответствует ли какой-либо навык резюме какому-либо варианту
    unique_variants = set(all_required_variants)
    for resume_skill in resume_skills:
        if normalize_skill_name(resume_skill) in unique_variants:
            return True

    return False


def find_matching_synonym(
    resume_skills: List[str], required_skill: str, synonyms_map: Dict[str, List[str]]
) -> Optional[str]:
    """
    Найти соответствующий навык резюме для требуемого навыка.

    Возвращает фактическое имя навыка из резюме, которое соответствует требуемому,
    либо напрямую, либо через синонимы. Полезно для отображения пользователю,
    какая конкретная вариация была найдена.

    Args:
        resume_skills: Список навыков, извлечённых из резюме
        required_skill: Навык, требуемый вакансией
        synonyms_map: Словарь синонимов навыков

    Returns:
        Имя соответствующего навыка резюме или None, если совпадение не найдено

    Example:
        >>> synonyms = {"SQL": ["SQL", "PostgreSQL"]}
        >>> find_matching_synonym(["Java", "PostgreSQL"], "SQL", synonyms)
        "PostgreSQL"
    """
    normalized_required = normalize_skill_name(required_skill)

    # Формируем множество всех вариантов для требуемого навыка
    all_variants = {normalized_required}

    for canonical_name, synonym_list in synonyms_map.items():
        normalized_canonical = normalize_skill_name(canonical_name)
        if normalized_canonical == normalized_required:
            all_variants.update([normalize_skill_name(s) for s in synonym_list])
        else:
            for synonym in synonym_list:
                if normalize_skill_name(synonym) == normalized_required:
                    all_variants.add(normalized_canonical)
                    all_variants.update([normalize_skill_name(s) for s in synonym_list])
                    break

    # Находим соответствующий навык резюме
    for resume_skill in resume_skills:
        if normalize_skill_name(resume_skill) in all_variants:
            return resume_skill

    return None


class MatchRequest(BaseModel):
    """Модель запроса для эндпоинта подбора вакансии."""

    resume_id: str = Field(..., description="Уникальный идентификатор резюме для сопоставления")
    vacancy_data: Dict[str, Any] = Field(
        ..., description="Данные вакансии с требуемыми навыками и опытом"
    )


class SkillMatch(BaseModel):
    """Результат сопоставления отдельного навыка с оценкой уверенности."""

    skill: str = Field(..., description="Имя навыка из вакансии")
    status: str = Field(..., description="Статус сопоставления: 'matched' или 'missing'")
    matched_as: Optional[str] = Field(
        None, description="Фактическое имя навыка, найденное в резюме (если совпало)"
    )
    highlight: str = Field(..., description="Цвет выделения: 'green' или 'red'")
    confidence: float = Field(
        0.0, description="Оценка уверенности от 0.0 до 1.0 (от 0% до 100%)"
    )
    match_type: str = Field(
        "none", description="Тип совпадения: 'direct', 'context', 'synonym', 'fuzzy' или 'none'"
    )


class ExperienceVerification(BaseModel):
    """Результаты проверки опыта работы."""

    required_months: int = Field(..., description="Требуемый опыт в месяцах")
    actual_months: int = Field(..., description="Фактический опыт в месяцах")
    meets_requirement: bool = Field(..., description="Удовлетворяет ли опыт требованию")
    summary: str = Field(..., description="Человекочитаемая сводка опыта")


class MatchResponse(BaseModel):
    """Полный ответ подбора вакансии."""

    resume_id: str = Field(..., description="Идентификатор резюме")
    vacancy_title: str = Field(..., description="Название вакансии")
    match_percentage: float = Field(..., description="Общий процент совпадения навыков (0-100)")
    required_skills_match: List[SkillMatch] = Field(
        ..., description="Результаты сопоставления обязательных навыков"
    )
    additional_skills_match: List[SkillMatch] = Field(
        ..., description="Результаты сопоставления дополнительных/желательных навыков"
    )
    experience_verification: Optional[ExperienceVerification] = Field(
        None, description="Проверка требования к опыту (если применимо)"
    )
    processing_time_ms: float = Field(..., description="Время обработки в миллисекундах")


class MatchFeedbackRequest(BaseModel):
    """Модель запроса для отправки отзыва о сопоставлении навыков."""

    match_id: str = Field(..., description="ID результата сопоставления")
    skill: str = Field(..., description="Имя навыка, который был сопоставлен")
    was_correct: bool = Field(..., description="Было ли сопоставение ИИ корректным")
    recruiter_correction: Optional[str] = Field(
        None, description="На что рекрутёр исправил значение (если неверно)"
    )
    confidence_score: Optional[float] = Field(
        None,
        description="Оценка уверенности, назначенная ИИ (0-1)",
        ge=0,
        le=1,
    )
    extra_metadata: Optional[dict] = Field(None, description="Дополнительные метаданные отзыва")


class MatchFeedbackResponse(BaseModel):
    """Модель ответа для отправки отзыва о сопоставлении."""

    id: str = Field(..., description="Уникальный идентификатор записи отзыва")
    match_id: str = Field(..., description="ID результата сопоставления")
    skill: str = Field(..., description="Имя навыка, который был сопоставлен")
    was_correct: bool = Field(..., description="Было ли сопоставение ИИ корректным")
    recruiter_correction: Optional[str] = Field(None, description="Поправка рекрутёра")
    feedback_source: str = Field(..., description="Источник отзыва")
    processed: bool = Field(..., description="Был ли отзыв обработан ML-конвейером")
    created_at: str = Field(..., description="Временная метка создания")


@router.post(
    "/compare",
    response_model=MatchResponse,
    status_code=status.HTTP_200_OK,
    tags=["Matching"],
)
async def compare_resume_to_vacancy(
    http_request: Request,
    request: MatchRequest,
    db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    """
    Сравнить резюме с вакансией с учётом синонимов навыков.

    Этот эндпоинт выполняет интеллектуальное сопоставление навыков резюме и требований
    вакансии, обрабатывая синонимы (например, PostgreSQL ≈ SQL) и предоставляя
    визуальное выделение для рекрутёров.

    Возможности:
    - Сопоставление синонимов навыков (PostgreSQL соответствует требованию SQL)
    - Расчёт процента совпадения
    - Визуальное выделение (зелёный=совпало, красный=отсутствует)
    - Проверка опыта (суммирует месяцы по проектам)
    - Сравнение без учёта регистра
    - Поддержка навыков из нескольких слов

    Args:
        http_request: Объект запроса FastAPI (для заголовка Accept-Language)
        request: Запрос на сопоставление с resume_id и vacancy_data

    Returns:
        JSON-ответ с результатами сопоставления, данными выделения и проверкой

    Raises:
        HTTPException(404): Если файл резюме не найден
        HTTPException(422): Если извлечение текста не удалось
        HTTPException(500): Если обработка сопоставления не удалась

    Examples:
        >>> import requests
        >>> vacancy = {
        ...     "title": "Java Developer",
        ...     "required_skills": ["Java", "Spring", "SQL"],
        ...     "min_experience_months": 36
        ... }
        >>> response = requests.post(
        ...     "http://localhost:8000/api/matching/compare",
        ...     json={"resume_id": "abc123", "vacancy_data": vacancy}
        ... )
        >>> response.json()
        {
            "resume_id": "abc123",
            "vacancy_title": "Java Developer",
            "match_percentage": 66.67,
            "required_skills_match": [
                {"skill": "Java", "status": "matched", "matched_as": "Java", "highlight": "green"},
                {"skill": "Spring", "status": "matched", "matched_as": "Spring Boot", "highlight": "green"},
                {"skill": "SQL", "status": "matched", "matched_as": "PostgreSQL", "highlight": "green"}
            ],
            "additional_skills_match": [],
            "experience_verification": {
                "required_months": 36,
                "actual_months": 47,
                "meets_requirement": true,
                "summary": "47 months (3 years 11 months) of experience"
            },
            "processing_time_ms": 123.45
        }
    """
    import time

    # Извлечение локали из заголовка Accept-Language
    locale = _extract_locale(http_request)

    start_time = time.time()

    try:
        logger.info(f"Начало сопоставления для resume_id: {request.resume_id}")

        # Шаг 1: Найти файл резюме
        for ext in [".pdf", ".docx", ".PDF", ".DOCX"]:
            file_path = UPLOAD_DIR / f"{request.resume_id}{ext}"
            if file_path.exists():
                break
        else:
            error_msg = get_error_message("file_not_found", locale)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_msg,
            )

        logger.info(f"Найден файл резюме: {file_path}")

        # Шаг 2: Извлечь текст из файла
        try:
            from services.data_extractor.extract import extract_text_from_pdf, extract_text_from_docx

            file_ext = file_path.suffix.lower()
            if file_ext == ".pdf":
                result = extract_text_from_pdf(file_path)
            elif file_ext == ".docx":
                result = extract_text_from_docx(file_path)
            else:
                error_msg = get_error_message("invalid_file_type", locale, file_ext=file_ext, allowed=".pdf, .docx")
                raise HTTPException(
                    status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                    detail=error_msg,
                )

            if result.get("error"):
                error_msg = get_error_message("extraction_failed", locale)
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=error_msg,
                )

            resume_text = result.get("text", "")
            if not resume_text or len(resume_text.strip()) < 10:
                error_msg = get_error_message("file_corrupted", locale)
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=error_msg,
                )

            logger.info(f"Извлечено {len(resume_text)} символов из резюме")

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Ошибка извлечения текста: {e}", exc_info=True)
            error_msg = get_error_message("extraction_failed", locale)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error_msg,
            ) from e

        # Шаг 3: Определить язык
        try:
            from langdetect import detect, LangDetectException

            try:
                detected_lang = detect(resume_text)
                language = "ru" if detected_lang == "ru" else "en"
            except LangDetectException:
                language = "en"
        except ImportError:
            language = "en"

        logger.info(f"Обнаруженный язык: {language}")

        # Шаг 4: Извлечь навыки из резюме
        logger.info("Извлечение навыков из резюме...")

        # Сначала пытаемся получить сохранённый анализ
        from uuid import UUID
        from models.resume_analysis import ResumeAnalysis
        saved_analysis = await db.execute(
            select(ResumeAnalysis).where(ResumeAnalysis.resume_id == UUID(request.resume_id))
        )
        analysis_obj = saved_analysis.scalar_one_or_none()

        # Вспомогательная функция для извлечения строк из кортежей
        def extract_strings(items):
            """Извлечь строковые ключевые слова из кортежей или списков."""
            result = []
            for item in items:
                if isinstance(item, (list, tuple)):
                    result.append(str(item[0]) if item else "")
                else:
                    result.append(str(item))
            return result

        if analysis_obj and analysis_obj.skills:
            # Используем сохранённые навыки из базы данных
            resume_skills = analysis_obj.skills
            logger.info(f"Используем {len(resume_skills)} сохранённых навыков из базы данных")
        else:
            # Извлекаем навыки из текста
            keywords_result = extract_resume_keywords(
                resume_text, language=language
            )
            entities_result = extract_resume_entities(resume_text, language=language)

            # Извлекаем строки из кортежей (keywords/keyphrases могут быть кортежами)
            keywords_list = extract_strings(keywords_result.get("keywords") or [])
            keyphrases_list = extract_strings(keywords_result.get("keyphrases") or [])
            tech_skills = entities_result.get("technical_skills") or []

            # Объединяем все навыки
            resume_skills = list(set(keywords_list + keyphrases_list + tech_skills))

        logger.info(f"Извлечено {len(resume_skills)} уникальных навыков из резюме")

        # Шаг 5: Инициализировать улучшенный сопоставитель навыков
        enhanced_matcher = EnhancedSkillMatcher()
        # Предварительная загрузка синонимов для логирования
        synonyms_map = enhanced_matcher.load_synonyms()
        logger.info(f"Инициализирован улучшенный сопоставитель с {len(synonyms_map)} отображениями синонимов")

        # Шаг 6: Получить данные вакансии
        vacancy_title = request.vacancy_data.get(
            "title", request.vacancy_data.get("position", "Unknown Position")
        )
        # Поддержка как required_skills, так и mandatory_requirements
        required_skills = request.vacancy_data.get("required_skills") or request.vacancy_data.get("mandatory_requirements", [])
        # Поддержка как additional_requirements, так и optional_requirements
        additional_skills = request.vacancy_data.get("additional_requirements") or request.vacancy_data.get("optional_skills", []) or request.vacancy_data.get("additional_skills", [])
        min_experience_months = request.vacancy_data.get("min_experience_months", None)

        # Если required_skills - строковый список, используем напрямую
        if isinstance(required_skills, str):
            required_skills = [required_skills]

        # Шаг 7: Сопоставить обязательные навыки с улучшенным сопоставителем
        required_skills_matches = []
        for skill in required_skills:
            # Используем улучшенный сопоставитель с учётом контекста
            match_result = enhanced_matcher.match_with_context(
                resume_skills=resume_skills,
                required_skill=skill,
                context=vacancy_title.lower(),  # Используем название вакансии как подсказку контекста
                use_fuzzy=True  # Включаем нечёткое сопоставление
            )

            if match_result["matched"]:
                required_skills_matches.append(
                    SkillMatch(
                        skill=skill,
                        status="matched",
                        matched_as=match_result["matched_as"],
                        highlight="green",
                        confidence=round(match_result["confidence"], 2),
                        match_type=match_result["match_type"]
                    )
                )
            else:
                required_skills_matches.append(
                    SkillMatch(
                        skill=skill,
                        status="missing",
                        matched_as=None,
                        highlight="red",
                        confidence=0.0,
                        match_type="none"
                    )
                )

        # Шаг 8: Сопоставить дополнительные/желательные навыки с улучшенным сопоставителем
        additional_skills_matches = []
        for skill in additional_skills:
            # Используем улучшенный сопоставитель с учётом контекста
            match_result = enhanced_matcher.match_with_context(
                resume_skills=resume_skills,
                required_skill=skill,
                context=vacancy_title.lower(),  # Используем название вакансии как подсказку контекста
                use_fuzzy=True  # Включаем нечёткое сопоставление
            )

            if match_result["matched"]:
                additional_skills_matches.append(
                    SkillMatch(
                        skill=skill,
                        status="matched",
                        matched_as=match_result["matched_as"],
                        highlight="green",
                        confidence=round(match_result["confidence"], 2),
                        match_type=match_result["match_type"]
                    )
                )
            else:
                additional_skills_matches.append(
                    SkillMatch(
                        skill=skill,
                        status="missing",
                        matched_as=None,
                        highlight="red",
                        confidence=0.0,
                        match_type="none"
                    )
                )

        # Шаг 9: Рассчитать процент совпадения
        total_required = len(required_skills)
        matched_required = sum(
            1 for m in required_skills_matches if m.status == "matched"
        )
        match_percentage = (
            round((matched_required / total_required * 100), 2) if total_required > 0 else 0.0
        )

        logger.info(
            f"Сопоставлено {matched_required}/{total_required} обязательных навыков ({match_percentage}%)"
        )

        # Шаг 10: Проверить опыт (если вакансия имеет требование к опыту)
        experience_verification = None
        if min_experience_months and min_experience_months > 0:
            logger.info(f"Проверка требования к опыту: {min_experience_months} месяцев")

            # Пытаемся получить опыт из основного навыка вакансии
            # Пока используем первый обязательный навык как основной
            primary_skill = required_skills[0] if required_skills else None

            if primary_skill:
                try:
                    # Пока пропускаем расчёт опыта, так как требуются распаршенные данные опыта
                    # TODO: Реализовать парсинг резюме для извлечения структурированных записей опыта
                    logger.info(f"Пропуск расчёта опыта для {primary_skill} - требуются распаршенные данные опыта")
                except Exception as e:
                    logger.warning(f"Расчёт опыта не удался: {e}")
                    # Продолжаем без проверки опыта

        # Расчёт времени обработки
        processing_time_ms = (time.time() - start_time) * 1000

        # Формирование ответа
        response_data = {
            "resume_id": request.resume_id,
            "vacancy_title": vacancy_title,
            "match_percentage": match_percentage,
            "required_skills_match": [
                m.model_dump() for m in required_skills_matches
            ],
            "additional_skills_match": [
                m.model_dump() for m in additional_skills_matches
            ],
            "experience_verification": (
                experience_verification.model_dump() if experience_verification else None
            ),
            "processing_time_ms": round(processing_time_ms, 2),
        }

        logger.info(
            f"Сопоставление завершено для resume_id {request.resume_id} за {processing_time_ms:.2f}мс"
        )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=response_data,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка сопоставления резюме с вакансией: {e}", exc_info=True)
        error_msg = get_error_message("parsing_failed", locale)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_msg,
        ) from e


@router.post(
    "/feedback",
    response_model=MatchFeedbackResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Matching"],
)
async def submit_match_feedback(http_request: Request, request: MatchFeedbackRequest) -> JSONResponse:
    """
    Отправить отзыв о результате сопоставления навыков.

    Этот эндпоинт позволяет рекрутёрам оставлять отзывы о решениях ИИ по сопоставлению
    навыков, записывая, были ли совпадения корректными и какие нужны исправления.
    Эти отзывы используются для улучшения точности будущего сопоставления через ML-переобучение.

    Args:
        http_request: Объект запроса FastAPI (для заголовка Accept-Language)
        request: Запрос отзыва с деталями сопоставления и исправлениями рекрутёра

    Returns:
        JSON-ответ с созданной записью отзыва

    Raises:
        HTTPException(422): Если валидация не прошла
        HTTPException(500): Если операция с базой данных не удалась

    Examples:
        >>> import requests
        >>> data = {
        ...     "match_id": "match123",
        ...     "skill": "React",
        ...     "was_correct": True,
        ...     "recruiter_correction": None
        ... }
        >>> response = requests.post(
        ...     "http://localhost:8000/api/matching/feedback",
        ...     json=data
        ... )
        >>> response.json()
        {
            "id": "feedback-id",
            "match_id": "match123",
            "skill": "React",
            "was_correct": True,
            "recruiter_correction": None,
            "feedback_source": "matching_api",
            "processed": False,
            "created_at": "2024-01-25T00:00:00Z"
        }
    """
    # Извлечение локали из заголовка Accept-Language
    locale = _extract_locale(http_request)

    try:
        logger.info(
            f"Отправка отзыва для match_id: {request.match_id}, "
            f"skill: {request.skill}, was_correct: {request.was_correct}"
        )

        # Валидация оценки уверенности, если указана
        if request.confidence_score is not None and not (
            0 <= request.confidence_score <= 1
        ):
            error_msg = get_error_message("value_out_of_range", locale, field="confidence_score")
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=error_msg,
            )

        # Пока возвращаем заглушку ответа
        # Интеграция с базой данных будет добавлена в следующей подзадаче
        feedback_response = {
            "id": "placeholder-feedback-id",
            "match_id": request.match_id,
            "skill": request.skill,
            "was_correct": request.was_correct,
            "recruiter_correction": request.recruiter_correction,
            "feedback_source": "matching_api",
            "processed": False,
            "created_at": "2024-01-25T00:00:00Z",
        }

        logger.info(f"Создана запись отзыва для match_id: {request.match_id}")

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content=feedback_response,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка отправки отзыва о сопоставлении: {e}", exc_info=True)
        error_msg = get_error_message("database_error", locale)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_msg,
        ) from e


class UnifiedMatchRequest(BaseModel):
    """Модель запроса для унифицированного эндпоинта подбора вакансии."""

    resume_id: str = Field(..., description="Уникальный идентификатор резюме для сопоставления")
    vacancy_data: Dict[str, Any] = Field(
        ..., description="Данные вакансии с требуемыми навыками и опытом"
    )
    use_unified: bool = Field(True, description="Использовать унифицированный сопоставитель (TF-IDF + Vector + Keyword)")


@router.post(
    "/compare-unified",
    status_code=status.HTTP_200_OK,
    tags=["Matching"],
)
async def compare_resume_to_vacancy_unified(
    http_request: Request,
    request: UnifiedMatchRequest,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Сравнить резюме с вакансией, используя унифицированное сопоставление (TF-IDF + Vector + Keyword).

    Этот эндпоинт обеспечивает комплексное сопоставление с использованием трёх взаимодополняющих подходов:
    1. Улучшенное сопоставление по ключевым словам (синонимы, нечёткое, составные навыки)
    2. Взвешенное сопоставление TF-IDF (оценка на основе важности)
    3. Векторная семантическая схожесть (sentence-transformers)

    Общая оценка является взвешенной комбинацией всех трёх методов для максимально
    точных результатов сопоставления.

    Args:
        http_request: Объект запроса FastAPI (для заголовка Accept-Language)
        request: Запрос на сопоставление с resume_id и vacancy_data

    Returns:
        JSON-ответ с комплексными результатами сопоставления, включая:
        - overall_score: Взвешенная комбинация всех методов (0-1)
        - keyword_score: Оценка улучшенного сопоставления по ключевым словам
        - tfidf_score: Взвешенная оценка TF-IDF
        - vector_score: Оценка семантической схожести
        - matched_skills: Список совпавших навыков
        - missing_skills: Список отсутствующих навыков (ранжированных по важности)
        - recommendation: Рекомендация по найму (excellent/good/maybe/poor)

    Raises:
        HTTPException(404): Если файл резюме не найден
        HTTPException(500): Если обработка сопоставления не удалась

    Examples:
        >>> import requests
        >>> vacancy = {
        ...     "title": "React Developer",
        ...     "description": "Looking for React expert with TypeScript",
        ...     "required_skills": ["React", "TypeScript", "JavaScript"]
        ... }
        >>> response = requests.post(
        ...     "http://localhost:8000/api/matching/compare-unified",
        ...     json={"resume_id": "abc123", "vacancy_data": vacancy}
        ... )
        >>> response.json()
        {
            "resume_id": "abc123",
            "vacancy_title": "React Developer",
            "overall_score": 0.75,
            "keyword_score": 0.67,
            "tfidf_score": 0.80,
            "vector_score": 0.72,
            "passed": true,
            "recommendation": "good",
            "matched_skills": ["React", "JavaScript"],
            "missing_skills": ["TypeScript"],
            "processing_time_ms": 250.5
        }
    """
    import time

    locale = _extract_locale(http_request)
    start_time = time.time()

    try:
        logger.info(f"Начало унифицированного сопоставления для resume_id: {request.resume_id}")

        # Шаг 1: Пытаемся найти файл резюме ИЛИ использовать данные из базы данных
        resume_text = None
        file_path = None

        # Сначала пытаемся найти файл
        for ext in [".pdf", ".docx", ".PDF", ".DOCX"]:
            potential_path = UPLOAD_DIR / f"{request.resume_id}{ext}"
            if potential_path.exists():
                file_path = potential_path
                break

        # Шаг 2: Извлечь текст из файла или использовать резервный вариант из базы данных
        if file_path:
            # Извлечение из файла
            try:
                from services.data_extractor.extract import extract_text_from_pdf, extract_text_from_docx

                file_ext = file_path.suffix.lower()
                if file_ext == ".pdf":
                    result = extract_text_from_pdf(str(file_path))
                elif file_ext == ".docx":
                    result = extract_text_from_docx(str(file_path))
                else:
                    raise HTTPException(
                        status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                        detail="Неподдерживаемый тип файла",
                    )

                resume_text = result.get("text", "")
                if not resume_text or len(resume_text.strip()) < 10:
                    resume_text = None

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Ошибка извлечения текста из файла: {e}")
                resume_text = None

        # Резервный вариант: пытаемся получить текст из базы данных
        if not resume_text:
            try:
                from models.resume import Resume as ResumeModel
                from models.resume_analysis import ResumeAnalysis

                resume_uuid = UUID(request.resume_id)
                resume_query = select(ResumeModel).where(ResumeModel.id == resume_uuid)
                resume_result = await db.execute(resume_query)
                resume_record = resume_result.scalar_one_or_none()

                if resume_record and resume_record.raw_text:
                    resume_text = resume_record.raw_text
                    logger.info(f"Используем raw_text из базы данных для резюме {request.resume_id}")
                elif resume_record:
                    # Пытаемся получить из ResumeAnalysis
                    analysis_query = select(ResumeAnalysis).where(
                        ResumeAnalysis.resume_id == resume_uuid
                    )
                    analysis_result = await db.execute(analysis_query)
                    analysis_record = analysis_result.scalar_one_or_none()

                    if analysis_record and analysis_record.raw_text:
                        resume_text = analysis_record.raw_text
                        logger.info(f"Используем raw_text из ResumeAnalysis для резюме {request.resume_id}")
                    else:
                        logger.warning(f"Текст не найден для резюме {request.resume_id}")
                else:
                    logger.warning(f"Резюме {request.resume_id} не найдено в базе данных")

            except Exception as e:
                logger.error(f"Ошибка получения резюме из базы данных: {e}")

        if not resume_text or len(resume_text.strip()) < 10:
            # Возвращаем ответ по умолчанию с нулями
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "resume_id": request.resume_id,
                    "vacancy_title": request.vacancy_data.get("title", "Unknown"),
                    "overall_score": 0.0,
                    "passed": False,
                    "recommendation": "poor",
                    "keyword_score": 0.0,
                    "keyword_passed": False,
                    "tfidf_score": 0.0,
                    "tfidf_passed": False,
                    "tfidf_matched": [],
                    "tfidf_missing": request.vacancy_data.get("required_skills", [])[:5],
                    "vector_score": 0.0,
                    "vector_passed": False,
                    "vector_similarity": 0.0,
                    "matched_skills": [],
                    "missing_skills": request.vacancy_data.get("required_skills", []),
                    "processing_time_ms": 0.0,
                },
            )

        # Шаг 3: Извлечь навыки, используя сопоставление по шаблонам
        from analyzers.hf_skill_extractor import extract_resume_skills

        skills_result = extract_resume_skills(
            resume_text, method="pattern", top_n=30
        )
        resume_skills = skills_result.get("skills", [])

        logger.info(f"Извлечено {len(resume_skills)} навыков из резюме")

        # Шаг 4: Получить данные вакансии
        vacancy_title = request.vacancy_data.get(
            "title", request.vacancy_data.get("position", "Unknown Position")
        )
        vacancy_description = request.vacancy_data.get("description", "")
        required_skills = request.vacancy_data.get("required_skills", [])

        if isinstance(required_skills, str):
            required_skills = [required_skills]

        # Шаг 5: Использовать унифицированный сопоставитель
        unified_matcher = get_unified_matcher()

        # ОТЛАДКА: логируем, что передаётся сопоставителю
        logger.info(f"[DEBUG] resume_skills (len={len(resume_skills)}): {resume_skills[:10]}...")
        logger.info(f"[DEBUG] required_skills: {required_skills}")
        logger.info(f"[DEBUG] 'python' in resume_skills: {'python' in resume_skills}")

        match_result = unified_matcher.match(
            resume_text=resume_text,
            resume_skills=resume_skills,
            job_title=vacancy_title,
            job_description=vacancy_description,
            required_skills=required_skills,
            context=vacancy_title.lower(),
        )

        # ОТЛАДКА: логируем, что вернул сопоставитель
        logger.info(f"[DEBUG] match_result.matched_skills: {match_result.matched_skills}")
        logger.info(f"[DEBUG] match_result.missing_skills: {match_result.missing_skills}")

        processing_time_ms = (time.time() - start_time) * 1000

        # Шаг 6: Сохранить результаты сопоставления в базу данных
        try:
            # Парсинг resume_id как UUID
            resume_uuid = UUID(request.resume_id)

            # Получить vacancy_id из vacancy_data, если указан
            vacancy_id = request.vacancy_data.get("id")
            vacancy_uuid = UUID(vacancy_id) if vacancy_id else None

            # Проверить, существует ли уже результат сопоставления
            existing_match = None
            if vacancy_uuid:
                existing_query = select(MatchResult).where(
                    MatchResult.resume_id == resume_uuid,
                    MatchResult.vacancy_id == vacancy_uuid
                )
                existing_result = await db.execute(existing_query)
                existing_match = existing_result.scalar_one_or_none()

            # Подготовка данных сопоставления для сохранения
            match_percentage = round(match_result.overall_score * 100, 2)
            matched_skills_detailed = [
                {"skill": s, "matched": True}
                for s in match_result.matched_skills
            ]
            missing_skills_detailed = [
                {"skill": s, "matched": False}
                for s in match_result.missing_skills
            ]

            if existing_match:
                # Обновить существующую запись
                existing_match.match_percentage = match_percentage
                existing_match.matched_skills = matched_skills_detailed
                existing_match.missing_skills = missing_skills_detailed
                existing_match.overall_score = match_result.overall_score
                existing_match.keyword_score = match_result.keyword_score
                existing_match.tfidf_score = match_result.tfidf_score
                existing_match.vector_score = match_result.vector_score
                existing_match.vector_similarity = match_result.vector_similarity
                existing_match.recommendation = match_result.recommendation
                existing_match.keyword_passed = match_result.keyword_passed
                existing_match.tfidf_passed = match_result.tfidf_passed
                existing_match.vector_passed = match_result.vector_passed
                existing_match.tfidf_matched = match_result.tfidf_matched
                existing_match.tfidf_missing = match_result.tfidf_missing
                existing_match.matcher_version = "unified-v1"
                logger.info(f"Обновлён существующий результат сопоставления: {existing_match.id}")
            else:
                # Создать новую запись результата сопоставления (только если есть vacancy_id)
                if vacancy_uuid:
                    new_match = MatchResult(
                        resume_id=resume_uuid,
                        vacancy_id=vacancy_uuid,
                        match_percentage=match_percentage,
                        matched_skills=matched_skills_detailed,
                        missing_skills=missing_skills_detailed,
                        overall_score=match_result.overall_score,
                        keyword_score=match_result.keyword_score,
                        tfidf_score=match_result.tfidf_score,
                        vector_score=match_result.vector_score,
                        vector_similarity=match_result.vector_similarity,
                        recommendation=match_result.recommendation,
                        keyword_passed=match_result.keyword_passed,
                        tfidf_passed=match_result.tfidf_passed,
                        vector_passed=match_result.vector_passed,
                        tfidf_matched=match_result.tfidf_matched,
                        tfidf_missing=match_result.tfidf_missing,
                        matcher_version="unified-v1",
                    )
                    db.add(new_match)
                    logger.info(f"Создан новый результат сопоставления для резюме {resume_uuid} и вакансии {vacancy_uuid}")

            await db.commit()

        except ValueError as e:
            logger.warning(f"Неверный формат UUID, пропускаем сохранение в базу данных: {e}")
        except Exception as e:
            logger.error(f"Не удалось сохранить результат сопоставления в базу данных: {e}")
            await db.rollback()

        # Формирование ответа
        response_data = {
            "resume_id": request.resume_id,
            "vacancy_title": vacancy_title,
            "overall_score": match_result.overall_score,
            "passed": match_result.passed,
            "recommendation": match_result.recommendation,
            "keyword_score": match_result.keyword_score,
            "keyword_passed": match_result.keyword_passed,
            "tfidf_score": match_result.tfidf_score,
            "tfidf_passed": match_result.tfidf_passed,
            "tfidf_matched": match_result.tfidf_matched,
            "tfidf_missing": match_result.tfidf_missing,
            "vector_score": match_result.vector_score,
            "vector_passed": match_result.vector_passed,
            "vector_similarity": match_result.vector_similarity,
            "matched_skills": match_result.matched_skills,
            "missing_skills": match_result.missing_skills,
            "processing_time_ms": round(processing_time_ms, 2),
        }

        logger.info(
            f"Унифицированное сопоставление завершено для resume_id {request.resume_id}: "
            f"score={match_result.overall_score:.2f}, "
            f"recommendation={match_result.recommendation}"
        )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=response_data,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка в унифицированном сопоставлении: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Унифицированное сопоставление не удалось: {str(e)}",
        ) from e
