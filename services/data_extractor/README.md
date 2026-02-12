# Сервис извлечения данных

Сервис извлечения текста из резюме в форматах PDF и DOCX с надёжной обработкой ошибок.

## Возможности

- **Извлечение из PDF**: Поддержка двух библиотек (PyPDF2 + pdfplumber как резервный)
- **Извлечение из DOCX**: Полная поддержка, включая табличные макеты
- **Обработка ошибок**: Корректная обработка некорректных, пустых и повреждённых файлов
- **Валидация**: Предварительная валидация целостности файла перед извлечением
- **Комплексные тесты**: Полный набор тестов с покрытием граничных случаев

## Установка

```bash
# Установка зависимостей
pip install -r requirements.txt
```

### Требования

- Python 3.9+
- PyPDF2==3.0.1
- python-docx==1.1.2
- pdfplumber==0.11.4
- pytest==8.3.3 (для тестирования)

## Использование

### Базовое извлечение из PDF

```python
from extract import extract_text_from_pdf

result = extract_text_from_pdf("resume.pdf")

print(result["text"])      # Извлечённый текст
print(result["method"])    # 'pypdf2' или 'pdfplumber'
print(result["pages"])     # Количество страниц
print(result["error"])     # None при успехе
```

### Базовое извлечение из DOCX

```python
from extract import extract_text_from_docx

result = extract_text_from_docx("resume.docx")

print(result["text"])         # Извлечённый текст
print(result["paragraphs"])   # Количество абзацев
print(result["error"])        # None при успехе
```

### С валидацией

```python
from extract import validate_pdf_file, extract_text_from_pdf

# Сначала валидация
validation = validate_pdf_file("resume.pdf")
if validation["valid"]:
    result = extract_text_from_pdf("resume.pdf")
else:
    print(f"Неверный файл: {validation['reason']}")
```

## Запуск тестов

### Использование pytest (рекомендуется)

```bash
cd services/data_extractor
pytest tests/test_extract.py -v
```

### Запуск определённого тестового класса

```bash
pytest tests/test_extract.py::TestPDFExtraction -v
pytest tests/test_extract.py::TestDOCXExtraction -v
pytest tests/test_extract.py::TestErrorHandling -v
```

### С покрытием

```bash
pytest tests/test_extract.py -v --cov=. --cov-report=term-missing
```

## Структура тестов

```
tests/
├── __init__.py
└── test_extract.py
    ├── TestPDFExtraction      # Тесты извлечения из PDF
    ├── TestDOCXExtraction     # Тесты извлечения из DOCX
    └── TestErrorHandling      # Тесты граничных случаев и ошибок
```

### Покрытие тестами

- **Валидные файлы**: Обычные файлы PDF/DOCX
- **Невалидные файлы**: Неверные расширения, несуществующие файлы
- **Пустые файлы**: Файлы без содержимого
- **Повреждённые файлы**: Некорректная структура файлов
- **Специальные символы**: Юникод и многоязычный текст
- **Таблицы**: Файлы DOCX с табличными макетами
- **Большие файлы**: Многостраничные документы

## Примеры файлов

Примеры тестовых файлов предоставлены в `test_samples/`:

- `sample.pdf` - Пример резюме в формате PDF
- `sample.docx` - Пример резюме в формате DOCX

Эти файлы используются набором тестов для валидации.

## Справочник по API

### Функции для PDF

#### `extract_text_from_pdf(file_path, use_fallback=True)`

Извлекает текст из PDF с поддержкой двух библиотек.

**Параметры:**
- `file_path` (str|Path): Путь к файлу PDF
- `use_fallback` (bool): Использовать pdfplumber при сбое PyPDF2 (по умолчанию: True)

**Возвращает:** Словарь с ключами:
- `text` (str|None): Извлечённый текст
- `method` (str|None): 'pypdf2', 'pdfplumber' или None
- `pages` (int): Количество страниц
- `error` (str|None): Сообщение об ошибке при неудаче

**Raises:**
- `FileNotFoundError`: Если файл не существует
- `ValueError`: Если файл не является PDF

#### `validate_pdf_file(file_path)`

Валидирует PDF файл перед извлечением.

**Возвращает:** Словарь с ключами:
- `valid` (bool): True, если файл валиден
- `reason` (str|None): Пояснение, если файл невалиден

### Функции для DOCX

#### `extract_text_from_docx(file_path)`

Извлекает текст из DOCX, включая содержимое таблиц.

**Параметры:**
- `file_path` (str|Path): Путь к файлу DOCX

**Возвращает:** Словарь с ключами:
- `text` (str|None): Извлечённый текст
- `method` (str|None): 'python-docx' или None
- `paragraphs` (int): Количество абзацев
- `error` (str|None): Сообщение об ошибке при неудаче

**Raises:**
- `FileNotFoundError`: Если файл не существует
- `ValueError`: Если файл не является DOCX

#### `validate_docx_file(file_path)`

Валидирует файл DOCX перед извлечением.

**Возвращает:** Словарь с ключами:
- `valid` (bool): True, если файл валиден
- `reason` (str|None): Пояснение, если файл невалиден

## Обработка ошибок

Сервис корректно обрабатывает различные условия ошибок:

### Файл не найден
```python
extract_text_from_pdf("missing.pdf")
# Raises: FileNotFoundError("File not found: missing.pdf")
```

### Неверный тип файла
```python
extract_text_from_pdf("document.txt")
# Raises: ValueError("File is not a PDF: document.txt")
```

### Повреждённые файлы
```python
result = extract_text_from_pdf("corrupted.pdf")
# Returns: {"text": None, "error": "...", ...}
```

### Пустые файлы
```python
validation = validate_pdf_file("empty.pdf")
# Returns: {"valid": False, "reason": "File is empty"}
```

## Разработка

### Стиль кода

В этом проекте следуют стандартным соглашениям Python:
- Типы для всех параметров функций
- Комплексные docstrings
- Логирование для отладки
- Форматирование PEP 8

### Рекомендации по тестированию

1. **Используйте фикстуры** для повторно используемых тестовых данных
2. **Тестируйте случаи успеха и неудачи**
3. **Проверяйте**, что сообщения об ошибках полезны
4. **Тестируйте граничные случаи** (пустые, повреждённые, большие файлы)
5. **Используйте tmp_path** для временных тестовых файлов

## Устранение неполадок

### Тесты падают с ошибкой "ModuleNotFoundError"

Убедитесь, что запускаете из правильной директории:
```bash
cd services/data_extractor
pytest tests/test_extract.py -v
```

### Извлечение из PDF возвращает минимальный текст

Попробуйте включить режим отката (по умолчанию):
```python
result = extract_text_from_pdf("file.pdf", use_fallback=True)
```

### Извлечение из DOCX пропускает содержимое таблиц

Сервис автоматически извлекает содержимое таблиц. Если отсутствует, убедитесь:
- Файл не повреждён
- Таблицы правильно отформатированы в DOCX

## Лицензия

MIT License - Подробности в файле LICENSE
