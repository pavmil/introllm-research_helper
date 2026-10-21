---
id: T-0001
title: Bootstrap репозитория и инфраструктуры для агентов
status: done
executor: agent
created: 2026-10-20
links: [docs/design-doc.md §7 §9 §11, ADR-0002]
---

# T-0001: Bootstrap репозитория и инфраструктуры для агентов

## Контекст

Архитектура (design doc v0.1) и план недели 1 готовы. Дальше разработка идёт в основном силами ИИ-агентов, поэтому до первого кода нужны правила, контекст и автоматические проверки. Иначе агенты будут каждый раз заново угадывать договорённости.

## Цель

Репозиторий, в котором агент за 5 минут понимает проект и правила, любое изменение проверяется одной командой `make check` локально и в CI, а зацикливание агента ограничено и в коде продукта, и в работе dev-агента.

## Входы

- `design-doc.md`, `week-1-plan.md`, шаблоны golden set и разметки (из папки сессии)
- Решения: домашний домен ML/NLP (ADR-0001), детерминированный контроллер (design doc §5.1)

## Scope

**Делаем:**
- Структура каталогов по design doc §11 (адаптированная)
- README, AGENTS.md, CLAUDE.md, CONTRIBUTING.md, docs/HISTORY.md, контекст, глоссарий, ADR, шаблон задач
- `pyproject.toml` (uv), Makefile, ruff, mypy strict, pytest с таймаутами и покрытием, pre-commit
- `LoopGuard` (бюджеты + детекция повторов и отсутствия прогресса) с тестами
- Базовые схемы ledger (Paper, Span, Claim, Verification, Proposition, Conflict) с тестами
- Хук Claude Code против зацикливания dev-агента + тесты
- GitHub Actions: `make check` на каждый push в main и на каждый PR
- Задачи T-0002 и T-0003 для недели 1

**Не делаем:**
- Код агентов, поиска, парсинга (это следующие задачи)
- Push на GitHub и настройку branch protection (действия человека)
- CD: деплоить пока нечего; вернуться на этапе демо (неделя 12)

## План

1. Описать эту задачу.
2. Каркас: pyproject, Makefile, конфиги, .gitignore, .env.example.
3. Документы для людей и агентов.
4. Код: errors, LoopGuard, config, схемы ledger + тесты.
5. Хук против зацикливания + settings.json + тесты.
6. CI, pre-commit; прогнать `make check` локально.
7. Записать итог в HISTORY и в эту задачу.

## Контракты

- `research_helper.controller.LoopGuard(budget, clock=...)`:
  - `check_step(action, payload)`
  - `record_llm_call(tokens=, cost_usd=)`
  - `record_progress(new_items)`
  - `usage()`
- `research_helper.config.load_budget(profile="default", path=Path("configs/budgets.yaml")) -> Budget`
- Исключения: `research_helper.errors` (иерархия от `ResearchHelperError`)
- Хук: `.claude/hooks/loop_guard.py {pre|post}`, JSON на stdin; exit 2 = блок

## Критерии приёмки

- [ ] `make check` зелёный локально (ruff, format, mypy strict, pytest, покрытие ≥ 80%)
- [ ] CI-workflow запускает тот же `make check`
- [ ] Хук проверен pipe-тестом и работает на системном Python 3.9
- [ ] AGENTS.md описывает рабочий цикл, DoD, правила остановки; CLAUDE.md импортирует AGENTS.md
- [ ] HISTORY содержит историю решений с начала проекта

## Проверка

```bash
make check
```

## Бюджет и стоп-условия

- Одна сессия. Стоп, если зависимости не ставятся (нет сети) — тогда записать и сдать без локального прогона.

## Риски и открытые вопросы

- Хук срабатывает только в новой сессии Claude Code, открытой в этом репозитории.
- Branch protection на GitHub нужно включить вручную после первого push.

## Журнал выполнения

- 2026-10-20 — задача описана, начат bootstrap.
- 2026-10-21 — первый `make check`: одна длинная строка (E501) и 4 файла на автоформат. Ruff форматирует и Python-блоки в Markdown — оставили: примеры кода в docs заодно проверяются на синтаксис.
- 2026-10-21 — `make check` зелёный: 60 тестов, покрытие 99%, mypy strict без ошибок. Хук проверен pipe-тестом на системном Python 3.9.6 (4-й одинаковый прогон заблокирован, exit 2). `settings.json` проверен `jq`, `.pre-commit-config.yaml` — `pre-commit validate-config`.

## Итог

**Сделано:**
- Структура, документы для людей и агентов, `uv.lock`, CI (`check` + `hook-compat` на Python 3.9), dependabot для actions.
- `LoopGuard`, схемы ledger, хук против зацикливания — с тестами.
- Задачи T-0002 и T-0003 расписаны по шаблону.

**Отклонения от плана:**
- Тесты контрактов репозитория (`tests/tooling/test_repo_contracts.py`) добавлены сверх плана: они ловят поломку инфраструктуры агентов — пропавший импорт AGENTS.md, хук без скрипта, задачу без обязательных разделов.
- ADR о retriever-е baseline перенумерован в 0004 и вынесен в T-0002.

**Не сделано (действия человека):**
- Первый коммит и push на GitHub.
- Branch protection для `main`.
- Проверка, что хук срабатывает в новой сессии Claude Code, открытой в репозитории.

**HISTORY:** этап 2.
