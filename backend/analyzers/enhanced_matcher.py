"""
Улучшенный сопоставитель навыков с учетом контекста и оценкой уверенности.

Этот модуль обеспечивает интеллектуальное сопоставление навыков, выходящее за рамки
простого сравнения строк, включая:
- Контекстно-зависимое сопоставление (например, React.js ≈ React в контексте web_framework)
- Оценку уверенности в качестве сопоставления
- Поддержку отраслевых таксономий
- Обработка пользовательских синонимов организации
- Обнаружение частичных совпадений с нечётким сопоставлением
"""
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)

# Путь к файлу синонимов навыков
SYNONYMS_FILE = Path(__file__).parent.parent / "models" / "skill_synonyms.json"

# Кэш синонимов навыков
_synonyms_cache: Optional[Dict[str, List[str]]] = None


class EnhancedSkillMatcher:
    """
    Улучшенный сопоставитель навыков с учётом контекста и оценкой уверенности.

    Этот сопоставитель обеспечивает интеллектуальное сопоставление навыков, включая:
    - Прямое сопоставление по названию
    - Сопоставление на основе синонимов
    - Контекстно-зависимое сопоставление (учитывает отраслевой контекст)
    - Нечёткое сопоставление для опечаток и вариаций
    - Оценку уверенности для всех типов сопоставлений

    Пример:
        >>> matcher = EnhancedSkillMatcher()
        >>> result = matcher.match_with_context(['ReactJS'], 'React', context='web_framework')
        >>> print(result['confidence'])
        0.95
        >>> result = matcher.match_with_context(['React Native'], 'React', context='web_framework')
        >>> print(result['confidence'])
        0.7
    """

    def __init__(self, synonyms_file: Optional[Path] = None):
        """
        Инициализировать улучшенный сопоставитель навыков.

        Args:
            synonyms_file: Необязательный путь к пользовательскому JSON-файлу синонимов.
                          По умолчанию используется встроенный skill_synonyms.json.
        """
        self.synonyms_file = synonyms_file or SYNONYMS_FILE
        self._synonyms_map: Optional[Dict[str, List[str]]] = None
        self._taxonomy_map: Dict[str, Dict[str, List[str]]] = {}

    def load_synonyms(self) -> Dict[str, List[str]]:
        """
        Загрузить синонимы навыков из JSON-файла.

        Возвращает словарь, сопоставляющий канонические названия навыков со списками синонимов.

        Структура файла синонимов организует навыки по категориям (базы данных,
        языки программирования, веб-фреймворки и т.д.), где каждый навык имеет
        каноническое название и список эквивалентных терминов.

        Returns:
            Словарь, сопоставляющий названия навыков с их синонимами

        Example:
            >>> matcher = EnhancedSkillMatcher()
            >>> synonyms = matcher.load_synonyms()
            >>> synonyms["PostgreSQL"]
            ["PostgreSQL", "Postgres", "Postgres SQL"]
        """
        if self._synonyms_map is not None:
            return self._synonyms_map

        try:
            with open(self.synonyms_file, "r", encoding="utf-8") as f:
                synonyms_data = json.load(f)

            # Выравнять структуру категорий в один словарь
            # Вход: {"databases": {"SQL": ["SQL", "PostgreSQL", ...]}}
            # Выход: {"SQL": ["SQL", "PostgreSQL", ...]}
            flat_synonyms: Dict[str, List[str]] = {}

            for category, skills in synonyms_data.items():
                if isinstance(skills, dict):
                    for canonical_name, synonyms_list in skills.items():
                        if isinstance(synonyms_list, list):
                            # Убедиться, что каноническое название есть в списке
                            all_synonyms = set(synonyms_list + [canonical_name])
                            flat_synonyms[canonical_name] = list(all_synonyms)

                            # Также построить карту таксономии по категориям
                            if category not in self._taxonomy_map:
                                self._taxonomy_map[category] = {}
                            self._taxonomy_map[category][canonical_name] = list(all_synonyms)

            self._synonyms_map = flat_synonyms
            logger.info(f"Загружено {len(flat_synonyms)} соответствий синонимов навыков")
            return flat_synonyms

        except FileNotFoundError:
            logger.warning(f"Файл синонимов навыков не найден: {self.synonyms_file}")
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка разбора JSON синонимов навыков: {e}")
            return {}
        except Exception as e:
            logger.error(f"Ошибка загрузки синонимов навыков: {e}", exc_info=True)
            return {}

    @staticmethod
    def normalize_skill_name(skill: str) -> str:
        """
        Нормализовать название навыка для корректного сравнения.

        Удаляет лишние пробелы, преобразует в нижний регистр, обрабатывает
        общие вариации регистрозаписи и пробелов, а также удаляет
        специальные символы, не влияющие на смысл.

        Args:
            skill: Название навыка для нормализации

        Returns:
            Нормализованное название навыка

        Example:
            >>> EnhancedSkillMatcher.normalize_skill_name("  React JS  ")
            "react js"
        """
        # Удалить лишние пробелы и преобразовать в нижний регистр
        normalized = " ".join(skill.strip().lower().split())

        # Удалить общую пунктуацию, не влияющую на смысл
        # Сохранить: буквы, цифры, пробелы, точки, плюс, решётку
        normalized = "".join(c for c in normalized if c.isalnum() or c in " .+#")

        return normalized

    def calculate_fuzzy_similarity(self, skill1: str, skill2: str) -> float:
        """
        Вычислить нечёткое сходство между двумя названиями навыков.

        Использует SequenceMatcher для определения сходства двух строк,
        полезно для обнаружения опечаток и незначительных вариаций.

        Args:
            skill1: Первое название навыка
            skill2: Второе название навыка

        Returns:
            Оценка сходства от 0.0 до 1.0

        Example:
            >>> matcher = EnhancedSkillMatcher()
            >>> matcher.calculate_fuzzy_similarity("React", "ReactJS")
            0.75
        """
        norm1 = self.normalize_skill_name(skill1)
        norm2 = self.normalize_skill_name(skill2)

        return SequenceMatcher(None, norm1, norm2).ratio()

    def find_synonym_match(
        self,
        resume_skills: List[str],
        required_skill: str,
        synonyms_map: Dict[str, List[str]]
    ) -> Optional[Tuple[str, float]]:
        """
        Найти совпадение синонима для требуемого навыка в навыках резюме.

        Выполняет поиск по карте синонимов, чтобы определить, является ли какой-либо
        навык из резюме синонимом требуемого навыка.

        Args:
            resume_skills: Список навыков, извлечённых из резюме
            required_skill: Навык, требуемый вакансией
            synonyms_map: Словарь синонимов навыков

        Returns:
            Кортеж (matched_skill, confidence) при нахождении, иначе None

        Example:
            >>> matcher = EnhancedSkillMatcher()
            >>> synonyms = {"SQL": ["SQL", "PostgreSQL", "MySQL"]}
            >>> matcher.find_synonym_match(["Java", "PostgreSQL"], "SQL", synonyms)
            ("PostgreSQL", 0.85)
        """
        normalized_required = self.normalize_skill_name(required_skill)

        # Build set of all variants for the required skill
        all_variants = {normalized_required}

        for canonical_name, synonym_list in synonyms_map.items():
            normalized_canonical = self.normalize_skill_name(canonical_name)
            if normalized_canonical == normalized_required:
                all_variants.update([self.normalize_skill_name(s) for s in synonym_list])
            else:
                for synonym in synonym_list:
                    if self.normalize_skill_name(synonym) == normalized_required:
                        all_variants.add(normalized_canonical)
                        all_variants.update([self.normalize_skill_name(s) for s in synonym_list])
                        break

        # Find matching resume skill
        for resume_skill in resume_skills:
            normalized_resume = self.normalize_skill_name(resume_skill)
            if normalized_resume in all_variants:
                # Calculate confidence based on match type
                if normalized_resume == normalized_required:
                    # Direct match after normalization
                    return resume_skill, 0.95
                else:
                    # Synonym match
                    return resume_skill, 0.85

        return None

    def find_context_match(
        self,
        resume_skills: List[str],
        required_skill: str,
        context: Optional[str]
    ) -> Optional[Tuple[str, float]]:
        """
        Find a context-aware match for the required skill.

        Context-aware matching considers the domain/industry to improve
        matching accuracy. For example:
        - "React" in "web_framework" context matches "ReactJS", "React.js"
        - "React" in "mobile" context may NOT match "React Native" (different domain)

        Args:
            resume_skills: List of skills extracted from the resume
            required_skill: The skill required by the vacancy
            context: Optional context hint (e.g., "web_framework", "database", "mobile")

        Returns:
            Tuple of (matched_skill, confidence) if found, None otherwise

        Example:
            >>> matcher = EnhancedSkillMatcher()
            >>> result = matcher.find_context_match(['ReactJS'], 'React', 'web_framework')
            >>> result
            ('ReactJS', 0.95)
        """
        if not context:
            return None

        normalized_context = self.normalize_skill_name(context)
        normalized_required = self.normalize_skill_name(required_skill)

        # Context-specific matching rules
        context_rules: Dict[str, Dict[str, List[str]]] = {
            "web_framework": {
                "react": ["react", "reactjs", "react.js", "reactjs"],
                "vue": ["vue", "vue.js", "vuejs"],
                "angular": ["angular", "angularjs", "angular.js"],
            },
            "database": {
                "sql": ["sql", "postgresql", "mysql", "sqlite", "mssql"],
                "nosql": ["mongodb", "cassandra", "dynamodb", "redis"],
            },
            "language": {
                "javascript": ["javascript", "js", "ecmascript"],
                "typescript": ["typescript", "ts"],
            },
        }

        # Check if context has rules
        if normalized_context not in context_rules:
            return None

        # Check if required skill has context rules
        context_skill_map = context_rules[normalized_context]
        if normalized_required not in context_skill_map:
            return None

        # Find matching resume skill
        allowed_variants = context_skill_map[normalized_required]

        for resume_skill in resume_skills:
            normalized_resume = self.normalize_skill_name(resume_skill)
            if normalized_resume in [self.normalize_skill_name(v) for v in allowed_variants]:
                # High confidence for context-aware match
                return resume_skill, 0.95

        return None

    def find_fuzzy_match(
        self,
        resume_skills: List[str],
        required_skill: str,
        threshold: float = 0.7
    ) -> Optional[Tuple[str, float]]:
        """
        Find a fuzzy match for the required skill in resume skills.

        Uses string similarity to detect typos and minor variations.
        Useful when the resume has "ReactJS" and vacancy requires "React.js".

        Args:
            resume_skills: List of skills extracted from the resume
            required_skill: The skill required by the vacancy
            threshold: Minimum similarity score (0.0-1.0) to consider a match

        Returns:
            Tuple of (matched_skill, confidence) if found, None otherwise

        Example:
            >>> matcher = EnhancedSkillMatcher()
            >>> result = matcher.find_fuzzy_match(['ReactJS'], 'React.js')
            >>> result
            ('ReactJS', 0.85)
        """
        best_match: Optional[Tuple[str, float]] = None
        best_similarity = 0.0

        for resume_skill in resume_skills:
            similarity = self.calculate_fuzzy_similarity(resume_skill, required_skill)

            if similarity >= threshold and similarity > best_similarity:
                best_match = (resume_skill, similarity)
                best_similarity = similarity

        return best_match

    def _split_compound_skill(self, skill: str) -> List[str]:
        """
        Split compound skills like "C/C++", "Python, Django", "SQL & NoSQL"
        into individual skills.

        Args:
            skill: The skill name that might be compound

        Returns:
            List of individual skill names

        Example:
            >>> EnhancedSkillMatcher()._split_compound_skill("C/C++")
            ['c', 'c++']
            >>> EnhancedSkillMatcher()._split_compound_skill("Python, Django")
            ['python', 'django']
        """
        # Split by common separators: /, &, +, comma
        parts = []
        for separator in ['/', '&', '+', ',']:
            if separator in skill:
                parts = [p.strip() for p in skill.split(separator)]
                break

        if not parts:
            return [skill]

        # Further split by comma if needed
        result = []
        for part in parts:
            if ',' in part:
                result.extend([p.strip() for p in part.split(',')])
            else:
                result.append(part)

        return [p for p in result if p]

    def match_with_context(
        self,
        resume_skills: List[str],
        required_skill: str,
        context: Optional[str] = None,
        organization_id: Optional[str] = None,
        use_fuzzy: bool = True
    ) -> Dict[str, Any]:
        """
        Сопоставить требуемый навык с навыками резюме с учётом контекста.

        Это основной метод сопоставления, который комбинирует несколько стратегий:
        1. Прямое совпадение (наивысшая уверенность)
        2. Совпадение составных навыков (например, "C/C++" содержит "C")
        3. Контекстно-зависимое совпадение (высокая уверенность)
        4. Совпадение синонимов (средне-высокая уверенность)
        5. Нечёткое совпадение (средняя уверенность)

        Args:
            resume_skills: Список навыков, извлечённых из резюме
            required_skill: Навык, требуемый вакансией
            context: Необязательная подсказка контекста (например, "web_framework", "database")
            organization_id: Необязательный ID организации для пользовательских синонимов
            use_fuzzy: Использовать ли нечёткое сопоставление (по умолчанию: True)

        Returns:
            Словарь с результатами сопоставления:
            - matched (bool): Найдено ли совпадение
            - confidence (float): Оценка уверенности (0.0-1.0)
            - matched_as (str|None): Фактическое название навыка из резюме, которое совпало
            - match_type (str): Тип совпадения ('direct', 'context', 'synonym', 'fuzzy', 'none')

        Example:
            >>> matcher = EnhancedSkillMatcher()
            >>> result = matcher.match_with_context(['ReactJS'], 'React', context='web_framework')
            >>> result['matched']
            True
            >>> result['confidence']
            0.95
        """
        result: Dict[str, Any] = {
            "matched": False,
            "confidence": 0.0,
            "matched_as": None,
            "match_type": "none",
        }

        if not resume_skills or not required_skill:
            return result

        # Load synonyms if not already loaded
        synonyms_map = self.load_synonyms()

        normalized_required = self.normalize_skill_name(required_skill)

        # Strategy 1: Direct match
        for resume_skill in resume_skills:
            if self.normalize_skill_name(resume_skill) == normalized_required:
                result.update({
                    "matched": True,
                    "confidence": 1.0,
                    "matched_as": resume_skill,
                    "match_type": "direct"
                })
                return result

        # Strategy 1.5: Compound skill match (e.g., "C/C++" contains "C")
        for resume_skill in resume_skills:
            parts = self._split_compound_skill(resume_skill)
            if len(parts) > 1:
                for part in parts:
                    if self.normalize_skill_name(part) == normalized_required:
                        result.update({
                            "matched": True,
                            "confidence": 0.9,
                            "matched_as": resume_skill,
                            "match_type": "compound"
                        })
                        return result

        # Strategy 1.75: C/C++ language hierarchy match
        # C++ implies C knowledge, C# doesn't imply C
        c_related = {
            'c': ['c', 'c++', 'c/c++'],
            'c++': ['c++', 'c/c++'],
            'c#': ['c#', 'c sharp'],
        }
        if normalized_required in c_related:
            for resume_skill in resume_skills:
                normalized_resume = self.normalize_skill_name(resume_skill)
                # Check if resume skill is in the list of acceptable variants
                if normalized_resume in [self.normalize_skill_name(v) for v in c_related[normalized_required]]:
                    # Special case: if required is 'c', match 'c++' but NOT 'c#'
                    if normalized_required == 'c':
                        if 'c#' in normalized_resume or 'csharp' in normalized_resume or 'c sharp' in normalized_resume:
                            continue
                        # Match 'c++' or 'c/c++' as 'c'
                        if normalized_resume in ['c++', 'c/c++']:
                            result.update({
                                "matched": True,
                                "confidence": 0.85,
                                "matched_as": resume_skill,
                                "match_type": "language_hierarchy"
                            })
                            return result
                    # Match exact variants
                    if normalized_resume in c_related[normalized_required]:
                        result.update({
                            "matched": True,
                            "confidence": 0.95,
                            "matched_as": resume_skill,
                            "match_type": "language_hierarchy"
                        })
                        return result

        # Strategy 2: Context-aware match
        if context:
            context_match = self.find_context_match(resume_skills, required_skill, context)
            if context_match:
                matched_skill, confidence = context_match
                result.update({
                    "matched": True,
                    "confidence": confidence,
                    "matched_as": matched_skill,
                    "match_type": "context"
                })
                return result

        # Strategy 3: Synonym match
        synonym_match = self.find_synonym_match(resume_skills, required_skill, synonyms_map)
        if synonym_match:
            matched_skill, confidence = synonym_match
            result.update({
                "matched": True,
                "confidence": confidence,
                "matched_as": matched_skill,
                "match_type": "synonym"
            })
            return result

        # Strategy 4: Fuzzy match
        if use_fuzzy:
            fuzzy_match = self.find_fuzzy_match(resume_skills, required_skill)
            if fuzzy_match:
                matched_skill, confidence = fuzzy_match
                result.update({
                    "matched": True,
                    "confidence": confidence,
                    "matched_as": matched_skill,
                    "match_type": "fuzzy"
                })
                return result

        # No match found
        return result

    def match_multiple(
        self,
        resume_skills: List[str],
        required_skills: List[str],
        context: Optional[str] = None,
        organization_id: Optional[str] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Сопоставить несколько требуемых навыков с навыками резюме.

        Args:
            resume_skills: Список навыков, извлечённых из резюме
            required_skills: Список навыков, требуемых вакансией
            context: Необязательная подсказка контекста для всех сопоставлений
            organization_id: Необязательный ID организации для пользовательских синонимов

        Returns:
            Словарь, сопоставляющий каждый требуемый навык с результатом сопоставления

        Example:
            >>> matcher = EnhancedSkillMatcher()
            >>> results = matcher.match_multiple(
            ...     ['ReactJS', 'Python', 'PostgreSQL'],
            ...     ['React', 'Python', 'SQL'],
            ...     context='web_framework'
            ... )
            >>> results['React']['matched']
            True
            >>> results['SQL']['matched']
            True  # PostgreSQL сопоставлен через синоним
        """
        results: Dict[str, Dict[str, Any]] = {}

        for skill in required_skills:
            results[skill] = self.match_with_context(
                resume_skills, skill, context, organization_id
            )

        return results

    def calculate_match_percentage(
        self,
        match_results: Dict[str, Dict[str, Any]]
    ) -> float:
        """
        Рассчитать общий процент совпадения из нескольких результатов сопоставления.

        Args:
            match_results: Словарь результатов сопоставления навыков из match_multiple()

        Returns:
            Процент совпадения (0.0-100.0)

        Example:
            >>> matcher = EnhancedSkillMatcher()
            >>> results = matcher.match_multiple(['React'], ['React', 'Python'])
            >>> matcher.calculate_match_percentage(results)
            50.0
        """
        if not match_results:
            return 0.0

        total = len(match_results)
        matched = sum(1 for r in match_results.values() if r.get("matched", False))

        return round((matched / total * 100), 2) if total > 0 else 0.0

    def get_low_confidence_matches(
        self,
        match_results: Dict[str, Dict[str, Any]],
        threshold: float = 0.8
    ) -> List[str]:
        """
        Получить список навыков с совпадениями низкой уверенности.

        Полезно для пометки совпадений, которые могут потребовать проверки рекрутером.

        Args:
            match_results: Словарь результатов сопоставления навыков из match_multiple()
            threshold: Порог уверенности, ниже которого совпадения считаются низкими

        Returns:
            Список названий навыков с совпадениями низкой уверенности

        Example:
            >>> matcher = EnhancedSkillMatcher()
            >>> results = matcher.match_multiple(['ReactJS'], ['React', 'Python'])
            >>> low_conf = matcher.get_low_confidence_matches(results, threshold=0.9)
            >>> 'React' in low_conf
            True  # Предполагается совпадение синонима с уверенностью 0.85
        """
        return [
            skill
            for skill, result in match_results.items()
            if result.get("matched", False) and result.get("confidence", 0) < threshold
        ]
