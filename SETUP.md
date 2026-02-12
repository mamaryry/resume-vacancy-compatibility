# TEAM7 Платформа анализа резюме

Система анализа резюме на основе ИИ с интеллектуальным сопоставлением вакансий.

## Быстрый старт

Выберите вашу операционную систему:

### macOS / Linux

```bash
bash setup.sh
```

### Windows (PowerShell)

```powershell
.\setup.ps1
```

Скрипт выполнит следующие действия:
1. Проверит установлен ли Docker
2. Создаст конфигурационный файл `.env`
3. Соберёт и запустит все сервисы
4. Проверит работоспособность сервисов

Затем откройте http://localhost:5173 в вашем браузере.

## Загрузка тестовых данных

После установки загрузите примеры резюме и вакансий:

### macOS / Linux

```bash
bash scripts/load_test_data.sh
```

### Windows (PowerShell)

```powershell
.\scripts\load-test-data.ps1
```

Это загрузит:
- **65 резюме** (формат DOCX)
- **5 вакансий** (различные технические роли)

## Требования

- **Docker Desktop** (Mac/Windows) или Docker + Docker Compose (Linux)
- **8 ГБ ОЗУ** минимум (рекомендуется 16 ГБ)
- **5 ГБ места на диске**

### Примечания для Windows

- Требуется **Windows 10/11** с установленным Docker Desktop
- Запускайте PowerShell от имени **Администратора** при необходимости
- Если выполнение скриптов заблокировано, выполните: `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`

## Сервисы

| Сервис | URL | Описание |
|--------|-----|------------|
| Фронтенд | http://localhost:5173 | React UI |
| API бэкенда | http://localhost:8000 | Бэкенд FastAPI |
| Документация API | http://localhost:8000/docs | Интерактивная документация API |
| Flower | http://localhost:5555 | Мониторинг задач Celery |

## Ручная настройка (Альтернатива)

Если вы предпочитаете ручную настройку:

```bash
# 1. Скопируйте файл окружения
cp .env.example .env

# 2. Запустите все сервисы
docker-compose up -d
# Windows: docker compose up -d

# 3. Просмотр логов
docker-compose logs -f
# Windows: docker compose logs -f
```

## Основные команды

```bash
# Просмотр всех логов
docker-compose logs -f           # Mac/Linux
docker compose logs -f           # Windows

# Просмотр логов определённого сервиса
docker-compose logs -f backend   # Mac/Linux
docker compose logs backend      # Windows

# Перезапуск сервисов
docker-compose restart           # Mac/Linux
docker compose restart           # Windows

# Остановка всех сервисов
docker-compose down              # Mac/Linux
docker compose down              # Windows

# Остановка и удаление томов (удаляет данные)
docker-compose down -v           # Mac/Linux
docker compose down -v           # Windows
```

## Возможности

- **Загрузка и анализ резюме**: Загрузка резюме в формате PDF/DOCX для анализа ИИ
- **Сопоставление вакансий**: Сравнение резюме с вакансиями
- **Мультиязычность**: Поддержка английского и русского языков
- **Панель аналитики**: Отслеживание метрик найма и воронок
- **Таксономия навыков**: Кастомное сопоставление навыков с синонимами
- **Система обратной связи**: Улучшение точности сопоставления с течением времени

## Тестовые данные

Репозиторий включает образцы данных для тестирования:

- **65 резюме** в `testdata/vacancy-resume-matching-dataset-main/CV/`
- **5 вакансий** в `testdata/vacancy-resume-matching-dataset-main/5_vacancies.csv`

Вакансии включают:
- Software Developer - .NET
- Remote Software Developer (Python/Java/C++)
- Backend Software Developer (LAMP stack)
- Junior Level Software Developer
- Software Developer (Java/C#)

## Устранение неполадок

**Порт уже занят?**
Отредактируйте `.env` и измените `FRONTEND_PORT` или `BACKEND_PORT`.

**Сервисы не запускаются?**
```bash
docker-compose logs backend    # Mac/Linux
docker compose logs backend    # Windows
```

**PowerShell сообщает, что скрипты отключены?**
Выполните: `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`

**Нужно сбросить всё?**
```bash
docker-compose down -v          # Mac/Linux
docker compose down -v          # Windows
bash setup.sh                   # Mac/Linux
.\setup.ps1                     # Windows
```

## Структура проекта

```
├── backend/               # Бэкенд FastAPI
├── frontend/              # Фронтенд React + Vite
├── docker-compose.yml     # Конфигурация сервисов Docker
├── setup.sh               # Скрипт настройки для Mac/Linux
├── setup.ps1              # Скрипт настройки для Windows
├── scripts/
│   ├── load_test_data.sh      # Загрузчик тестовых данных (Mac/Linux)
│   └── load-test-data.ps1     # Загрузчик тестовых данных (Windows)
├── testdata/              # Образцы резюме и вакансий
└── .env.example           # Шаблон переменных окружения
```

## Поддержка

При возникновении проблем или вопросов обращайтесь к команде TEAM7.
