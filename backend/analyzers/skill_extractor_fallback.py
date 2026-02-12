"""
Резервный извлекатель навыков с автоматическим выбором метода.

Этот модуль предоставляет унифицированный интерфейс, который автоматически
пытается использовать различные методы извлечения в порядке приоритета,
переходя к альтернативам при сбое одного метода.
"""
import logging
from typing import Dict, List, Optional, Union

logger = logging.getLogger(__name__)


def extract_skills_with_fallback(
    text: str,
    *,
    top_n: int = 10,
    candidate_skills: Optional[List[str]] = None,
    preferred_method: str = "auto",
) -> Dict[str, Optional[Union[List[str], List[tuple], str]]]:
    """
    Извлечь навыки из текста с автоматическим резервным переходом.

    Эта функция пытается использовать несколько методов извлечения по порядку:
    1. Hugging Face NER (если transformers доступен)
    2. KeyBERT (если keybert доступен)
    3. SpaCy NER (если доступен)
    4. Классификация zero-shot (если предоставлены candidate_skills)

    Args:
        text: Текст для извлечения навыков
        top_n: Максимальное количество возвращаемых навыков
        candidate_skills: Необязательный список навыков-кандидатов для zero-shot
        preferred_method: Предпочитаемый метод извлечения:
            - 'auto': Попробовать все методы автоматически (по умолчанию)
            - 'ner': Использовать только NER-модели
            - 'keybert': Использовать только KeyBERT
            - 'zero-shot': Использовать только zero-shot (требует candidate_skills)
            - 'hybrid': Попробовать сначала NER, затем KeyBERT

    Returns:
        Словарь с результатами извлечения, включая:
            - skills: Список извлечённых навыков
            - skills_with_scores: Список кортежей (skill, score)
            - count: Количество извлечённых навыков
            - method: Метод, который успешно сработал
            - model: Использованное название модели
            - error: Сообщение об ошибке, если все методы не удались

    Examples:
        >>> # Автоматический выбор метода
        >>> result = extract_skills_with_fallback(resume_text, top_n=10)

        >>> # С предварительно определённой таксономией навыков
        >>> taxonomy = ["Python", "Java", "JavaScript", "Django", "React"]
        >>> result = extract_skills_with_fallback(
        ...     resume_text,
        ...     candidate_skills=taxonomy,
        ...     top_n=5
        ... )
    """
    if not text or not isinstance(text) or len(text.strip()) < 10:
        return {
            "skills": None,
            "skills_with_scores": None,
            "count": 0,
            "method": "none",
            "model": "none",
            "error": "Текст должен быть непустой строкой минимум из 10 символов",
        }

    # Отслеживать попытанные методы
    attempts = []

    # Метод 1: Попробовать Hugging Face NER (рекомендуется, без зависимости от KeyBERT)
    if preferred_method in ["auto", "ner", "hybrid"]:
        try:
            from .hf_skill_extractor import extract_skills_ner

            logger.info("Попытка извлечения Hugging Face NER")
            result = extract_skills_ner(text, top_n=top_n)

            if not result.get("error") and result.get("skills"):
                logger.info(f"✓ Hugging Face NER успешно: {result['count']} навыков")
                return {
                    **result,
                    "method": "huggingface_ner",
                }
            else:
                attempts.append(("huggingface_ner", result.get("error", "Навыки не найдены")))
                logger.warning(f"Hugging Face NER не удалось: {result.get('error')}")
        except ImportError:
            attempts.append(("huggingface_ner", "Transformers не установлен"))
            logger.info("Hugging Face transformers недоступен")
        except Exception as e:
            attempts.append(("huggingface_ner", str(e)))
            logger.warning(f"Ошибка Hugging Face NER: {e}")

    # Метод 2: Попробовать KeyBERT (оригинальный метод, могут быть проблемы с Keras)
    if preferred_method in ["auto", "keybert", "hybrid"]:
        try:
            from .keyword_extractor import extract_top_skills

            logger.info("Попытка извлечения KeyBERT")
            result = extract_top_skills(text, top_n=top_n)

            if not result.get("error") and result.get("skills"):
                logger.info(f"✓ KeyBERT успешно: {result['count']} навыков")
                return {
                    **result,
                    "method": "keybert",
                }
            else:
                attempts.append(("keybert", result.get("error", "Навыки не найдены")))
                logger.warning(f"KeyBERT не удалось: {result.get('error')}")
        except ImportError:
            attempts.append(("keybert", "KeyBERT не установлен"))
            logger.info("KeyBERT недоступен")
        except Exception as e:
            attempts.append(("keybert", str(e)))
            logger.warning(f"Ошибка KeyBERT: {e}")

    # Метод 3: Попробовать Hugging Face zero-shot (если предоставлены candidate_skills)
    if candidate_skills and preferred_method in ["auto", "zero-shot", "hybrid"]:
        try:
            from .hf_skill_extractor import extract_skills_zero_shot

            logger.info("Попытка классификации zero-shot")
            result = extract_skills_zero_shot(text, candidate_skills, top_n=top_n)

            if not result.get("error") and result.get("skills"):
                logger.info(f"✓ Zero-shot успешно: {result['count']} навыков")
                return {
                    **result,
                    "method": "zero_shot",
                }
            else:
                attempts.append(("zero_shot", result.get("error", "Навыки не найдены")))
                logger.warning(f"Zero-shot не удалось: {result.get('error')}")
        except ImportError:
            attempts.append(("zero_shot", "Transformers не установлен"))
            logger.info("Zero-shot недоступен")
        except Exception as e:
            attempts.append(("zero_shot", str(e)))
            logger.warning(f"Ошибка Zero-shot: {e}")

    # Метод 4: Попробовать SpaCy NER (базовый резервный вариант)
    if preferred_method in ["auto", "hybrid"]:
        try:
            from .ner_extractor import extract_entities

            logger.info("Попытка извлечения SpaCy NER")
            result = extract_entities(text)

            # Фильтровать похожие на навыки сущности
            if result and not result.get("error"):
                entities = result.get("entities", {})
                skills = []

                # Извлечь организации и продукты как потенциальные навыки
                for org in entities.get("organizations", [])[:top_n]:
                    skills.append((org, 0.7))  # Оценка по умолчанию
                for product in entities.get("products", [])[: top_n // 2]:
                    skills.append((product, 0.6))

                if skills:
                    skills = skills[:top_n]
                    logger.info(f"✓ SpaCy NER успешно: {len(skills)} навыков")
                    return {
                        "skills": [s for s, _ in skills],
                        "skills_with_scores": skills,
                        "count": len(skills),
                        "method": "spacy_ner",
                        "model": "spacy",
                        "error": None,
                    }
                else:
                    attempts.append(("spacy_ner", "Сущностей, похожих на навыки, не найдено"))
            else:
                attempts.append(("spacy_ner", result.get("error", "Неизвестная ошибка")))
        except Exception as e:
            attempts.append(("spacy_ner", str(e)))
            logger.warning(f"Ошибка SpaCy NER: {e}")

    # Все методы не удались
    error_msg = f"Все методы извлечения не удались. Попытки: {attempts}"
    logger.error(error_msg)

    return {
        "skills": None,
        "skills_with_scores": None,
        "count": 0,
        "method": "none",
        "model": "none",
        "error": error_msg,
        "attempts": attempts,
    }


def extract_top_skills_auto(
    text: str,
    top_n: int = 10,
    candidate_skills: Optional[List[str]] = None,
) -> Dict[str, Optional[Union[List[str], List[tuple], str]]]:
    """
    Convenience function for automatic skill extraction.

    This is the recommended function for most use cases. It automatically
    tries different extraction methods and returns the best result.

    Args:
        text: Text to extract skills from
        top_n: Maximum number of skills to return
        candidate_skills: Optional predefined skill taxonomy

    Returns:
        Dictionary with extraction results

    Examples:
        >>> from analyzers import extract_top_skills_auto
        >>>
        >>> # Simple usage
        >>> result = extract_top_skills_auto(resume_text, top_n=10)
        >>> print(result["skills"])
        ['Python', 'Django', 'PostgreSQL']

        >>> # With predefined skills
        >>> taxonomy = ["Python", "Java", "JavaScript", "React"]
        >>> result = extract_top_skills_auto(resume_text, candidate_skills=taxonomy)
        >>> print(f"Method used: {result['method']}")
    """
    return extract_skills_with_fallback(
        text,
        top_n=top_n,
        candidate_skills=candidate_skills,
        preferred_method="auto",
    )
