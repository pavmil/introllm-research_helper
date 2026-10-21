from __future__ import annotations

from pathlib import Path

import pytest

from research_helper.config import load_budget
from research_helper.controller import Budget
from research_helper.errors import ConfigError


def test_repo_budgets_file_profiles_are_valid(repo_root: Path) -> None:
    path = repo_root / "configs" / "budgets.yaml"
    default = load_budget("default", path)
    smoke = load_budget("smoke", path)
    assert isinstance(default, Budget)
    assert smoke.max_steps < default.max_steps
    assert smoke.max_cost_usd < default.max_cost_usd


def test_unknown_profile_lists_available_profiles(tmp_path: Path) -> None:
    path = tmp_path / "budgets.yaml"
    path.write_text("default:\n  max_steps: 10\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="available: default"):
        load_budget("nope", path)


def test_missing_file_raises_config_error(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="not found"):
        load_budget("default", tmp_path / "missing.yaml")


@pytest.mark.parametrize(
    ("content", "message"),
    [
        ("default: [unclosed\n", "not valid YAML"),
        ("- just\n- a list\n", "must map profile names"),
        ("default:\n  max_steps: -5\n", "invalid budget profile"),
        ("default:\n  unknown_limit: 1\n", "invalid budget profile"),
    ],
)
def test_invalid_budgets_file_raises_config_error(
    tmp_path: Path, content: str, message: str
) -> None:
    path = tmp_path / "budgets.yaml"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(ConfigError, match=message):
        load_budget("default", path)
