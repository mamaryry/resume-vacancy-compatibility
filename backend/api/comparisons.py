"""
Эндпоинты сравнения резюме для анализа и ранжирования нескольких резюме.

Этот модуль предоставляет эндпоинты для создания, получения и управления
представлениями сравнения нескольких резюме с возможностями ранжирования,
фильтрации и сортировки.
"""
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# Add parent directory to path to import from data_extractor service
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "services" / "data_extractor"))

from analyzers import (
    extract_resume_keywords_hf as extract_resume_keywords,
    extract_resume_entities,
    calculate_skill_experience,
    format_experience_summary,
    EnhancedSkillMatcher,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# Директория, где хранятся загруженные резюме
UPLOAD_DIR = Path("data/uploads")

# Путь к файлу синонимов навыков
SYNONYMS_FILE = Path(__file__).parent.parent / "models" / "skill_synonyms.json"


def compare_multiple_resumes(
    resume_ids: List[str],
    vacancy_data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Сравнить несколько резюме с вакансией и агрегировать результаты.

    Эта функция выполняет интеллектуальное сопоставление навыков каждого резюме
    с требованиями вакансии, обрабатывая синонимы (например, PostgreSQL ≈ SQL)
    и предоставляя агрегированные результаты с ранжированием по проценту совпадения.

    Возможности:
    - Сопоставление синонимов навыков (PostgreSQL соответствует требованию SQL)
    - Расчёт процента совпадения для каждого резюме
    - Проверка опыта для каждого резюме
    - Автоматическое ранжирование по проценту совпадения (по убыванию)
    - Отслеживание времени обработки

    Args:
        resume_ids: Список ID резюме для сравнения (2-5 резюме)
        vacancy_data: Данные вакансии с требуемыми навыками и опытом

    Returns:
        Словарь, содержащий:
        - vacancy_title: Название вакансии
        - comparison_results: Список результатов сопоставления для каждого резюме, ранжированный
        - total_resumes: Количество сравнённых резюме
        - processing_time_ms: Общее время обработки

    Raises:
        HTTPException(404): Если какой-либо файл резюме не найден
        HTTPException(422): Если извлечение текста не удалось для какого-либо резюме
        HTTPException(500): Если обработка сопоставления не удалась

    Example:
        >>> vacancy = {
        ...     "title": "Java Developer",
        ...     "required_skills": ["Java", "Spring", "SQL"],
        ...     "min_experience_months": 36
        ... }
        >>> results = compare_multiple_resumes(
        ...     ["resume1", "resume2", "resume3"],
        ...     vacancy
        ... )
        >>> results["comparison_results"][0]["rank"]
        1
    """
    start_time = time.time()

    try:
        logger.info(
            f"Starting comparison for {len(resume_ids)} resumes against vacancy: "
            f"{vacancy_data.get('title', 'Unknown')}"
        )

        # Проверка количества резюме
        if len(resume_ids) < 2:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="At least 2 resumes must be provided for comparison",
            )
        if len(resume_ids) > 5:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Maximum 5 resumes can be compared at once",
            )

        # Получение данных вакансии
        vacancy_title = vacancy_data.get(
            "title", vacancy_data.get("position", "Unknown Position")
        )
        required_skills = vacancy_data.get("required_skills", [])
        additional_skills = vacancy_data.get(
            "additional_requirements", vacancy_data.get("additional_skills", [])
        )
        min_experience_months = vacancy_data.get("min_experience_months", None)

        # Если required_skills - строковый список, используем напрямую
        if isinstance(required_skills, str):
            required_skills = [required_skills]

        # Обработка каждого резюме
        comparison_results = []

        for resume_id in resume_ids:
            try:
                logger.info(f"Processing resume_id: {resume_id}")

                # Шаг 1: Найти файл резюме
                for ext in [".pdf", ".docx", ".PDF", ".DOCX"]:
                    file_path = UPLOAD_DIR / f"{resume_id}{ext}"
                    if file_path.exists():
                        break
                else:
                    logger.warning(f"Resume file not found: {resume_id}")
                    # Добавляем результат-заглушку для отсутствующих резюме
                    comparison_results.append({
                        "resume_id": resume_id,
                        "vacancy_title": vacancy_title,
                        "match_percentage": 0.0,
                        "required_skills_match": [],
                        "additional_skills_match": [],
                        "experience_verification": None,
                        "processing_time_ms": 0.0,
                        "error": "Resume file not found",
                    })
                    continue

                # Шаг 2: Извлечь текст из файла
                try:
                    from services.data_extractor.extract import extract_text_from_pdf, extract_text_from_docx

                    file_ext = file_path.suffix.lower()
                    if file_ext == ".pdf":
                        result = extract_text_from_pdf(file_path)
                    elif file_ext == ".docx":
                        result = extract_text_from_docx(file_path)
                    else:
                        raise HTTPException(
                            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                            detail=f"Unsupported file type: {file_ext}",
                        )

                    if result.get("error"):
                        raise HTTPException(
                            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail=f"Text extraction failed: {result['error']}",
                        )

                    resume_text = result.get("text", "")
                    if not resume_text or len(resume_text.strip()) < 10:
                        raise HTTPException(
                            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail="Extracted text is too short or empty",
                        )

                    logger.info(f"Extracted {len(resume_text)} characters from resume")

                except HTTPException:
                    raise
                except Exception as e:
                    logger.error(f"Error extracting text: {e}", exc_info=True)
                    comparison_results.append({
                        "resume_id": resume_id,
                        "vacancy_title": vacancy_title,
                        "match_percentage": 0.0,
                        "required_skills_match": [],
                        "additional_skills_match": [],
                        "experience_verification": None,
                        "processing_time_ms": 0.0,
                        "error": f"Text extraction failed: {str(e)}",
                    })
                    continue

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

                logger.info(f"Detected language: {language}")

                # Шаг 4: Извлечь навыки из резюме
                logger.info("Extracting skills from resume...")
                keywords_result = extract_resume_keywords(
                    resume_text, language=language, top_n=50
                )
                entities_result = extract_resume_entities(resume_text, language=language)

                # Объединить ключевые слова и технические навыки
                resume_skills = list(set(
                    keywords_result.get("keywords", []) +
                    keywords_result.get("keyphrases", []) +
                    entities_result.get("technical_skills", [])
                ))

                logger.info(f"Extracted {len(resume_skills)} unique skills from resume")

                # Шаг 5: Инициализировать улучшенный сопоставитель навыков
                enhanced_matcher = EnhancedSkillMatcher()
                synonyms_map = enhanced_matcher.load_synonyms()
                logger.info(f"Initialized enhanced skill matcher with {len(synonyms_map)} synonym mappings")

                # Шаг 6: Сопоставить обязательные навыки
                required_skills_matches = []
                for skill in required_skills:
                    match_result = enhanced_matcher.match_with_context(
                        resume_skills=resume_skills,
                        required_skill=skill,
                        context=vacancy_title.lower(),
                        use_fuzzy=True
                    )

                    if match_result["matched"]:
                        required_skills_matches.append({
                            "skill": skill,
                            "status": "matched",
                            "matched_as": match_result["matched_as"],
                            "highlight": "green",
                            "confidence": round(match_result["confidence"], 2),
                            "match_type": match_result["match_type"]
                        })
                    else:
                        required_skills_matches.append({
                            "skill": skill,
                            "status": "missing",
                            "matched_as": None,
                            "highlight": "red",
                            "confidence": 0.0,
                            "match_type": "none"
                        })

                # Шаг 7: Сопоставить дополнительные/желательные навыки
                additional_skills_matches = []
                for skill in additional_skills:
                    match_result = enhanced_matcher.match_with_context(
                        resume_skills=resume_skills,
                        required_skill=skill,
                        context=vacancy_title.lower(),
                        use_fuzzy=True
                    )

                    if match_result["matched"]:
                        additional_skills_matches.append({
                            "skill": skill,
                            "status": "matched",
                            "matched_as": match_result["matched_as"],
                            "highlight": "green",
                            "confidence": round(match_result["confidence"], 2),
                            "match_type": match_result["match_type"]
                        })
                    else:
                        additional_skills_matches.append({
                            "skill": skill,
                            "status": "missing",
                            "matched_as": None,
                            "highlight": "red",
                            "confidence": 0.0,
                            "match_type": "none"
                        })

                # Шаг 8: Рассчитать процент совпадения
                total_required = len(required_skills)
                matched_required = sum(
                    1 for m in required_skills_matches if m["status"] == "matched"
                )
                match_percentage = (
                    round((matched_required / total_required * 100), 2) if total_required > 0 else 0.0
                )

                logger.info(
                    f"Matched {matched_required}/{total_required} required skills ({match_percentage}%)"
                )

                # Шаг 9: Проверить опыт (если вакансия имеет требование к опыту)
                experience_verification = None
                if min_experience_months and min_experience_months > 0:
                    logger.info(f"Verifying experience requirement: {min_experience_months} months")

                    primary_skill = required_skills[0] if required_skills else None

                    if primary_skill:
                        try:
                            skill_exp_result = calculate_skill_experience(
                                resume_text, primary_skill, language=language
                            )
                            actual_months = skill_exp_result.get("total_months", 0)
                            experience_summary = format_experience_summary(actual_months)

                            experience_verification = {
                                "required_months": min_experience_months,
                                "actual_months": actual_months,
                                "meets_requirement": actual_months >= min_experience_months,
                                "summary": experience_summary,
                            }

                            logger.info(
                                f"Experience verification: {actual_months} months (required: {min_experience_months})"
                            )

                        except Exception as e:
                            logger.warning(f"Experience calculation failed: {e}")
                            # Продолжаем без проверки опыта

                # Формируем результат для этого резюме
                resume_result = {
                    "resume_id": resume_id,
                    "vacancy_title": vacancy_title,
                    "match_percentage": match_percentage,
                    "required_skills_match": required_skills_matches,
                    "additional_skills_match": additional_skills_matches,
                    "experience_verification": experience_verification,
                    "processing_time_ms": 0.0,  # Will be updated after total time calculation
                }

                comparison_results.append(resume_result)

            except Exception as e:
                logger.error(f"Error processing resume {resume_id}: {e}", exc_info=True)
                comparison_results.append({
                    "resume_id": resume_id,
                    "vacancy_title": vacancy_title,
                    "match_percentage": 0.0,
                    "required_skills_match": [],
                    "additional_skills_match": [],
                    "experience_verification": None,
                    "processing_time_ms": 0.0,
                    "error": str(e),
                })

        # Шаг 10: Сортировать результаты по проценту совпадения (по убыванию)
        comparison_results.sort(key=lambda x: x.get("match_percentage", 0), reverse=True)

        # Назначить ранги
        for idx, result in enumerate(comparison_results, start=1):
            result["rank"] = idx

        # Рассчитать общее время обработки
        total_processing_time_ms = (time.time() - start_time) * 1000

        # Распределить время обработки по резюме (приблизительно)
        if comparison_results:
            time_per_resume = total_processing_time_ms / len(comparison_results)
            for result in comparison_results:
                if "error" not in result:
                    result["processing_time_ms"] = round(time_per_resume, 2)

        logger.info(
            f"Comparison completed for {len(resume_ids)} resumes in {total_processing_time_ms:.2f}ms"
        )

        return {
            "vacancy_title": vacancy_title,
            "comparison_results": comparison_results,
            "total_resumes": len(resume_ids),
            "processing_time_ms": round(total_processing_time_ms, 2),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error comparing multiple resumes: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compare resumes: {str(e)}",
        ) from e


class ComparisonCreate(BaseModel):
    """Модель запроса для создания представления сравнения."""

    vacancy_id: str = Field(..., description="ID вакансии для сравнения")
    resume_ids: List[str] = Field(..., description="Список ID резюме для сравнения (2-5 резюме)", min_length=2, max_length=5)
    name: Optional[str] = Field(None, description="Опциональное название для представления сравнения")
    filters: Optional[dict] = Field(None, description="Настройки фильтрации (диапазон совпадения, поле сортировки и т.д.)")
    created_by: Optional[str] = Field(None, description="Идентификатор пользователя, создавшего сравнение")
    shared_with: Optional[List[str]] = Field(None, description="Список ID пользователей/email для совместного доступа")


class ComparisonUpdate(BaseModel):
    """Модель запроса для обновления представления сравнения."""

    name: Optional[str] = Field(None, description="Обновлённое название для представления сравнения")
    filters: Optional[dict] = Field(None, description="Обновлённые настройки фильтрации")
    shared_with: Optional[List[str]] = Field(None, description="Обновлённый список пользователей для совместного доступа")


class ComparisonResponse(BaseModel):
    """Модель ответа для представления сравнения."""

    id: str = Field(..., description="Уникальный идентификатор сравнения")
    vacancy_id: str = Field(..., description="ID вакансии")
    resume_ids: List[str] = Field(..., description="Список ID сравниваемых резюме")
    name: Optional[str] = Field(None, description="Название представления сравнения")
    filters: Optional[dict] = Field(None, description="Настройки фильтрации")
    created_by: Optional[str] = Field(None, description="Пользователь, создавший сравнение")
    shared_with: Optional[List[str]] = Field(None, description="Список пользователей с совместным доступом")
    comparison_results: Optional[List[dict]] = Field(None, description="Результаты сопоставления для каждого резюме")
    created_at: str = Field(..., description="Временная метка создания")
    updated_at: str = Field(..., description="Временная метка последнего обновления")


class ComparisonListResponse(BaseModel):
    """Модель ответа для списка представлений сравнения."""

    comparisons: List[ComparisonResponse] = Field(..., description="Список представлений сравнения")
    total_count: int = Field(..., description="Общее количество представлений сравнения")


@router.post(
    "/",
    response_model=ComparisonResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Comparisons"],
)
async def create_comparison(request: ComparisonCreate) -> JSONResponse:
    """
    Создать новое представление сравнения резюме.

    Этот эндпоинт создаёт новое представление сравнения для анализа нескольких резюме
    бок о бок с вакансией. Сравнение можно сохранить с фильтрами, поделиться с
    командой и получить позже.

    Args:
        request: Запрос на создание с vacancy_id, resume_ids и опциональными настройками

    Returns:
        JSON-ответ с деталями созданного представления сравнения

    Raises:
        HTTPException(422): Если валидация не прошла
        HTTPException(500): Если операция с базой данных не удалась

    Examples:
        >>> import requests
        >>> data = {
        ...     "vacancy_id": "vacancy-123",
        ...     "resume_ids": ["resume1", "resume2", "resume3"],
        ...     "name": "Senior Developer Candidates"
        ... }
        >>> response = requests.post("http://localhost:8000/api/comparisons/", json=data)
        >>> response.json()
        {
            "id": "comp-123",
            "vacancy_id": "vacancy-123",
            "resume_ids": ["resume1", "resume2", "resume3"],
            "name": "Senior Developer Candidates",
            "filters": None,
            "created_by": None,
            "shared_with": None,
            "comparison_results": None,
            "created_at": "2024-01-25T00:00:00Z",
            "updated_at": "2024-01-25T00:00:00Z"
        }
    """
    try:
        logger.info(
            f"Creating comparison for vacancy_id: {request.vacancy_id} "
            f"with {len(request.resume_ids)} resumes"
        )

        # Проверка количества resume_ids
        if len(request.resume_ids) < 2:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="At least 2 resumes must be provided for comparison",
            )
        if len(request.resume_ids) > 5:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Maximum 5 resumes can be compared at once",
            )

        # Пока возвращаем ответ-заглушку
        # Интеграция с базой данных будет добавлена в следующей подзадаче, когда будет настроена async session
        comparison_response = {
            "id": "placeholder-comparison-id",
            "vacancy_id": request.vacancy_id,
            "resume_ids": request.resume_ids,
            "name": request.name,
            "filters": request.filters,
            "created_by": request.created_by,
            "shared_with": request.shared_with,
            "comparison_results": None,
            "created_at": "2024-01-25T00:00:00Z",
            "updated_at": "2024-01-25T00:00:00Z",
        }

        logger.info(
            f"Created comparison for vacancy {request.vacancy_id} "
            f"with {len(request.resume_ids)} resumes"
        )

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content=comparison_response,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating comparison: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create comparison: {str(e)}",
        ) from e


@router.get("/", tags=["Comparisons"])
async def list_comparisons(
    vacancy_id: Optional[str] = Query(None, description="Filter by vacancy ID"),
    created_by: Optional[str] = Query(None, description="Filter by creator user ID"),
    min_match_percentage: Optional[float] = Query(None, description="Filter by minimum match percentage", ge=0, le=100),
    max_match_percentage: Optional[float] = Query(None, description="Filter by maximum match percentage", ge=0, le=100),
    sort_by: Optional[str] = Query("created_at", description="Sort field (created_at, match_percentage, name)"),
    order: Optional[str] = Query("desc", description="Sort order (asc or desc)"),
    limit: int = Query(50, description="Maximum number of comparisons to return", ge=1, le=100),
    offset: int = Query(0, description="Number of comparisons to skip", ge=0),
) -> JSONResponse:
    """
    Получить список представлений сравнения резюме с опциональными фильтрами и сортировкой.

    Args:
        vacancy_id: Опциональный фильтр по ID вакансии
        created_by: Опциональный фильтр по ID пользователя-создателя
        min_match_percentage: Опциональный фильтр минимального процента совпадения (0-100)
        max_match_percentage: Опциональный фильтр максимального процента совпадения (0-100)
        sort_by: Поле сортировки - created_at, match_percentage или name (по умолчанию: created_at)
        order: Порядок сортировки - asc или desc (по умолчанию: desc)
        limit: Максимальное количество результатов для возврата (по умолчанию: 50, максимум: 100)
        offset: Количество результатов для пропуска (по умолчанию: 0)

    Returns:
        JSON-ответ со списком представлений сравнения

    Raises:
        HTTPException(422): Если параметры sort_by или order недействительны
        HTTPException(500): Если запрос к базе данных не удался

    Examples:
        >>> import requests
        >>> # List comparisons for a specific vacancy
        >>> response = requests.get("http://localhost:8000/api/comparisons/?vacancy_id=vac-123")
        >>> # Sort by match percentage descending
        >>> response = requests.get("http://localhost:8000/api/comparisons/?sort_by=match_percentage&order=desc")
        >>> # Filter by match percentage range
        >>> response = requests.get("http://localhost:8000/api/comparisons/?min_match_percentage=50&max_match_percentage=90")
        >>> response.json()
    """
    try:
        # Проверка параметра sort_by
        valid_sort_fields = ["created_at", "match_percentage", "name", "updated_at"]
        if sort_by and sort_by not in valid_sort_fields:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid sort_by field. Must be one of: {', '.join(valid_sort_fields)}",
            )

        # Проверка параметра order
        valid_orders = ["asc", "desc"]
        if order and order not in valid_orders:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid order field. Must be one of: {', '.join(valid_orders)}",
            )

        # Проверка диапазона процента совпадения
        if min_match_percentage is not None and max_match_percentage is not None:
            if min_match_percentage > max_match_percentage:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="min_match_percentage must be less than or equal to max_match_percentage",
                )

        logger.info(
            f"Listing comparisons with filters - vacancy_id: {vacancy_id}, "
            f"created_by: {created_by}, min_match_percentage: {min_match_percentage}, "
            f"max_match_percentage: {max_match_percentage}, sort_by: {sort_by}, "
            f"order: {order}, limit: {limit}, offset: {offset}"
        )

        # Пока возвращаем ответ-заглушку
        # Интеграция с базой данных будет добавлена в следующей подзадаче, когда будет настроена async session
        # При интеграции с БД фильтры и сортировка будут применяться на уровне запроса:
        # - Построение WHERE-клауз на основе параметров фильтрации
        # - Применение ORDER BY с sort_by и order
        # - Использование LIMIT и OFFSET для пагинации
        response_data = {
            "comparisons": [],
            "total_count": 0,
            "filters_applied": {
                "vacancy_id": vacancy_id,
                "created_by": created_by,
                "min_match_percentage": min_match_percentage,
                "max_match_percentage": max_match_percentage,
                "sort_by": sort_by,
                "order": order,
            },
        }

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=response_data,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing comparisons: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list comparisons: {str(e)}",
        ) from e


@router.get("/{comparison_id}", tags=["Comparisons"])
async def get_comparison(comparison_id: str) -> JSONResponse:
    """
    Получить конкретное представление сравнения по ID.

    Args:
        comparison_id: Уникальный идентификатор представления сравнения

    Returns:
        JSON-ответ с деталями представления сравнения

    Raises:
        HTTPException(404): Если представление сравнения не найдено
        HTTPException(500): Если запрос к базе данных не удался

    Examples:
        >>> import requests
        >>> response = requests.get(
        ...     "http://localhost:8000/api/comparisons/123e4567-e89b-12d3-a456-426614174000"
        ... )
        >>> response.json()
    """
    try:
        logger.info(f"Getting comparison: {comparison_id}")

        # Пока возвращаем ответ-заглушку
        # Интеграция с базой данных будет добавлена в следующей подзадаче, когда будет настроена async session
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "id": comparison_id,
                "vacancy_id": "vacancy-123",
                "resume_ids": ["resume1", "resume2"],
                "name": "Sample Comparison",
                "filters": None,
                "created_by": "user-123",
                "shared_with": None,
                "comparison_results": None,
                "created_at": "2024-01-25T00:00:00Z",
                "updated_at": "2024-01-25T00:00:00Z",
            },
        )

    except Exception as e:
        logger.error(f"Error getting comparison: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get comparison: {str(e)}",
        ) from e


@router.put("/{comparison_id}", tags=["Comparisons"])
async def update_comparison(
    comparison_id: str, request: ComparisonUpdate
) -> JSONResponse:
    """
    Обновить представление сравнения.

    Args:
        comparison_id: Уникальный идентификатор представления сравнения
        request: Запрос на обновление с полями для изменения

    Returns:
        JSON-ответ с обновлённым представлением сравнения

    Raises:
        HTTPException(404): Если представление сравнения не найдено
        HTTPException(422): Если валидация не прошла
        HTTPException(500): Если операция с базой данных не удалась

    Examples:
        >>> import requests
        >>> data = {"name": "Updated Comparison Name"}
        >>> response = requests.put(
        ...     "http://localhost:8000/api/comparisons/123",
        ...     json=data
        ... )
        >>> response.json()
    """
    try:
        logger.info(f"Updating comparison: {comparison_id}")

        # Пока возвращаем ответ-заглушку
        # Интеграция с базой данных будет добавлена в следующей подзадаче, когда будет настроена async session
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "id": comparison_id,
                "vacancy_id": "vacancy-123",
                "resume_ids": ["resume1", "resume2"],
                "name": request.name if request.name is not None else "Sample Comparison",
                "filters": request.filters,
                "created_by": "user-123",
                "shared_with": request.shared_with,
                "comparison_results": None,
                "created_at": "2024-01-25T00:00:00Z",
                "updated_at": "2024-01-25T00:00:00Z",
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating comparison: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update comparison: {str(e)}",
        ) from e


@router.delete("/{comparison_id}", tags=["Comparisons"])
async def delete_comparison(comparison_id: str) -> JSONResponse:
    """
    Удалить представление сравнения.

    Args:
        comparison_id: Уникальный идентификатор представления сравнения

    Returns:
        JSON-ответ, подтверждающий удаление

    Raises:
        HTTPException(404): Если представление сравнения не найдено
        HTTPException(500): Если операция с базой данных не удалась

    Examples:
        >>> import requests
        >>> response = requests.delete("http://localhost:8000/api/comparisons/123")
        >>> response.json()
        {"message": "Comparison deleted successfully"}
    """
    try:
        logger.info(f"Deleting comparison: {comparison_id}")

        # Пока возвращаем ответ-заглушку
        # Интеграция с базой данных будет добавлена в следующей подзадаче, когда будет настроена async session
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": f"Comparison {comparison_id} deleted successfully"},
        )

    except Exception as e:
        logger.error(f"Error deleting comparison: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete comparison: {str(e)}",
        ) from e


@router.get("/shared/{share_id}", tags=["Comparisons"])
async def get_shared_comparison(share_id: str) -> JSONResponse:
    """
    Получить общее представление сравнения по share ID.

    Этот эндпоинт позволяет получить доступ к общему представлению сравнения без аутентификации.
    Он разработан для совместного использования результатов сравнения с членами команды или внешними сторонами.

    Args:
        share_id: Уникальный идентификатор share для представления сравнения

    Returns:
        JSON-ответ с деталями представления сравнения

    Raises:
        HTTPException(404): Если общее представление сравнения не найдено
        HTTPException(500): Если запрос к базе данных не удался

    Examples:
        >>> import requests
        >>> response = requests.get(
        ...     "http://localhost:8000/api/comparisons/shared/abc123def456"
        ... )
        >>> response.json()
        {
            "id": "comp-123",
            "vacancy_id": "vacancy-123",
            "resume_ids": ["resume1", "resume2", "resume3"],
            "name": "Senior Developer Candidates",
            "comparison_results": [...],
            "created_at": "2024-01-25T00:00:00Z",
            "share_id": "abc123def456"
        }
    """
    try:
        logger.info(f"Getting shared comparison: {share_id}")

        # Пока возвращаем ответ-заглушку
        # Интеграция с базой данных будет добавлена в следующей подзадаче, когда будет настроена async session
        # При интеграции это будет:
        # 1. Запрос к таблице resume_comparisons по share_id
        # 2. Проверка, что сравнение помечено как общее
        # 3. Возврат данных сравнения без требования аутентификации
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "id": "comp-123",
                "vacancy_id": "vacancy-123",
                "resume_ids": ["resume1", "resume2", "resume3"],
                "name": "Shared Comparison View",
                "filters": None,
                "created_by": "user-123",
                "shared_with": None,
                "comparison_results": None,
                "created_at": "2024-01-25T00:00:00Z",
                "updated_at": "2024-01-25T00:00:00Z",
                "share_id": share_id,
            },
        )

    except Exception as e:
        logger.error(f"Error getting shared comparison: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get shared comparison: {str(e)}",
        ) from e


class CompareMultipleRequest(BaseModel):
    """Модель запроса для сравнения нескольких резюме."""

    vacancy_id: str = Field(..., description="ID вакансии для сравнения")
    resume_ids: List[str] = Field(
        ..., description="Список ID резюме для сравнения (2-5 резюме)", min_length=2, max_length=5
    )
    vacancy_data: Optional[Dict[str, Any]] = Field(
        None,
        description="Опциональные данные вакансии (title, required_skills, min_experience_months). "
        "Если не предоставлены, будут получены из хранилища вакансий.",
    )


@router.post("/compare-multiple", tags=["Comparisons"])
async def compare_multiple_endpoint(request: CompareMultipleRequest) -> JSONResponse:
    """
    Сравнить несколько резюме с вакансией.

    Этот эндпоинт выполняет интеллектуальное сопоставление навыков каждого резюме
    с требованиями вакансии, с поддержкой синонимов и автоматическим ранжированием
    по проценту совпадения.

    Args:
        request: Запрос, содержащий vacancy_id и список ID резюме

    Returns:
        JSON-ответ с результатами сравнения, ранжированными по проценту совпадения

    Raises:
        HTTPException(422): Если валидация не прошла
        HTTPException(404): Если какой-либо файл резюме не найден
        HTTPException(500): Если обработка сравнения не удалась

    Examples:
        >>> import requests
        >>> data = {
        ...     "vacancy_id": "vacancy-123",
        ...     "resume_ids": ["resume1", "resume2", "resume3"],
        ...     "vacancy_data": {
        ...         "title": "Senior Java Developer",
        ...         "required_skills": ["Java", "Spring", "SQL"],
        ...         "min_experience_months": 60
        ...     }
        ... }
        >>> response = requests.post(
        ...     "http://localhost:8000/api/comparisons/compare-multiple",
        ...     json=data
        ... )
        >>> response.json()
        {
            "vacancy_id": "vacancy-123",
            "vacancy_title": "Senior Java Developer",
            "comparison_results": [
                {
                    "resume_id": "resume2",
                    "match_percentage": 85.5,
                    "rank": 1,
                    "matched_skills": [...],
                    "missing_skills": [...],
                    "experience_verification": [...]
                },
                {
                    "resume_id": "resume1",
                    "match_percentage": 72.3,
                    "rank": 2,
                    ...
                },
                {
                    "resume_id": "resume3",
                    "match_percentage": 65.0,
                    "rank": 3,
                    ...
                }
            ],
            "total_resumes": 3,
            "processing_time_ms": 1234.56
        }
    """
    try:
        logger.info(
            f"Compare multiple endpoint called for vacancy {request.vacancy_id} "
            f"with {len(request.resume_ids)} resumes"
        )

        # Если vacancy_data не предоставлены, используем значения по умолчанию или получаем из хранилища
        vacancy_data = request.vacancy_data or {
            "title": f"Vacancy {request.vacancy_id}",
            "required_skills": [],
            "min_experience_months": 0,
        }

        # Вызов функции сравнения
        raw_results = compare_multiple_resumes(
            resume_ids=request.resume_ids,
            vacancy_data=vacancy_data,
        )

        # Преобразование результатов для соответствия интерфейсу ComparisonMatrixData фронтенда
        # Извлечение всех уникальных навыков из всех резюме
        all_skills = set()
        for result in raw_results.get("comparison_results", []):
            if "error" not in result:
                # Extract from required_skills_match
                for skill_match in result.get("required_skills_match", []):
                    all_skills.add(skill_match.get("skill", ""))
                # Extract from additional_skills_match
                for skill_match in result.get("additional_skills_match", []):
                    all_skills.add(skill_match.get("skill", ""))

        # Преобразование каждого результата сравнения для соответствия интерфейсу ResumeComparisonResult фронтенда
        comparisons = []
        for result in raw_results.get("comparison_results", []):
            if "error" in result:
                # Обработка случая ошибки - всё равно включаем в результаты, но с минимальными данными
                comparisons.append({
                    "resume_id": result.get("resume_id", ""),
                    "match_percentage": 0.0,
                    "matched_skills": [],
                    "missing_skills": [],
                    "overall_match": False,
                })
            else:
                # Преобразование совпавших навыков в формат фронтенда
                matched_skills = []
                for skill_match in result.get("required_skills_match", []):
                    matched_skills.append({
                        "skill": skill_match.get("skill", ""),
                        "matched": skill_match.get("matched", False),
                        "highlight": "green" if skill_match.get("matched", False) else "red",
                    })

                # Добавление дополнительных совпавших навыков
                for skill_match in result.get("additional_skills_match", []):
                    if skill_match.get("matched", False):
                        matched_skills.append({
                            "skill": skill_match.get("skill", ""),
                            "matched": True,
                            "highlight": "green",
                        })

                # Определение отсутствующих навыков (обязательные навыки, не совпавшие)
                missing_skills = []
                for skill_match in result.get("required_skills_match", []):
                    if not skill_match.get("matched", False):
                        missing_skills.append({
                            "skill": skill_match.get("skill", ""),
                            "matched": False,
                            "highlight": "red",
                        })

                # Формирование результата сравнения
                comparison = {
                    "resume_id": result.get("resume_id", ""),
                    "match_percentage": result.get("match_percentage", 0.0),
                    "matched_skills": matched_skills,
                    "missing_skills": missing_skills,
                    "overall_match": result.get("match_percentage", 0) > 0,
                }

                # Добавление проверки опыта, если доступна
                exp_verification = result.get("experience_verification")
                if exp_verification:
                    comparison["experience_verification"] = exp_verification

                comparisons.append(comparison)

        # Возврат преобразованного ответа, соответствующего интерфейсу ComparisonMatrixData фронтенда
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "vacancy_id": request.vacancy_id,
                "comparisons": comparisons,
                "all_unique_skills": sorted(list(all_skills)),
                "processing_time": raw_results.get("processing_time_ms", 0),
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in compare-multiple endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compare resumes: {str(e)}",
        ) from e
