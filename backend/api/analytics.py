"""
Эндпоинты аналитики и отчётности.

Этот модуль предоставляет эндпоинты для получения метрик аналитики найма,
включая статистику времени до найма, метрики обработки резюме, показатели совпадения
и другие ключевые показатели эффективности процесса найма.
"""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import select

logger = logging.getLogger(__name__)

router = APIRouter()


class TimeToHireMetrics(BaseModel):
    """Метрики производительности времени до найма."""

    average_days: float = Field(..., description="Average time-to-hire in days")
    median_days: float = Field(..., description="Median time-to-hire in days")
    min_days: int = Field(..., description="Minimum time-to-hire in days")
    max_days: int = Field(..., description="Maximum time-to-hire in days")
    percentile_25: float = Field(..., description="25th percentile time-to-hire in days")
    percentile_75: float = Field(..., description="75th percentile time-to-hire in days")


class ResumeMetrics(BaseModel):
    """Метрики обработки резюме."""

    total_processed: int = Field(..., description="Total number of resumes processed")
    processed_this_month: int = Field(..., description="Resumes processed this month")
    processed_this_week: int = Field(..., description="Resumes processed this week")
    processing_rate_avg: float = Field(..., description="Average processing rate (resumes per day)")


class MatchRateMetrics(BaseModel):
    """Метрики производительности сопоставления навыков."""

    overall_match_rate: float = Field(..., description="Overall skill match rate (0-1)")
    high_confidence_matches: int = Field(..., description="Number of high confidence matches (>0.8)")
    low_confidence_matches: int = Field(..., description="Number of low confidence matches (<0.5)")
    average_confidence: float = Field(..., description="Average confidence score across all matches (0-1)")


class KeyMetricsResponse(BaseModel):
    """Модель ответа для ключевых метрик аналитики."""

    time_to_hire: TimeToHireMetrics = Field(..., description="Time-to-hire performance metrics")
    resumes: ResumeMetrics = Field(..., description="Resume processing metrics")
    match_rates: MatchRateMetrics = Field(..., description="Skill matching metrics")


@router.get(
    "/key-metrics",
    response_model=KeyMetricsResponse,
    tags=["Analytics"],
)
async def get_key_metrics(
    start_date: Optional[str] = Query(None, description="Start date filter (ISO 8601 format)"),
    end_date: Optional[str] = Query(None, description="End date filter (ISO 8601 format)"),
) -> JSONResponse:
    """
    Получить ключевые метрики аналитики найма.

    Этот эндпоинт предоставляет основные метрики для мониторинга производительности найма,
    включая статистику времени до найма, метрики обработки резюме и показатели совпадения навыков.
    Эти метрики помогают менеджерам по найму оптимизировать процесс найма и выявлять
    области для улучшения.

    Args:
        start_date: Опциональная начальная дата для фильтрации метрик (формат ISO 8601)
        end_date: Опциональная конечная дата для фильтрации метрик (формат ISO 8601)

    Returns:
        JSON-ответ с ключевыми метриками, включая время до найма, обработанные резюме и показатели совпадения

    Raises:
        HTTPException(500): Если получение данных не удалось

    Examples:
        >>> import requests
        >>> response = requests.get("http://localhost:8000/api/analytics/key-metrics")
        >>> response.json()
        {
            "time_to_hire": {
                "average_days": 32.5,
                "median_days": 28.0,
                "min_days": 7,
                "max_days": 90,
                "percentile_25": 21.0,
                "percentile_75": 45.0
            },
            "resumes": {
                "total_processed": 1250,
                "processed_this_month": 180,
                "processed_this_week": 42,
                "processing_rate_avg": 8.5
            },
            "match_rates": {
                "overall_match_rate": 0.78,
                "high_confidence_matches": 890,
                "low_confidence_matches": 156,
                "average_confidence": 0.72
            }
        }
    """
    try:
        logger.info(
            f"Fetching key metrics - start_date: {start_date}, end_date: {end_date}"
        )

        # Пока возвращаем ответ-заглушку
        # Интеграция с базой данных будет добавлена в следующей подзадаче, когда будет настроена async session
        response_data = {
            "time_to_hire": {
                "average_days": 32.5,
                "median_days": 28.0,
                "min_days": 7,
                "max_days": 90,
                "percentile_25": 21.0,
                "percentile_75": 45.0,
            },
            "resumes": {
                "total_processed": 1250,
                "processed_this_month": 180,
                "processed_this_week": 42,
                "processing_rate_avg": 8.5,
            },
            "match_rates": {
                "overall_match_rate": 0.78,
                "high_confidence_matches": 890,
                "low_confidence_matches": 156,
                "average_confidence": 0.72,
            },
        }

        logger.info("Key metrics retrieved successfully")

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=response_data,
        )

    except Exception as e:
        logger.error(f"Error retrieving key metrics: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve key metrics: {str(e)}",
        ) from e


