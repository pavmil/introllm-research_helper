"""Contracts of the agent infrastructure: if one breaks, agents lose rules or context."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml

TASK_STATUSES = {"todo", "in-progress", "blocked", "done", "dropped"}
TASK_SECTIONS = ("## Цель", "## Scope", "## Критерии приёмки", "## Бюджет и стоп-условия")


def front_matter(text: str) -> dict[str, Any]:
    match = re.match(r"^---\n(.*?)\n---\n", text, flags=re.S)
    assert match, "file must start with a YAML front matter block"
    data = yaml.safe_load(match.group(1))
    assert isinstance(data, dict)
    return data


def task_files(repo_root: Path) -> list[Path]:
    return sorted((repo_root / "docs" / "tasks").glob("[0-9][0-9][0-9][0-9]-*.md"))


def test_claude_md_imports_agents_md(repo_root: Path) -> None:
    assert (repo_root / "AGENTS.md").is_file()
    assert "@AGENTS.md" in (repo_root / "CLAUDE.md").read_text(encoding="utf-8")


def test_claude_settings_hooks_point_to_existing_scripts(repo_root: Path) -> None:
    settings = json.loads((repo_root / ".claude" / "settings.json").read_text(encoding="utf-8"))
    commands = [
        hook["command"]
        for groups in settings["hooks"].values()
        for group in groups
        for hook in group["hooks"]
    ]
    assert commands, "loop-guard hooks must be configured"
    for command in commands:
        script = re.search(r"(\.claude/hooks/[\w.-]+\.sh)", command)
        assert script, command
        assert (repo_root / script.group(1)).is_file(), command


def test_secrets_are_denied_to_agents(repo_root: Path) -> None:
    settings = json.loads((repo_root / ".claude" / "settings.json").read_text(encoding="utf-8"))
    assert "Read(./.env)" in settings["permissions"]["deny"]
    assert ".env" in (repo_root / ".gitignore").read_text(encoding="utf-8").splitlines()


def test_task_files_follow_template(repo_root: Path) -> None:
    files = task_files(repo_root)
    assert files, "docs/tasks must contain numbered task files"
    for path in files:
        text = path.read_text(encoding="utf-8")
        meta = front_matter(text)
        assert meta["id"] == f"T-{path.name[:4]}", path.name
        assert meta["status"] in TASK_STATUSES, path.name
        for section in TASK_SECTIONS:
            assert section in text, f"{path.name}: missing {section!r}"


def test_task_index_lists_every_task(repo_root: Path) -> None:
    index = (repo_root / "docs" / "tasks" / "README.md").read_text(encoding="utf-8")
    for path in task_files(repo_root):
        assert f"({path.name})" in index, f"{path.name} is missing from docs/tasks/README.md"


def test_adrs_declare_status(repo_root: Path) -> None:
    adrs = sorted((repo_root / "docs" / "adr").glob("[0-9][0-9][0-9][0-9]-*.md"))
    adrs = [path for path in adrs if not path.name.startswith("0000")]
    assert adrs
    for path in adrs:
        text = path.read_text(encoding="utf-8")
        assert re.search(r"\*\*Статус:\*\* (accepted|proposed|superseded)", text), path.name


def test_history_has_current_status_section(repo_root: Path) -> None:
    history = (repo_root / "docs" / "HISTORY.md").read_text(encoding="utf-8")
    assert "## Где мы сейчас" in history


def test_ci_runs_the_same_check_as_developers(repo_root: Path) -> None:
    workflow = (repo_root / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "make check" in workflow
    assert "uv sync --locked" in workflow
    assert "timeout-minutes" in workflow
