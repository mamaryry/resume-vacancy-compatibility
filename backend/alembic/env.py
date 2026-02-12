"""
Конфигурация окружения Alembic для миграций базы данных

Этот файл выполняется Alembic при запуске команд миграции.
Он настраивает подключение к базе данных и предоставляет контекст для миграций.
"""
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Импорт моделей и base для поддержки autogenerate
from models import Base  # noqa: E402
from models.analysis_result import AnalysisResult  # noqa: E402
from models.job_vacancy import JobVacancy  # noqa: E402
from models.match_result import MatchResult  # noqa: E402
from models.resume import Resume  # noqa: E402

# это объект конфигурации Alembic
config = context.config

# Интерпретация файла конфигурации для логирования Python
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Установка URL базы данных из переменной окружения, если доступна
database_url = os.environ.get("DATABASE_URL")
if database_url:
    config.set_main_option("sqlalchemy.url", database_url)

# Добавьте MetaData объект вашей модели здесь для поддержки 'autogenerate'
target_metadata = Base.metadata

# Другие значения из конфигурации, определённые потребностями env.py
# могут быть получены my = context.config.x.get_extension()
# для multi-database или других нужд


def run_migrations_offline() -> None:
    """
    Запуск миграций в режиме 'offline'.

    Это настраивает контекст только с URL, а не с Engine,
    хотя Engine здесь также приемлем. Пропуская создание Engine,
    нам даже не нужен доступный DBAPI.

    Вызовы context.execute() здесь выводят данную строку в вывод скрипта.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Запуск миграций в режиме 'online'.

    В этом сценарии нам нужно создать Engine и связать подключение
    с контекстом.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