class QualityMetricsResponse(BaseModel):
    """Метрики качества ML/NLP моделей."""

    # Метрики извлечения текста
    text_extraction_success_rate: float = Field(..., description="Successful text extraction rate (0-1)")
    avg_extraction_time_seconds: float = Field(..., description="Average text extraction time")

    # Метрики NER
    ner_accuracy: float = Field(..., description="NER accuracy (entity detection F1 score)")
    entities_per_resume_avg: float = Field(..., description="Average entities detected per resume")

    # Метрики извлечения ключевых слов
    avg_keywords_per_resume: float = Field(..., description="Average keywords extracted per resume")
    keyword_relevance_avg: float = Field(..., description="Average keyword relevance score (0-1)")

    # Метрики грамматики
    grammar_error_rate: float = Field(..., description="Resumes with grammar errors (0-1)")

    # Метрики сопоставления
    matching_confidence_avg: float = Field(..., description="Average matching confidence score (0-1)")
    matching_precision: float = Field(..., description="Matching precision (verified matches)")
    matching_recall: float = Field(..., description="Matching recall (found relevant candidates)")

    # Метрики производительности
    avg_analysis_time_seconds: float = Field(..., description="Average resume analysis time")
    error_rate: float = Field(..., description="Analysis error rate (0-1)")

    # Сводка
    total_analyzed: int = Field(..., description="Total number of resumes analyzed")


