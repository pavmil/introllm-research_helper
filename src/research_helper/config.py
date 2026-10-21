"""Loading of YAML configs from ``configs/`` into typed models."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from research_helper.controller.loop_guard import Budget
from research_helper.errors import ConfigError

DEFAULT_BUDGETS_PATH = Path("configs/budgets.yaml")


def load_budget(profile: str = "default", path: Path = DEFAULT_BUDGETS_PATH) -> Budget:
    """Load one budget profile from a YAML file that maps profile names to budgets.

    Raises ``ConfigError`` if the file is missing or invalid, or the profile is unknown.
    """
    try:
        raw: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigError(f"budgets file not found: {path}") from exc
    except yaml.YAMLError as exc:
        raise ConfigError(f"budgets file is not valid YAML: {path}") from exc

    if not isinstance(raw, dict):
        raise ConfigError(f"budgets file must map profile names to budgets: {path}")
    if profile not in raw:
        available = ", ".join(sorted(str(name) for name in raw)) or "none"
        raise ConfigError(f"unknown budget profile {profile!r} in {path}; available: {available}")
    try:
        return Budget.model_validate(raw[profile])
    except ValidationError as exc:
        raise ConfigError(f"invalid budget profile {profile!r} in {path}: {exc}") from exc
