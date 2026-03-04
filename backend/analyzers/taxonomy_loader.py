"""
Динамический загрузчик таксономии, объединяющий статические синонимы, отраслевые таксономии
и пользовательские синонимы организации.

Этот модуль предоставляет унифицированный интерфейс для загрузки и объединения таксономий
навыков из нескольких источников: статического JSON-файла, отраслевых таксономий базы данных
и пользовательских синонимов организации.

Загрузчик реализует систему приоритетов:
1. Пользовательские синонимы организации (наивысший приоритет)
2. Отраслевые таксономии
3. Статические синонимы из JSON-файла (резервный вариант)

Это обеспечивает преимущество пользовательских настроек организации, за которыми следуют
отраслевой контекст, а статические синонимы служат базой знаний.
"""
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from models.skill_taxonomy import SkillTaxonomy
from models.custom_synonyms import CustomSynonym

logger = logging.getLogger(__name__)

# Путь к статическому файлу синонимов навыков
SYNONYMS_FILE = Path(__file__).parent.parent / "models" / "skill_synonyms.json"

# Кэш загруженных таксономий
_static_synonyms_cache: Optional[Dict[str, List[str]]] = None
_taxonomy_cache: Dict[str, Dict[str, List[str]]] = {}


class TaxonomyLoader:
    """
    Динамический загрузчик таксономии, объединяющий несколько источников синонимов.

    Этот класс предоставляет методы для загрузки и объединения таксономий навыков из
    статических файлов, моделей базы данных и пользовательских переопределений организации.

    Attributes:
        use_cache: Кэшировать ли загруженные таксономии для производительности

    Example:
        >>> loader = TaxonomyLoader()
        >>> taxonomies = loader.load_for_organization('org123', 'tech')
        >>> print(taxonomies['React'])
        ['React', 'ReactJS', 'React.js', 'CustomReactName']
    """

    def __init__(self, use_cache: bool = True) -> None:
        """
        Инициализировать загрузчик таксономии.

        Args:
            use_cache: Кэшировать ли загруженные таксономии (по умолчанию: True)
        """
        self.use_cache = use_cache

    def load_static_synonyms(self) -> Dict[str, List[str]]:
        """
        Загрузить статические синонимы навыков из JSON-файла.

        Этот метод загружает базовые синонимы навыков из статического JSON-файла,
        который служит базой знаний по умолчанию для сопоставления навыков.

        Returns:
            Словарь, сопоставляющий канонические названия навыков со списками синонимов

        Example:
            >>> loader = TaxonomyLoader()
            >>> synonyms = loader.load_static_synonyms()
            >>> synonyms["PostgreSQL"]
            ["PostgreSQL", "Postgres", "Postgres SQL"]
        """
        global _static_synonyms_cache

        if self.use_cache and _static_synonyms_cache is not None:
            return _static_synonyms_cache

        try:
            with open(SYNONYMS_FILE, "r", encoding="utf-8") as f:
                synonyms_data = json.load(f)

            # Выравнять структуру категорий в один словарь
            # Вход: {"databases": {"SQL": ["SQL", "PostgreSQL", ...]}}
            # Выход: {"SQL": ["SQL", "PostgreSQL", ...]}
            flat_synonyms: Dict[str, List[str]] = {}

            for category in synonyms_data.values():
                if isinstance(category, dict):
                    for canonical_name, synonyms_list in category.items():
                        if isinstance(synonyms_list, list):
                            # Убедиться, что каноническое название есть в списке
                            all_synonyms = set(synonyms_list + [canonical_name])
                            flat_synonyms[canonical_name] = list(all_synonyms)

            if self.use_cache:
                _static_synonyms_cache = flat_synonyms

            logger.info(f"Загружено {len(flat_synonyms)} соответствий статических синонимов навыков")
            return flat_synonyms

        except FileNotFoundError:
            logger.warning(f"Файл статических синонимов навыков не найден: {SYNONYMS_FILE}")
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка разбора JSON статических синонимов навыков: {e}")
            return {}
        except Exception as e:
            logger.error(f"Ошибка загрузки статических синонимов навыков: {e}", exc_info=True)
            return {}

    def load_industry_taxonomies(
        self, industry: str, db_session: Optional[Any] = None
    ) -> Dict[str, List[str]]:
        """
        Load industry-specific skill taxonomies from the database.

        Queries the SkillTaxonomy model for all active taxonomy entries
        matching the specified industry.

        Args:
            industry: Industry sector (tech, healthcare, finance, etc.)
            db_session: Optional database session for querying

        Returns:
            Dictionary mapping skill names to their variants

        Example:
            >>> loader = TaxonomyLoader()
            >>> taxonomies = loader.load_industry_taxonomies('tech')
            >>> taxonomies['React']
            ['React', 'ReactJS', 'React.js', 'ReactJS']
        """
        # Check cache first
        cache_key = f"industry:{industry}"
        if self.use_cache and cache_key in _taxonomy_cache:
            return _taxonomy_cache[cache_key]

        taxonomies: Dict[str, List[str]] = {}

        # If no database session provided, return empty dict
        # (This allows the loader to work in non-database contexts)
        if db_session is None:
            logger.debug("No database session provided, skipping industry taxonomy load")
            return taxonomies

        try:
            # Query active taxonomies for this industry
            taxonomy_entries = (
                db_session.query(SkillTaxonomy)
                .filter(
                    SkillTaxonomy.industry == industry,
                    SkillTaxonomy.is_active == True,
                )
                .all()
            )

            # Build taxonomy dictionary
            for entry in taxonomy_entries:
                # Start with canonical name and variants from database
                variants = [entry.skill_name]
                if entry.variants:
                    variants.extend(entry.variants)

                # Add to taxonomies dict (deduplicate)
                taxonomies[entry.skill_name] = list(set(variants))

            if self.use_cache:
                _taxonomy_cache[cache_key] = taxonomies

            logger.info(
                f"Loaded {len(taxonomies)} industry taxonomies for industry: {industry}"
            )
            return taxonomies

        except Exception as e:
            logger.error(
                f"Error loading industry taxonomies for {industry}: {e}",
                exc_info=True,
            )
            return {}

    def load_custom_synonyms(
        self, organization_id: str, db_session: Optional[Any] = None
    ) -> Dict[str, List[str]]:
        """
        Load organization-specific custom synonyms from the database.

        Queries the CustomSynonym model for all active synonym mappings
        for the specified organization.

        Args:
            organization_id: Organization identifier
            db_session: Optional database session for querying

        Returns:
            Dictionary mapping canonical skill names to custom synonym lists

        Example:
            >>> loader = TaxonomyLoader()
            >>> synonyms = loader.load_custom_synonyms('org123')
            >>> synonyms['React']
            ['React', 'OurCustomReactName', 'ReactFramework']
        """
        # Check cache first
        cache_key = f"org:{organization_id}"
        if self.use_cache and cache_key in _taxonomy_cache:
            return _taxonomy_cache[cache_key]

        synonyms: Dict[str, List[str]] = {}

        # If no database session provided, return empty dict
        if db_session is None:
            logger.debug("No database session provided, skipping custom synonym load")
            return synonyms

        try:
            # Query active custom synonyms for this organization
            custom_entries = (
                db_session.query(CustomSynonym)
                .filter(
                    CustomSynonym.organization_id == organization_id,
                    CustomSynonym.is_active == True,
                )
                .all()
            )

            # Build synonyms dictionary
            for entry in custom_entries:
                # Start with canonical skill and custom synonyms
                all_synonyms = [entry.canonical_skill]
                if entry.custom_synonyms:
                    all_synonyms.extend(entry.custom_synonyms)

                # Add to synonyms dict (deduplicate)
                synonyms[entry.canonical_skill] = list(set(all_synonyms))

            if self.use_cache:
                _taxonomy_cache[cache_key] = synonyms

            logger.info(
                f"Loaded {len(synonyms)} custom synonym mappings for org: {organization_id}"
            )
            return synonyms

        except Exception as e:
            logger.error(
                f"Error loading custom synonyms for org {organization_id}: {e}",
                exc_info=True,
            )
            return {}

    def load_for_organization(
        self,
        organization_id: str,
        industry: str,
        db_session: Optional[Any] = None,
    ) -> Dict[str, List[str]]:
        """
        Загрузить объединённые таксономии для конкретной организации.

        Этот метод объединяет три источника в порядке приоритета:
        1. Пользовательские синонимы организации (наивысший приоритет - переопределяет все)
        2. Отраслевые таксономии (средний приоритет - переопределяет статические)
        3. Статические синонимы из JSON-файла (базовый резервный вариант)

        Это обеспечивает преимущество пользовательских настроек организации,
        сохраняя отраслевой контекст и базовые знания.

        Args:
            organization_id: Идентификатор организации
            industry: Отрасль (tech, healthcare, finance и т.д.)
            db_session: Необязательная сессия базы данных для запросов

        Returns:
            Объединённый словарь, сопоставляющий названия навыков с их списками синонимов

        Example:
            >>> loader = TaxonomyLoader()
            >>> taxonomies = loader.load_for_organization('org123', 'tech')
            >>> # Возвращает объединённые таксономии с приоритетом custom > industry > static
            >>> print(len(taxonomies))
            250
        """
        # Сначала проверить кэш
        cache_key = f"merged:{organization_id}:{industry}"
        if self.use_cache and cache_key in _taxonomy_cache:
            return _taxonomy_cache[cache_key]

        logger.info(
            f"Загрузка объединённых таксономий для org={organization_id}, industry={industry}"
        )

        # Шаг 1: Загрузить статические синонимы (базовый уровень)
        static_synonyms = self.load_static_synonyms()
        logger.debug(f"Загружено {len(static_synonyms)} статических синонимов")

        # Шаг 2: Загрузить отраслевые таксономии (переопределяют статические)
        industry_taxonomies = self.load_industry_taxonomies(industry, db_session)
        logger.debug(f"Загружено {len(industry_taxonomies)} отраслевых таксономий")

        # Шаг 3: Загрузить пользовательские синонимы организации (переопределяют всё)
        custom_synonyms = self.load_custom_synonyms(organization_id, db_session)
        logger.debug(f"Загружено {len(custom_synonyms)} пользовательских синонимов")

        # Шаг 4: Объединить с приоритетом: custom > industry > static
        merged: Dict[str, List[str]] = {}

        # Начать с статических синонимов (базовый уровень)
        for skill, variants in static_synonyms.items():
            merged[skill] = list(set(variants))

        # Добавить отраслевые таксономии (добавить новые записи, переопределить существующие)
        for skill, variants in industry_taxonomies.items():
            if skill in merged:
                # Объединить с существующими (объединение обоих списков)
                merged[skill] = list(set(merged[skill] + variants))
            else:
                # Добавить новый навык
                merged[skill] = list(set(variants))

        # Добавить пользовательские синонимы организации (наивысший приоритет - переопределить всё)
        for skill, variants in custom_synonyms.items():
            if skill in merged:
                # Заменить пользовательскими синонимами (полное переопределение)
                merged[skill] = list(set(variants))
            else:
                # Добавить новый пользовательский навык
                merged[skill] = list(set(variants))

        if self.use_cache:
            _taxonomy_cache[cache_key] = merged

        logger.info(
            f"Объединение таксономий завершено: {len(merged)} всего навыков "
            f"({len(static_synonyms)} статических + {len(industry_taxonomies)} отраслевых + "
            f"{len(custom_synonyms)} пользовательских)"
        )

        return merged

    def get_all_skills_for_organization(
        self,
        organization_id: str,
        industry: str,
        db_session: Optional[Any] = None,
    ) -> List[str]:
        """
        Get a flat list of all known skill variants for an organization.

        Returns a deduplicated list of all skill names and their synonyms
        across all sources (static, industry, custom).

        Args:
            organization_id: Organization identifier
            industry: Industry sector
            db_session: Optional database session for querying

        Returns:
            Flat list of all skill variants

        Example:
            >>> loader = TaxonomyLoader()
            >>> skills = loader.get_all_skills_for_organization('org123', 'tech')
            >>> print(len(skills))
            1500
        """
        merged = self.load_for_organization(organization_id, industry, db_session)

        # Flatten all variants into a single list
        all_skills = set()
        for variants in merged.values():
            all_skills.update(variants)

        return sorted(list(all_skills))

    def clear_cache(self) -> None:
        """
        Clear all cached taxonomy data.

        This method clears both the global static synonyms cache and
        the merged taxonomy cache. Useful for testing or when database
        data has been updated.

        Example:
            >>> loader = TaxonomyLoader()
            >>> loader.clear_cache()
            >>> # Next load will fetch fresh data
        """
        global _static_synonyms_cache
        _static_synonyms_cache = None
        _taxonomy_cache.clear()
        logger.info("Taxonomy loader cache cleared")

    def normalize_skill_name(self, skill: str) -> str:
        """
        Normalize a skill name for consistent comparison.

        Removes extra whitespace, converts to lowercase, and handles
        common variations in capitalization and spacing.

        Args:
            skill: The skill name to normalize

        Returns:
            Normalized skill name

        Example:
            >>> loader = TaxonomyLoader()
            >>> loader.normalize_skill_name("  React JS  ")
            "react js"
        """
        return " ".join(skill.strip().lower().split())

    def find_matching_skill(
        self,
        resume_skills: List[str],
        required_skill: str,
        organization_id: str,
        industry: str,
        db_session: Optional[Any] = None,
    ) -> Optional[str]:
        """
        Find a matching skill from resume using organization-specific taxonomies.

        This method checks if the required skill exists in the resume skills,
        using the merged taxonomies (static + industry + custom) to perform
        intelligent matching.

        Args:
            resume_skills: List of skills extracted from resume
            required_skill: The skill required by vacancy
            organization_id: Organization identifier
            industry: Industry sector
            db_session: Optional database session

        Returns:
            The matching resume skill name, or None if no match found

        Example:
            >>> loader = TaxonomyLoader()
            >>> # If custom synonym maps 'React' -> 'ReactJS'
            >>> result = loader.find_matching_skill(
            ...     ['ReactJS', 'Python'], 'React', 'org123', 'tech'
            ... )
            >>> print(result)
            "ReactJS"
        """
        normalized_required = self.normalize_skill_name(required_skill)

        # Load merged taxonomies for this organization
        merged_taxonomies = self.load_for_organization(
            organization_id, industry, db_session
        )

        # Build set of all variants for the required skill
        all_variants = {normalized_required}

        for canonical_name, synonym_list in merged_taxonomies.items():
            normalized_canonical = self.normalize_skill_name(canonical_name)
            if normalized_canonical == normalized_required:
                # This canonical name matches - add all its variants
                all_variants.update([self.normalize_skill_name(s) for s in synonym_list])
            else:
                # Check if any synonym matches
                for synonym in synonym_list:
                    if self.normalize_skill_name(synonym) == normalized_required:
                        # This synonym matches - add canonical and all variants
                        all_variants.add(normalized_canonical)
                        all_variants.update(
                            [self.normalize_skill_name(s) for s in synonym_list]
                        )
                        break

        # Find matching resume skill
        for resume_skill in resume_skills:
            if self.normalize_skill_name(resume_skill) in all_variants:
                return resume_skill

        return None