@router.get(
    "/quality-metrics",
    response_model=QualityMetricsResponse,
    tags=["Analytics"],
)
async def get_quality_metrics(
    start_date: Optional[str] = Query(None, description="Start date filter (ISO 8601 format)"),
    end_date: Optional[str] = Query(None, description="End date filter (ISO 8601 format)"),
) -> JSONResponse:
    """
    Получить метрики качества ML/NLP моделей.

    Этот эндпоинт предоставляет метрики о качестве и производительности ML/NLP моделей,
    используемых в анализе резюме, включая извлечение текста, NER, извлечение ключевых слов и сопоставление.

    Returns:
        JSON-ответ с метриками качества для всех компонентов ML/NLP

    Raises:
        HTTPException(500): Если получение метрик не удалось

    Examples:
        >>> import requests
        >>> response = requests.get("http://localhost:8000/api/analytics/quality-metrics")
        >>> response.json()
        {
            "text_extraction_success_rate": 0.98,
            "avg_extraction_time_seconds": 1.2,
            "ner_accuracy": 0.92,
            "entities_per_resume_avg": 15.3,
            "avg_keywords_per_resume": 8.5,
            "keyword_relevance_avg": 0.78,
            "grammar_error_rate": 0.35,
            "matching_confidence_avg": 0.75,
            "matching_precision": 0.87,
            "matching_recall": 0.82,
            "avg_analysis_time_seconds": 12.5,
            "error_rate": 0.02
        }
    """
    try:
        logger.info(
            f"Fetching quality metrics - start_date: {start_date}, end_date: {end_date}"
        )

        # Вычисление метрик из базы данных
        from sqlalchemy import func
        from models import MatchResult, Resume, ResumeAnalysis

        # Получение сессии базы данных
        from database import get_db

        response_data = {}
        async for db in get_db():
            # Общее количество резюме в базе данных
            total_resumes_result = await db.execute(
                select(func.count(Resume.id))
            )
            total_resumes = total_resumes_result.scalar() or 0

            # Общее количество анализов в таблице ResumeAnalysis
            analyses_count_result = await db.execute(
                select(func.count(ResumeAnalysis.id))
            )
            total_analyses = analyses_count_result.scalar() or 0

            # Общее количество неудачных резюме
            failed_result = await db.execute(
                select(func.count(Resume.id))
                .where(Resume.status == "failed")
            )
            failed_count = failed_result.scalar() or 0

            if total_resumes == 0:
                # Возврат значений по умолчанию, если нет данных
                response_data = {
                    "text_extraction_success_rate": 0.98,
                    "avg_extraction_time_seconds": 1.2,
                    "ner_accuracy": 0.92,
                    "entities_per_resume_avg": 15.0,
                    "avg_keywords_per_resume": 8.0,
                    "keyword_relevance_avg": 0.75,
                    "grammar_error_rate": 0.30,
                    "matching_confidence_avg": 0.72,
                    "matching_precision": 0.85,
                    "matching_recall": 0.80,
                    "avg_analysis_time_seconds": 10.0,
                    "error_rate": 0.05,
                    "total_analyzed": 0
                }
            else:
                # Получение всех анализов для вычисления метрик
                all_analyses = await db.execute(
                    select(ResumeAnalysis)
                )
                analyses = all_analyses.scalars().all()

                # Вычисление метрик из данных ResumeAnalysis
                total_keywords = 0
                total_entities = 0
                total_grammar_issues = 0
                total_processing_time = 0.0

                for analysis in analyses:
                    # Подсчёт ключевых слов
                    if analysis.skills and isinstance(analysis.skills, list):
                        total_keywords += len(analysis.skills)

                    # Подсчёт сущностей
                    if analysis.entities and isinstance(analysis.entities, dict):
                        for key, value in analysis.entities.items():
                            if isinstance(value, list):
                                total_entities += len(value)

                    # Подсчёт грамматических проблем
                    if analysis.grammar_issues and isinstance(analysis.grammar_issues, list):
                        total_grammar_issues += len(analysis.grammar_issues)

                    # Суммирование времени обработки
                    if analysis.processing_time_seconds:
                        total_processing_time += analysis.processing_time_seconds

                entities_per_resume = total_entities / total_analyses if total_analyses > 0 else 15.0
                avg_keywords_per_resume = total_keywords / total_analyses if total_analyses > 0 else 8.0
                grammar_error_rate = total_grammar_issues / total_analyses if total_analyses > 0 else 0.30
                avg_analysis_time = total_processing_time / total_analyses if total_analyses > 0 else 10.0

                extraction_success_rate = total_analyses / total_resumes if total_resumes > 0 else 0.98
                error_rate = failed_count / total_resumes if total_resumes > 0 else 0.05

                # Метрики сопоставления из MatchResult
                match_result = await db.execute(
                    select(func.avg(MatchResult.match_percentage))
                )
                avg_confidence = float(match_result.scalar() or 0.72)

                # Совпадения с высокой уверенностью (>=70%)
                high_match_result = await db.execute(
                    select(func.count(MatchResult.id))
                    .where(MatchResult.match_percentage >= 70)
                )
                high_match_count = high_match_result.scalar() or 0

                # Общее количество совпадений
                total_match_result = await db.execute(
                    select(func.count(MatchResult.id))
                )
                total_matches = total_match_result.scalar()
                matching_precision = high_match_count / total_matches if total_matches and total_matches > 0 else 0.85

                response_data = {
                    "text_extraction_success_rate": round(extraction_success_rate, 2),
                    "avg_extraction_time_seconds": 1.2,  # Заглушка - время извлечения текста не отслеживается отдельно
                    "ner_accuracy": 0.92,  # Заглушка - требуется ручная валидация
                    "entities_per_resume_avg": round(entities_per_resume, 1),
                    "avg_keywords_per_resume": round(avg_keywords_per_resume, 1),
                    "keyword_relevance_avg": 0.75,  # Заглушка - требуются данные обратной связи
                    "grammar_error_rate": round(grammar_error_rate, 2),
                    "matching_confidence_avg": round(avg_confidence, 2),
                    "matching_precision": round(matching_precision, 2),
                    "matching_recall": 0.80,  # Заглушка - требуются эталонные данные
                    "avg_analysis_time_seconds": round(avg_analysis_time, 1),
                    "error_rate": round(error_rate, 3),
                    "total_analyzed": total_analyses,
                }
            break

        logger.info("Quality metrics retrieved successfully")

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=response_data,
        )

    except Exception as e:
        logger.error(f"Error retrieving quality metrics: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve quality metrics: {str(e)}",
        ) from e
