"""
Система версионирования моделей с логикой распределения A/B-тестирования.

Этот модуль обеспечивает интеллектуальное управление версиями моделей машинного обучения,
включая возможности A/B-тестирования, отслеживание производительности и автоматический выбор моделей.
Система поддерживает:
- Управление активными версиями моделей
- A/B-тестирование с настраиваемым распределением трафика
- Продвижение моделей на основе производительности
- Обработка резервных вариантов при сбоях моделей
"""
import hashlib
import logging
from typing import Any, Dict, List, Optional, Tuple

from models.ml_model_version import MLModelVersion

logger = logging.getLogger(__name__)


class ModelVersionManager:
    """
    Менеджер версионирования моделей с логикой распределения A/B-тестирования.

    Этот класс предоставляет методы для управления версиями моделей ML, распределения трафика
    между моделями для A/B-тестирования и отслеживания метрик производительности для
    автоматического продвижения моделей.

    Attributes:
        default_fallback_version: Версия по умолчанию, используемая при отсутствии активной модели

    Example:
        >>> manager = ModelVersionManager()
        >>> model_info = manager.get_active_model('skill_matching')
        >>> print(model_info['version'])
        'v1.0.0'
        >>> allocated_model = manager.allocate_model_for_user('skill_matching', 'user123')
        >>> print(allocated_model['version'])
        'v2.0.0'  # Пользователь назначен экспериментальной модели
    """

    # Резервная версия по умолчанию при отсутствии активной модели
    DEFAULT_FALLBACK_VERSION = "v1.0.0"

    def __init__(self, default_fallback_version: Optional[str] = None) -> None:
        """
        Initialize the model version manager.

        Args:
            default_fallback_version: Default version to use as fallback
                                     (defaults to DEFAULT_FALLBACK_VERSION)
        """
        self.default_fallback_version = (
            default_fallback_version or self.DEFAULT_FALLBACK_VERSION
        )

    def get_active_model(
        self, model_name: str, db_session: Optional[Any] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Получить текущую активную версию модели для данного названия модели.

        Выполняет запрос к базе данных для активной (неэкспериментальной) версии модели,
        помеченной как активная. Это производственная модель, которая получает
        большую часть трафика.

        Args:
            model_name: Название модели (например, 'skill_matching', 'resume_parser')
            db_session: Необязательная сессия базы данных для запросов

        Returns:
            Словарь с информацией о модели (id, version, file_path и т.д.)
            или None, если активная модель не найдена

        Example:
            >>> manager = ModelVersionManager()
            >>> model = manager.get_active_model('skill_matching')
            >>> print(model['version'])
            'v1.2.0'
        """
        if db_session is None:
            logger.debug(
                f"Не предоставлена сессия базы данных для get_active_model({model_name}), возвращается None"
            )
            return None

        try:
            # Запрос активной, неэкспериментальной модели
            active_model = (
                db_session.query(MLModelVersion)
                .filter(
                    MLModelVersion.model_name == model_name,
                    MLModelVersion.is_active == True,
                    MLModelVersion.is_experiment == False,
                )
                .first()
            )

            if active_model:
                model_info = {
                    "id": str(active_model.id),
                    "model_name": active_model.model_name,
                    "version": active_model.version,
                    "file_path": active_model.file_path,
                    "performance_score": float(active_model.performance_score)
                    if active_model.performance_score
                    else None,
                    "model_metadata": active_model.model_metadata or {},
                    "accuracy_metrics": active_model.accuracy_metrics or {},
                    "is_active": active_model.is_active,
                    "is_experiment": active_model.is_experiment,
                }
                logger.info(
                    f"Найдена активная модель {model_name}:{active_model.version} "
                    f"(оценка: {model_info['performance_score']})"
                )
                return model_info
            else:
                logger.warning(f"Активная модель для {model_name} не найдена")
                return None

        except Exception as e:
            logger.error(
                f"Ошибка получения активной модели для {model_name}: {e}", exc_info=True
            )
            return None

    def get_experiment_models(
        self, model_name: str, db_session: Optional[Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all experimental model versions for A/B testing.

        Returns all models marked as experiments for the given model name,
        along with their traffic allocation configuration.

        Args:
            model_name: Name of the model
            db_session: Optional database session for querying

        Returns:
            List of dictionaries with experimental model information

        Example:
            >>> manager = ModelVersionManager()
            >>> experiments = manager.get_experiment_models('skill_matching')
            >>> for exp in experiments:
            ...     print(f"{exp['version']}: {exp['traffic_percentage']}%")
        """
        if db_session is None:
            logger.debug(
                f"No database session provided for get_experiment_models({model_name}), returning []"
            )
            return []

        try:
            # Query for experimental models
            experiment_models = (
                db_session.query(MLModelVersion)
                .filter(
                    MLModelVersion.model_name == model_name,
                    MLModelVersion.is_experiment == True,
                )
                .all()
            )

            experiments = []
            for model in experiment_models:
                # Extract traffic percentage from experiment_config
                traffic_percentage = 0
                if model.experiment_config:
                    traffic_percentage = model.experiment_config.get(
                        "traffic_percentage", 0
                    )

                exp_info = {
                    "id": str(model.id),
                    "model_name": model.model_name,
                    "version": model.version,
                    "file_path": model.file_path,
                    "performance_score": float(model.performance_score)
                    if model.performance_score
                    else None,
                    "traffic_percentage": traffic_percentage,
                    "model_metadata": model.model_metadata or {},
                    "accuracy_metrics": model.accuracy_metrics or {},
                }
                experiments.append(exp_info)

            logger.info(
                f"Found {len(experiments)} experimental models for {model_name}"
            )
            return experiments

        except Exception as e:
            logger.error(
                f"Error getting experiment models for {model_name}: {e}", exc_info=True
            )
            return []

    def allocate_model_for_user(
        self,
        model_name: str,
        user_id: str,
        db_session: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Распределить версию модели для конкретного пользователя с использованием логики A/B-тестирования.

        Этот метод реализует согласованное распределение A/B-тестирования путём хеширования
        user_id для детерминированного назначения пользователей версиям моделей.
        Это обеспечивает, что один и тот же пользователь всегда получает одну и ту же версию модели.

        Стратегия распределения:
        1. Получить все активные и экспериментальные модели
        2. Рассчитать общее распределение трафика (control + experiments)
        3. Хешировать user_id для получения значения 0-100
        4. Назначить пользователю модель на основе сегментов трафика

        Args:
            model_name: Название модели
            user_id: Уникальный идентификатор пользователя для согласованного распределения
            db_session: Необязательная сессия базы данных для запросов

        Returns:
            Словарь с информацией о распределённой модели

        Example:
            >>> manager = ModelVersionManager()
            >>> model = manager.allocate_model_for_user('skill_matching', 'user123')
            >>> print(model['version'])
            'v2.0.0-experiment'
        """
        # Получить активную (control) модель
        active_model = self.get_active_model(model_name, db_session)
        if not active_model:
            logger.warning(f"Нет активной модели для {model_name}, используется резервный вариант")
            return {
                "model_name": model_name,
                "version": self.default_fallback_version,
                "file_path": None,
                "is_fallback": True,
                "allocation_type": "fallback",
            }

        # Получить экспериментальные модели
        experiments = self.get_experiment_models(model_name, db_session)

        # Если нет экспериментов, вернуть активную модель
        if not experiments:
            logger.debug(f"Нет экспериментов для {model_name}, используется активная модель")
            return {
                **active_model,
                "is_fallback": False,
                "allocation_type": "control",
            }

        # Рассчитать сегменты распределения
        # Control модель получает оставшийся трафик после экспериментов
        total_experiment_traffic = sum(
            exp.get("traffic_percentage", 0) for exp in experiments
        )
        control_traffic = 100 - total_experiment_traffic

        # Хешировать user_id для согласованного распределения
        # Использовать SHA256 для равномерного распределения
        hash_value = int(hashlib.sha256(user_id.encode()).hexdigest(), 16)
        bucket = hash_value % 100

        # Распределить на основе сегментов трафика
        cumulative_traffic = 0

        # Сначала проверить экспериментальные модели
        for exp in experiments:
            traffic = exp.get("traffic_percentage", 0)
            cumulative_traffic += traffic
            if bucket < cumulative_traffic:
                logger.info(
                    f"Пользователь {user_id} назначен эксперименту {exp['version']} "
                    f"(сегмент: {bucket}, трафик: {traffic}%)"
                )
                return {
                    **exp,
                    "is_fallback": False,
                    "allocation_type": "experiment",
                }

        # По умолчанию использовать control модель
        logger.info(
            f"Пользователь {user_id} назначен control {active_model['version']} "
            f"(сегмент: {bucket}, control трафик: {control_traffic}%)"
        )
        return {
            **active_model,
            "is_fallback": False,
            "allocation_type": "control",
        }

    def get_all_model_versions(
        self, model_name: str, db_session: Optional[Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all model versions (both active and experimental) for a model.

        Args:
            model_name: Name of the model
            db_session: Optional database session for querying

        Returns:
            List of all model versions with their metadata

        Example:
            >>> manager = ModelVersionManager()
            >>> versions = manager.get_all_model_versions('skill_matching')
            >>> for v in versions:
            ...     print(f"{v['version']} - active: {v['is_active']}")
        """
        if db_session is None:
            logger.debug(
                f"No database session provided for get_all_model_versions({model_name}), returning []"
            )
            return []

        try:
            # Query all model versions
            all_models = (
                db_session.query(MLModelVersion)
                .filter(MLModelVersion.model_name == model_name)
                .order_by(MLModelVersion.created_at.desc())
                .all()
            )

            versions = []
            for model in all_models:
                version_info = {
                    "id": str(model.id),
                    "model_name": model.model_name,
                    "version": model.version,
                    "file_path": model.file_path,
                    "performance_score": float(model.performance_score)
                    if model.performance_score
                    else None,
                    "is_active": model.is_active,
                    "is_experiment": model.is_experiment,
                    "experiment_config": model.experiment_config or {},
                    "model_metadata": model.model_metadata or {},
                    "accuracy_metrics": model.accuracy_metrics or {},
                    "created_at": model.created_at.isoformat()
                    if model.created_at
                    else None,
                    "updated_at": model.updated_at.isoformat()
                    if model.updated_at
                    else None,
                }
                versions.append(version_info)

            logger.info(f"Found {len(versions)} total versions for {model_name}")
            return versions

        except Exception as e:
            logger.error(
                f"Error getting all model versions for {model_name}: {e}", exc_info=True
            )
            return []

    def calculate_model_metrics(
        self, model_name: str, db_session: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Calculate aggregate metrics for all versions of a model.

        Computes summary statistics including performance scores,
        accuracy metrics, and A/B testing traffic distribution.

        Args:
            model_name: Name of the model
            db_session: Optional database session for querying

        Returns:
            Dictionary with aggregate metrics

        Example:
            >>> manager = ModelVersionManager()
            >>> metrics = manager.calculate_model_metrics('skill_matching')
            >>> print(metrics['total_versions'])
            3
        """
        versions = self.get_all_model_versions(model_name, db_session)

        if not versions:
            return {
                "model_name": model_name,
                "total_versions": 0,
                "active_version": None,
                "experiment_count": 0,
                "avg_performance_score": 0.0,
                "best_performance_score": 0.0,
                "traffic_distribution": {},
            }

        # Separate active and experimental models
        active_model = next(
            (v for v in versions if v["is_active"] and not v["is_experiment"]), None
        )
        experiments = [v for v in versions if v["is_experiment"]]

        # Calculate performance metrics
        scores = [
            v["performance_score"]
            for v in versions
            if v["performance_score"] is not None
        ]
        avg_score = sum(scores) / len(scores) if scores else 0.0
        best_score = max(scores) if scores else 0.0

        # Build traffic distribution
        traffic_dist = {}
        if active_model:
            traffic_dist["control"] = 100 - sum(
                e.get("experiment_config", {}).get("traffic_percentage", 0)
                for e in experiments
            )
        for exp in experiments:
            traffic_pct = exp.get("experiment_config", {}).get("traffic_percentage", 0)
            if traffic_pct > 0:
                traffic_dist[exp["version"]] = traffic_pct

        return {
            "model_name": model_name,
            "total_versions": len(versions),
            "active_version": active_model["version"] if active_model else None,
            "experiment_count": len(experiments),
            "avg_performance_score": round(avg_score, 2),
            "best_performance_score": round(best_score, 2),
            "traffic_distribution": traffic_dist,
        }

    def recommend_promotion(
        self,
        model_name: str,
        min_performance_improvement: float = 5.0,
        min_sample_size: int = 100,
        db_session: Optional[Any] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Recommend whether an experimental model should be promoted to active.

        Compares experimental model performance against the active model
        and recommends promotion if:
        1. Performance improvement exceeds threshold
        2. Sample size is sufficient
        3. Accuracy metrics show consistent improvement

        Args:
            model_name: Name of the model
            min_performance_improvement: Minimum performance gain to recommend promotion
            min_sample_size: Minimum sample size for statistical significance
            db_session: Optional database session for querying

        Returns:
            Dictionary with promotion recommendation or None if no clear winner

        Example:
            >>> manager = ModelVersionManager()
            >>> rec = manager.recommend_promotion('skill_matching')
            >>> if rec['should_promote']:
            ...     print(f"Promote {rec['experiment_version']} to active")
        """
        active_model = self.get_active_model(model_name, db_session)
        experiments = self.get_experiment_models(model_name, db_session)

        if not active_model or not experiments:
            logger.debug(
                f"Cannot recommend promotion for {model_name}: "
                f"active={bool(active_model)}, experiments={len(experiments)}"
            )
            return None

        best_candidate = None
        best_improvement = 0.0

        for exp in experiments:
            # Check if experiment has sufficient sample size
            sample_size = exp.get("accuracy_metrics", {}).get("sample_size", 0)
            if sample_size < min_sample_size:
                logger.debug(
                    f"Experiment {exp['version']} has insufficient sample size: {sample_size}"
                )
                continue

            # Compare performance scores
            active_score = active_model.get("performance_score", 0) or 0
            exp_score = exp.get("performance_score", 0) or 0

            if exp_score > active_score:
                improvement = ((exp_score - active_score) / active_score * 100)
                if improvement > best_improvement:
                    best_improvement = improvement
                    best_candidate = exp

        if best_candidate and best_improvement >= min_performance_improvement:
            logger.info(
                f"Recommending promotion of {best_candidate['version']} "
                f"for {model_name} (improvement: {best_improvement:.2f}%)"
            )
            return {
                "should_promote": True,
                "model_name": model_name,
                "current_active": active_model["version"],
                "experiment_version": best_candidate["version"],
                "performance_improvement_pct": round(best_improvement, 2),
                "active_score": active_model.get("performance_score", 0),
                "experiment_score": best_candidate.get("performance_score", 0),
            }

        logger.info(
            f"No experiment meets promotion criteria for {model_name} "
            f"(best improvement: {best_improvement:.2f}%)"
        )
        return {
            "should_promote": False,
            "model_name": model_name,
            "reason": "No experiment meets performance criteria",
            "best_improvement_pct": round(best_improvement, 2),
        }
