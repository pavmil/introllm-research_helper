# CONTRIBUTING — правила написания кода

Правила обязательны для людей и ИИ-агентов. Общий рабочий цикл и Definition of Done — в [AGENTS.md](AGENTS.md).

## 1. Окружение

- Python 3.11 (`.python-version`), менеджер — [uv](https://docs.astral.sh/uv/). `pip install` и `requirements.txt` не используем.
- `make install` ставит зависимости и git-хуки pre-commit. `make check` — то же, что CI.
- Зависимости зафиксированы в `uv.lock`. Lock-файл коммитится, CI ставит строго по нему (`uv sync --locked`).

## 2. Стиль кода

- **Форматирование и линт** — ruff, длина строки 100. Не спорим со стилем: `make fmt`.
- **Типы обязательны везде.** mypy в режиме `strict` для `src/` и `tests/`. `Any` — только на границе с внешними данными, сразу дальше валидация в Pydantic.
- **Код, идентификаторы, docstring** — на английском. Документация в `docs/` — на русском.
- **Docstring** нужен у публичных функций и классов: одна строка «что делает» + ограничения и исключения, если они не очевидны. Пересказывать код не нужно.
- **Маленькие функции** (ориентир ≤ 50 строк) и чистые функции там, где возможно.
- **Зависимости передаются явно** (клиенты API, часы, генераторы ID) через параметры конструктора — это делает код тестируемым. Глобальное изменяемое состояние запрещено.
- **Конфиги** лежат в `configs/*.yaml` и загружаются в Pydantic-модели. Магические числа в коде — только с именованной константой и комментарием «почему».
- **`print` в библиотечном коде запрещён** (ruff T20). Используй `logger = logging.getLogger(__name__)`. CLI-вывод — через typer/rich в точке входа.
- **Межмодульные контракты** — Pydantic-модели из `research_helper.schemas`, а не голые `dict`.
- **Промпты** — в `prompts/` как версионированные файлы, а не строки в коде (см. `prompts/README.md`).

## 3. Библиотеки

Используем то, что в таблице. Альтернатива — только через ADR.

| Задача | Используем | Не используем |
|---|---|---|
| Модели данных, валидация | `pydantic` v2 | `dataclasses` для внешних контрактов, «голые» dict между модулями |
| Конфиги | YAML (`pyyaml`) → Pydantic | Константы, разбросанные по коду |
| Секреты и env | `pydantic-settings` | `os.environ[...]` в глубине кода |
| HTTP | `httpx` | `requests`, `aiohttp` |
| Ретраи | `tenacity` | Самописные `while`-циклы с `sleep` |
| LLM | `litellm` только через шлюз `research_helper.llm` | Прямые SDK провайдеров в агентах |
| Оркестрация агентов | Свой FSM-контроллер + `LoopGuard` (ADR-0002) | LangChain, LangGraph, LlamaIndex, CrewAI |
| Sparse retrieval | `bm25s` | Pyserini (JVM) без ADR |
| Dense retrieval | `sentence-transformers`, FAISS или LanceDB | Облачные векторные БД |
| Парсинг PDF | GROBID (через `httpx`), `docling` | Самописный парсинг PDF |
| Хранилище | `sqlite3` (stdlib), Parquet (`pyarrow`) | Серверные БД, тяжёлые ORM |
| Нечёткое сравнение строк | `rapidfuzz` | `fuzzywuzzy` |
| CLI | `typer` | `click` напрямую; `argparse` допустим в `scripts/` |
| Логи | stdlib `logging` | `print`, `loguru` |
| Тесты | `pytest`, `pytest-timeout`, `respx` (моки httpx), `hypothesis` по необходимости | `unittest`, реальные сетевые вызовы |

Сейчас установлены только `pydantic` и `pyyaml`. Остальное добавляется задачей, которой оно нужно.

**Новая зависимость:**
1. `uv add <pkg>`; тяжёлые и опциональные — в группу (`uv add --group retrieval <pkg>`).
2. Обоснуй в PR: зачем, какие альтернативы, вес.
3. Добавь запись в `docs/HISTORY.md`.

Baseline-системы с конфликтующими зависимостями (`knowledge-storm`, `paper-qa`) ставятся в отдельные окружения (`baselines/`), а не в основное.

## 4. Обработка ошибок

Иерархия исключений — в [`src/research_helper/errors.py`](src/research_helper/errors.py):

```
ResearchHelperError
├── ConfigError          неверный или отсутствующий конфиг, env, ключ
├── SourceError          внешний источник не ответил после ретраев
│   └── RateLimitedError лимит запросов не отпустил после ретраев
├── ParseError           документ не разбирается на фрагменты
├── LLMOutputError       ответ LLM не прошёл схему после попытки исправления
└── AgentHaltError       прогон агентов нужно остановить (ловит только контроллер)
    ├── BudgetExceededError
    └── LoopDetectedError
```

**Правила:**

1. **Ловить конкретные исключения.** `except Exception` разрешён только на границе (CLI, API-обработчик, верхний цикл эксперимента) и только с логированием и пробросом или преобразованием. `except: pass` запрещён (ruff BLE, S110).
2. **Сохранять причину:** `raise SourceError("S2 search failed for query=...") from exc`.
3. **Ретраи — только для временных ошибок:**
   - ретраим таймауты, ошибки соединения, HTTP 429 и 5xx;
   - не больше 3 попыток, экспоненциальная задержка с jitter, учитываем `Retry-After`;
   - 4xx (кроме 429) не ретраим — это ошибка запроса;
   - после исчерпания попыток бросаем доменное исключение.
4. **Ответы LLM:** валидация Pydantic → одна попытка исправления → `LLMOutputError`. Вызывающий код пропускает элемент с флагом в трассе, а не роняет весь прогон.
5. **Мягкая деградация** (design-doc §9.2):
   - источник недоступен → продолжаем с тем, что есть, и пишем ограничение в отчёт;
   - PDF не разобрался → работаем по аннотации и ставим флаг;
   - verifier не уверен → NEI.
6. **`AgentHaltError` и наследники** (бюджет, зацикливание) не ловятся внутри агентов. Их ловит только контроллер верхнего уровня, чтобы корректно завершить прогон и записать причину.
7. **Сообщение об ошибке** = что случилось + контекст (ID, запрос, URL **без ключей**) + что можно сделать.
8. **В логах не должно быть:** секретов; полных текстов статей на уровне INFO; персональных данных.

```python
import logging

import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_random_exponential

from research_helper.errors import SourceError

logger = logging.getLogger(__name__)


def _is_transient(exc: BaseException) -> bool:
    if isinstance(exc, httpx.TransportError):
        return True
    return isinstance(exc, httpx.HTTPStatusError) and (
        exc.response.status_code == 429 or exc.response.status_code >= 500
    )


@retry(
    retry=retry_if_exception(_is_transient),
    stop=stop_after_attempt(3),
    wait=wait_random_exponential(multiplier=1, max=20),
    reraise=True,
)
def _get(client: httpx.Client, url: str, params: dict[str, str]) -> httpx.Response:
    response = client.get(url, params=params)
    response.raise_for_status()
    return response


def search(client: httpx.Client, query: str) -> dict[str, object]:
    try:
        return _get(client, "/paper/search", {"query": query}).json()
    except httpx.HTTPError as exc:
        raise SourceError(f"paper search failed for query={query!r}") from exc
```

## 5. Тесты

- **Где лежат:**
  - `tests/unit/` — быстрые тесты модулей;
  - `tests/tooling/` — инфраструктура (хук, конфиги, контракты репозитория);
  - `tests/integration/` — сетевые, только с `@pytest.mark.network`.
- **По умолчанию тесты не ходят в сеть.** HTTP мокаем через `respx`, ответы API кладём фикстурами в `tests/fixtures/<source>/`.
- **Детерминизм:** фиксированные seed, внедрённые часы (`clock=`), никакого `time.sleep` в тестах.
- **Таймаут** каждого теста — 60 с (`pytest-timeout`). Зависший тест — это баг, а не «медленный тест».
- **Покрытие** ≥ 80% (`fail_under`). Понижать порог нельзя без согласования.
- **Имена:** `test_<что>_<при каком условии>_<ожидаемое>`. Проверяй и счастливый путь, и ошибки.
- **Каждый исправленный баг** получает регрессионный тест, который до исправления падал.

## 6. Коммиты и PR

- **Коммиты** по [Conventional Commits](https://www.conventionalcommits.org/): `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`, `ci:`. В теле — ID задачи (`Refs: T-0002`).
- **PR:** маленькие (ориентир до ~400 строк diff), одна задача — один PR, чек-лист из шаблона PR заполнен.
- В `main` попадает только то, что прошло CI.

## 7. Документация

- **`docs/HISTORY.md`** — append-only история шагов и решений. Запись нужна на каждое решение и на завершение этапа.
- **ADR** (`docs/adr/NNNN-slug.md` по шаблону `0000-template.md`) — для решений с альтернативами: библиотека, архитектура, контракт, метрика. Принятый ADR не правится. Новое решение — новым ADR со ссылкой «supersedes».
- **README** обновляется, если меняется установка, запуск или структура.
- **Design doc** обновляется при изменении архитектуры. Изменение фиксируется в HISTORY.
