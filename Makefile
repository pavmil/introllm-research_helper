.DEFAULT_GOAL := help
UV ?= uv

.PHONY: help install lint fmt format-check typecheck test check clean

help: ## Показать доступные команды
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-14s %s\n", $$1, $$2}'

install: ## Поставить окружение и git-хуки pre-commit
	$(UV) sync --all-groups
	$(UV) run pre-commit install --hook-type pre-commit --hook-type pre-push

lint: ## Линтер (ruff)
	$(UV) run ruff check .

fmt: ## Автоформат и автоисправления
	$(UV) run ruff format .
	$(UV) run ruff check --fix .

format-check: ## Проверка форматирования без изменений
	$(UV) run ruff format --check .

typecheck: ## Проверка типов (mypy strict)
	$(UV) run mypy

test: ## Тесты с покрытием (без сетевых)
	$(UV) run pytest

check: lint format-check typecheck test ## Всё, что проверяет CI
	@echo "make check: OK"

clean: ## Удалить кеши и артефакты сборки
	rm -rf .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov dist build
