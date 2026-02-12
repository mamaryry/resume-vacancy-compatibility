"""
Модуль сохранения анализа для сохранения результатов анализа резюме в базу данных.

Предоставляет функции для сохранения, получения и удаления анализов резюме,
а также расчёта оценок качества.
"""
from typing import Optional, Any, Dict, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from models.resume_analysis import ResumeAnalysis


async def save_resume_analysis(
    db: AsyncSession,
    resume_id: UUID,
    raw_text: str,
    language: str,
    skills: List[str],
    keywords: List[Dict[str, Any]],
    entities: Dict[str, Any],
    quality_score: Optional[int] = None,
    processing_time_seconds: Optional[float] = None,
    analyzer_version: str = "1.0.0",
    grammar_issues: Optional[List[Dict[str, Any]]] = None,
    warnings: Optional[List[Dict[str, Any]]] = None,
    total_experience_months: Optional[int] = None,
    education: Optional[List[Dict[str, Any]]] = None,
    contact_info: Optional[Dict[str, Any]] = None,
) -> ResumeAnalysis:
    """
    Сохранить или обновить анализ резюме в базе данных.

    Args:
        db: Сессия базы данных
        resume_id: UUID резюме
        raw_text: Извлеченный текст из резюме
        language: Обнаруженный код языка
        skills: Список извлеченных навыков
        keywords: Список ключевых слов с оценками
        entities: Словарь именованных сущностей
        quality_score: Общая оценка качества (0-100)
        processing_time_seconds: Время, затраченное на анализ
        analyzer_version: Версия анализатора
        grammar_issues: Список найденных грамматических проблем
        warnings: Список обнаруженных предупреждений
        total_experience_months: Общий стаж работы в месяцах
        education: Извлеченная информация об образовании
        contact_info: Извлеченная контактная информация

    Returns:
        ResumeAnalysis: Созданная или обновленная запись анализа
    """
    # Проверка существования анализа
    existing = await db.execute(
        select(ResumeAnalysis).where(ResumeAnalysis.resume_id == resume_id)
    )
    existing_analysis = existing.scalar_one_or_none()

    if existing_analysis:
        # Обновление существующего
        existing_analysis.raw_text = raw_text
        existing_analysis.language = language
        existing_analysis.skills = skills
        existing_analysis.keywords = keywords
        existing_analysis.entities = entities
        existing_analysis.quality_score = quality_score
        existing_analysis.processing_time_seconds = processing_time_seconds
        existing_analysis.analyzer_version = analyzer_version
        existing_analysis.grammar_issues = grammar_issues
        existing_analysis.warnings = warnings
        existing_analysis.total_experience_months = total_experience_months
        existing_analysis.education = education
        existing_analysis.contact_info = contact_info
        await db.flush()
        return existing_analysis

    # Создание нового
    analysis = ResumeAnalysis(
        resume_id=resume_id,
        raw_text=raw_text,
        language=language,
        skills=skills,
        keywords=keywords,
        entities=entities,
        quality_score=quality_score,
        processing_time_seconds=processing_time_seconds,
        analyzer_version=analyzer_version,
        grammar_issues=grammar_issues,
        warnings=warnings,
        total_experience_months=total_experience_months,
        education=education,
        contact_info=contact_info,
    )
    db.add(analysis)
    await db.flush()
    return analysis


async def get_resume_analysis(
    db: AsyncSession,
    resume_id: UUID,
) -> Optional[ResumeAnalysis]:
    """
    Получить анализ резюме из базы данных.

    Args:
        db: Сессия базы данных
        resume_id: UUID резюме

    Returns:
        ResumeAnalysis или None, если не найдено
    """
    result = await db.execute(
        select(ResumeAnalysis).where(ResumeAnalysis.resume_id == resume_id)
    )
    return result.scalar_one_or_none()


async def delete_resume_analysis(
    db: AsyncSession,
    resume_id: UUID,
) -> bool:
    """
    Удалить анализ резюме из базы данных.

    Args:
        db: Сессия базы данных
        resume_id: UUID резюме

    Returns:
        bool: True, если удалено, False, если не найдено
    """
    result = await db.execute(
        delete(ResumeAnalysis).where(ResumeAnalysis.resume_id == resume_id)
    )
    await db.flush()
    return result.rowcount > 0


def calculate_quality_score(
    grammar_issues: Optional[List[Dict[str, Any]]] = None,
    warnings: Optional[List[Dict[str, Any]]] = None,
    has_contact_info: bool = True,
    has_experience: bool = True,
    has_education: bool = True,
    text_length: int = 0,
) -> int:
    """
    Рассчитать оценку качества резюме на основе различных факторов.

    Args:
        grammar_issues: Список грамматических/орфографических проблем
        warnings: Список обнаруженных предупреждений
        has_contact_info: Наличие контактной информации
        has_experience: Наличие опыта работы
        has_education: Наличие образования
        text_length: Длина текста резюме

    Returns:
        int: Оценка качества от 0 до 100
    """
    score = 100

    # Штраф за грамматические проблемы
    if grammar_issues:
        score -= min(len(grammar_issues) * 2, 20)

    # Штраф за предупреждения
    if warnings:
        score -= min(len(warnings) * 5, 30)

    # Штраф за отсутствующие секции
    if not has_contact_info:
        score -= 15
    if not has_experience:
        score -= 20
    if not has_education:
        score -= 10

    # Штраф за короткие резюме
    if text_length < 500:
        score -= 20
    elif text_length < 1000:
        score -= 10

    # Убедимся, что оценка в допустимом диапазоне
    return max(0, min(score, 100))
