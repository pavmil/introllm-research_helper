---
id: T-0002
title: Клиент Semantic Scholar и retriever для STORM
status: todo
executor: agent
created: 2026-10-20
links: [docs/plans/week-01.md (день 3), design-doc §6.1 §8.3, CONTRIBUTING §3 §4]
---

# T-0002: Клиент Semantic Scholar и retriever для STORM

## Контекст

На неделе 1 запускаем ванильный STORM (baseline B3) на 5 вопросах FreshSci. Чтобы сравнение с нашей системой было честным, B3 должен искать в том же источнике, что и наша система, — в Semantic Scholar. Bing Search API, который STORM поддерживает из коробки, Microsoft закрыл в 2025 г. Клиент S2 — первый компонент `research_helper.sources`, и его потом переиспользует Discovery.

## Цель

`S2Client` ищет статьи и фрагменты с ретраями и ограничением частоты, а адаптер `S2RM` позволяет запустить `knowledge-storm` поверх него. Сетевых вызовов в тестах нет.

## Входы

- Официальная документация Semantic Scholar Academic Graph API. **Перед кодом сверь:**
  - эндпоинты paper search и snippet search;
  - поля ответа;
  - лимиты;
  - заголовок `x-api-key`.
  Не угадывай — если документация расходится с контрактом ниже, обнови контракт и запиши расхождение в журнал.
- Исходники установленного `knowledge-storm`, модуль `knowledge_storm/rm.py`: интерфейс retriever-классов и формат возвращаемых словарей. Читай код установленной версии, а не README.
- CONTRIBUTING §3 (httpx, tenacity, respx), §4 (ошибки и ретраи).
- `.env`: `S2_API_KEY` (может отсутствовать — клиент работает без ключа с пониженным лимитом).

## Scope

**Делаем:**
- `src/research_helper/sources/semantic_scholar.py`: `S2Client` + модели ответа.
- `baselines/storm/s2_rm.py`: адаптер к интерфейсу retriever-а `knowledge-storm`.
- `baselines/storm/run_storm.py`: запуск STORM на одном вопросе. Модель и параметры берёт из аргументов, выход сохраняет в `experiments/<date>_storm_smoke/`.
- `baselines/storm/README.md`: как поставить отдельное окружение и запустить.
- Тесты с фикстурами ответов API.
- ADR-0004: retriever для baseline STORM (S2 vs Tavily/Serper, отдельное окружение для `knowledge-storm`).

**Не делаем:**
- Record/replay кеш — отдельная задача на неделю 2. Интерфейс клиента должен позволять обернуть его позже.
- Загрузку PDF и парсинг.
- OpenAlex (нужен в T-0003 как запасной источник; там и добавляется).

## План

1. Сверить API S2 и интерфейс RM в `knowledge-storm`, записать находки в журнал.
2. `uv add httpx tenacity`; `uv add --group dev respx`.
3. Модели `S2Paper`, `S2Snippet` и клиент `S2Client` с ретраями и rate limiter-ом (часы внедряются).
4. Тесты клиента на respx-фикстурах.
5. Отдельное окружение для `knowledge-storm` (см. CONTRIBUTING §3), адаптер `S2RM` и тест преобразования формата без установки `knowledge-storm` (преобразование — чистая функция).
6. Скрипт запуска + README. Ручной прогон на 1 вопросе делает человек: нужны ключи.
7. ADR-0004, запись в HISTORY, итог задачи.

## Контракты

```python
class S2Paper(BaseModel):  # frozen
    paper_id: str
    title: str
    abstract: str | None
    year: int | None
    venue: str | None
    authors: list[str]
    external_ids: dict[str, str]  # DOI, ArXiv, ...
    url: str | None
    is_open_access: bool | None


class S2Snippet(BaseModel):  # frozen
    paper_id: str
    title: str
    text: str
    section: str | None
    score: float | None


class S2Client:
    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str = ...,
        timeout_s: float = 30.0,
        max_attempts: int = 3,
        min_interval_s: float = 1.0,
        http: httpx.Client | None = None,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None: ...
    def search_papers(
        self, query: str, *, limit: int = 20, year: str | None = None
    ) -> list[S2Paper]: ...
    def search_snippets(self, query: str, *, limit: int = 10) -> list[S2Snippet]: ...


def snippets_to_storm_results(
    snippets: list[S2Snippet],
) -> list[dict[str, Any]]: ...  # чистая функция
```

**Ошибки** (CONTRIBUTING §4):
- 429 и 5xx после ретраев → `RateLimitedError` / `SourceError`;
- 4xx (кроме 429) → сразу `SourceError` без ретраев;
- невалидный JSON или несовпадение схемы → `SourceError` с контекстом запроса (без ключа).

## Критерии приёмки

- [ ] Клиент:
  - ретраит 429/5xx/таймауты (не больше `max_attempts`, учитывает `Retry-After`);
  - не ретраит 400/404;
  - соблюдает `min_interval_s` между запросами.
  Всё проверено тестами с внедрёнными часами и `sleep`.
- [ ] Ключ передаётся в заголовке и не появляется в сообщениях исключений и логах — есть тест.
- [ ] `snippets_to_storm_results` даёт формат, совпадающий с тем, что возвращают RM-классы установленного `knowledge-storm`. Формат записан в docstring со ссылкой на файл и версию.
- [ ] Сетевой smoke-тест помечен `@pytest.mark.network` и в CI не запускается.
- [ ] `make check` зелёный, покрытие не упало ниже 80%.
- [ ] ADR-0004, запись в HISTORY, журнал и итог задачи заполнены.

## Проверка

```bash
make check
```

```bash
uv run pytest -m network tests/integration/test_s2_live.py
```

Второе — вручную, с ключом.

## Бюджет и стоп-условия

- Ориентир: 1 рабочая сессия.
- Остановиться и спросить, если:
  - API S2 не поддерживает snippet search так, как описано в контракте (тогда предложить замену: abstracts из paper search);
  - `knowledge-storm` конфликтует по зависимостям даже в отдельном окружении;
  - одна и та же ошибка 3 раза подряд.

## Риски и открытые вопросы

- Без ключа S2 лимит запросов низкий и общий — STORM может упираться в 429. Запасной вариант: Tavily/Serper с ограничением на arxiv.org, решение фиксируется в ADR-0004.
- Версия `knowledge-storm` фиксируется в окружении baseline: формат RM может меняться между версиями.

## Журнал выполнения

## Итог
