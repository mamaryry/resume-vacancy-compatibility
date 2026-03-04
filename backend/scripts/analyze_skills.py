"""
Анализ того, какие навыки извлекаются из тестовых резюме.
"""
import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from analyzers import extract_resume_entities
from services.data_extractor.extract import extract_text_from_docx


async def analyze_cv(cv_num: int):
    """Извлечь и проанализировать навыки из резюме."""
    cv_path = Path(f"data/uploads/{cv_num}.docx")
    
    if not cv_path.exists():
        return None

    # Извлечение текста
    result = extract_text_from_docx(str(cv_path))
    text = result.get("text", "")

    # Извлечение сущностей
    entities = extract_resume_entities(text)

    skills = entities.get("skills") or entities.get("technical_skills") or []

    return {
        'cv': cv_num,
        'text_length': len(text),
        'skills': skills,
        'num_skills': len(skills),
    }


async def main():
    """Проанализировать первые 5 резюме."""
    print("Анализ извлечения навыков из тестовых резюме...\n")
    
    for i in range(1, 6):
        info = await analyze_cv(i)
        if info:
            print(f"CV {info['cv']}: {info['num_skills']} skills extracted")
            print(f"  Text length: {info['text_length']} chars")
            print(f"  Skills: {', '.join(info['skills'][:10])}{'...' if len(info['skills']) > 10 else ''}")
            print()


if __name__ == "__main__":
    asyncio.run(main())
