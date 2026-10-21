---
id: T-0004
title: Python 3.12, надёжный запуск хука и первый push
status: in-progress
executor: agent
created: 2026-10-21
links: [T-0001, ADR-0002, docs/plans/week-01.md]
---

# T-0004: Python 3.12, надёжный запуск хука и первый push

## Контекст

Человек попросил:
- перевести проект на Python 3.12+ (был 3.11, а хук был совместим с системным 3.9);
- запушить репозиторий в `github.com/pavmil/introllm-research_helper`.

**Найден баг хука.** После переезда сессии `CLAUDE_PROJECT_DIR` указывал на старую папку. `python3` на отсутствующий скрипт отвечает кодом 2, а Claude Code считает код 2 блокировкой. Итог — все Bash/Edit/Write блокировались. Ошибка настройки хука не должна превращаться в блок.

Отдельный вопрос человека: нужен ли ключ Semantic Scholar, раз за ним надо подавать заявку.

## Цель

- Проект на Python 3.12.
- Хук запускается интерпретатором проекта и никогда не блокирует вызов из-за собственной поломки.
- Ключ S2 в плане помечен как необязательный.
- Всё закоммичено и запушено в `main`, CI на GitHub запущен.

## Входы

- `pyproject.toml`, `.python-version`, `.claude/settings.json`, `.claude/hooks/loop_guard.py`, `.github/workflows/ci.yml`
- README, CONTRIBUTING (упоминания версий), `docs/plans/week-01.md` (ключ S2)
- Remote: публичный пустой репозиторий; SSH-ключ `~/.ssh/id_ed25519`

## Scope

**Делаем:**
- `requires-python >=3.12`, `.python-version` 3.12, ruff/mypy на 3.12, перегенерировать `uv.lock`.
- Обёртку `.claude/hooks/run_loop_guard.sh`. Хук запускается из `.venv` проекта. Если нет `.venv` или скрипта — пропуск с сообщением, а не блок.
- Команду хука в `settings.json` с запасным вариантом на `$PWD`, если `CLAUDE_PROJECT_DIR` пуст или устарел.
- Состояние хука — рядом со скриптом (`.claude/state/`), путь можно переопределить через `LOOP_GUARD_STATE_DIR` (для тестов).
- Убрать CI-job `hook-compat`: хук больше не запускается системным 3.9.
- Регрессионные тесты:
  - команда из `settings.json` с устаревшим `CLAUDE_PROJECT_DIR` не блокирует;
  - обёртка без `.venv` не блокирует.
- Ключ S2 — «желательно, не блокирует» в плане недели и `.env.example`.
- Запись в HISTORY, git-идентичность для коммитов (локально в репозитории), первый коммит, push в `main`.

**Не делаем:**
- Branch protection: нужен доступ к настройкам GitHub (токен или вход в браузере) — делает человек или отдельный шаг с его согласия.

## План

1. Python 3.12: pyproject, `.python-version`, `uv lock`, `uv sync`.
2. Обёртка, новая команда хука, путь состояния, модернизация синтаксиса хука.
3. Тесты на обёртку и на устаревший `CLAUDE_PROJECT_DIR`.
4. CI без `hook-compat`; README и CONTRIBUTING.
5. Ключ S2 необязательный: план недели, `.env.example`, HISTORY.
6. `make check`.
7. Git-идентичность, коммит, `git remote add`, push.

## Контракты

- **Хук:**
  - `sh .claude/hooks/run_loop_guard.sh {pre|post}`, событие JSON на stdin;
  - exit 2 — блок, только по решению `loop_guard.py`; любая ошибка настройки → exit 0 + сообщение в stderr.
- **Переменные окружения:**
  - `LOOP_GUARD_STATE_DIR` — каталог состояния (по умолчанию `.claude/state/loop_guard`);
  - `LOOP_GUARD_MAX_SAME_RESULT`, `LOOP_GUARD_MAX_CALLS` — без изменений.

## Критерии приёмки

- [ ] `uv run python --version` → 3.12.x; `make check` зелёный.
- [ ] Команда хука из `settings.json` с `CLAUDE_PROJECT_DIR=/nonexistent` возвращает 0 — регрессионный тест.
- [ ] Обёртка без `.venv` возвращает 0 и пишет причину — тест.
- [ ] В репозитории не осталось упоминаний Python 3.9 и 3.11 как требований, кроме истории (HISTORY, T-0001).
- [ ] Коммит в `main` запушен, CI-workflow запустился.

## Проверка

```bash
make check
```

```bash
git log --oneline -1
```

```bash
git ls-remote origin
```

## Бюджет и стоп-условия

- Одна сессия.
- Остановиться и спросить, если:
  - push не проходит по правам доступа (SSH и HTTPS);
  - remote оказался не пустым.

## Риски и открытые вопросы

- После включения branch protection с обязательной проверкой `check` прямой push в `main` перестанет проходить. Работа пойдёт через ветки и PR — это и есть цель.
- Email в коммитах публичного репозитория виден всем. Используем noreply-адрес GitHub.

## Журнал выполнения

- 2026-10-21 — задача описана. Найден и описан баг блокировки при устаревшем `CLAUDE_PROJECT_DIR`.

## Итог
