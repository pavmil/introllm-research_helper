---
id: T-0003
title: Проверка существования ссылок для B0
status: todo
executor: agent
created: 2026-10-20
links: [docs/plans/week-01.md (день 3), T-0002, design-doc §3, §8.3]
---

# T-0003: Проверка существования ссылок для B0

## Контекст

B0 — LLM без поиска — отвечает на вопросы FreshSci со списком литературы. Первая цифра проекта — **доля выдуманных ссылок** у B0, и она мотивирует ADR-0003 (ссылки по построению). Нужен инструмент, который для каждой ссылки решает: существует ли такая статья.

## Цель

Утилита читает ответы B0 (JSONL), для каждой ссылки ищет статью в S2 (запасной вариант — OpenAlex) и выдаёт статус `found` / `not_found` / `ambiguous` с обоснованием. Итог — CSV и сводка с долей выдуманных ссылок.

## Входы

- `S2Client` из T-0002 (**зависимость: T-0002 должна быть done**).
- Документация OpenAlex API (`/works?search=`, поле `title`, `publication_year`, polite pool через `mailto`).
- CONTRIBUTING §3 (`rapidfuzz`, `typer`), §4.

## Scope

**Делаем:**
- `prompts/b0_closed_book.v1.md` — промпт B0: ответ + список литературы в JSON (title, authors, year, venue).
- `src/research_helper/evaluation/citation_check.py`: модели, сопоставление, CLI.
- `src/research_helper/sources/openalex.py`: минимальный клиент поиска работ по названию (по правилам T-0002: ретраи, rate limit, внедрённый HTTP-клиент).
- Тесты: нормализация названий, нечёткое сопоставление, граничные случаи, CLI на фикстурах.

**Не делаем:**
- Проверку, *подтверждает* ли статья утверждение — это задача судьи (неделя 2).
- Запуск B0 на вопросах — делает человек (нужны ключи и FreshSci).

## План

1. `uv add rapidfuzz typer`.
2. Модели `Reference`, `ReferenceCheck`; нормализация названия (регистр, пунктуация, подзаголовок после двоеточия, LaTeX-артефакты).
3. Сопоставление:
   - кандидаты из S2 (top-5);
   - `found`, если `token_set_ratio ≥ 90` и год совпадает ±1;
   - `ambiguous`, если 75–90 или год не совпадает;
   - иначе запрос в OpenAlex, затем `not_found`.
   Пороги — параметры, а не константы.
4. CLI: `uv run python -m research_helper.evaluation.citation_check INPUT.jsonl --out OUT.csv`. Печатает сводку: всего, found, not_found, ambiguous, доля выдуманных.
5. Промпт B0 и пример входного JSONL в `tests/fixtures/b0/`.
6. Тесты, HISTORY, итог.

## Контракты

```python
class Reference(BaseModel):  # frozen
    question_id: str
    ref_idx: int
    title: str
    authors: list[str] = []
    year: int | None = None
    venue: str | None = None


class ReferenceCheck(BaseModel):  # frozen
    reference: Reference
    status: Literal["found", "not_found", "ambiguous"]
    matched_paper_id: str | None
    matched_title: str | None
    title_score: float  # 0..100
    year_delta: int | None
    source: Literal["s2", "openalex", "none"]
    note: str


def normalize_title(title: str) -> str: ...
def match_reference(
    ref: Reference,
    candidates: list[Candidate],
    *,
    found_threshold: float = 90.0,
    ambiguous_threshold: float = 75.0,
    year_tolerance: int = 1,
) -> ReferenceCheck: ...
```

**Формат входа (JSONL):** по строке на ответ — `{"question_id": ..., "system": "b0", "answer": ..., "references": [...]}`.

## Критерии приёмки

- [ ] `match_reference` — чистая функция, покрыта тестами на:
  - точное совпадение;
  - регистр и пунктуацию;
  - подзаголовок;
  - год ±1 и ±2;
  - похожее, но другое название;
  - пустой список кандидатов.
- [ ] Сбой S2 (`SourceError`) не роняет весь прогон: ссылка получает статус после попытки через OpenAlex, а при сбое обоих — `ambiguous` с `note` о причине.
- [ ] CLI на фикстуре даёт ожидаемый CSV — есть тест через `typer.testing.CliRunner`.
- [ ] Сеть в тестах не используется.
- [ ] `make check` зелёный.
- [ ] HISTORY и итог задачи заполнены.

## Проверка

```bash
make check
```

## Бюджет и стоп-условия

- Ориентир: 1 рабочая сессия.
- Остановиться и спросить, если:
  - пороги сопоставления на 20 размеченных вручную ссылках дают больше 2 ошибок — нужна ручная калибровка с человеком;
  - одна и та же ошибка 3 раза подряд.

## Риски и открытые вопросы

- LLM может выдавать реальные названия с неверными авторами или годом. Это не `not_found`, а отдельный тип ошибки. Помечать в `note` (`year_mismatch`, `authors_mismatch`), в долю выдуманных не включать.
- Препринт и журнальная версия могут иметь разные названия → `ambiguous`; разбирать вручную.

## Журнал выполнения

## Итог
