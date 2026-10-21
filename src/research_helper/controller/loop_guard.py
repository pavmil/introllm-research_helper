"""Loop and budget protection for agent and LLM loops (ADR-0002).

Usage inside any loop that calls agents or LLMs::

    guard = LoopGuard(load_budget("default"))
    while not done:
        guard.check_step("expert.answer", {"perspective": p, "question": q})
        response = llm(...)
        guard.record_llm_call(tokens=response.tokens, cost_usd=response.cost)
        if new_verified_claims:
            guard.record_progress(len(new_verified_claims))

The guard raises ``BudgetExceededError`` or ``LoopDetectedError`` (both ``AgentHaltError``).
Agents must not catch them: only the top-level controller does, to finish the run and record
the reason.
"""

from __future__ import annotations

import hashlib
import json
import time
from collections import Counter
from collections.abc import Callable, Mapping
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from research_helper.errors import BudgetExceededError, LoopDetectedError

Payload = Mapping[str, Any] | str | None


class Budget(BaseModel):
    """Hard limits for one run. Limits are inclusive: ``max_steps=200`` allows 200 steps."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    max_steps: int = Field(default=200, gt=0)
    max_llm_calls: int = Field(default=300, gt=0)
    max_tokens: int = Field(default=2_000_000, gt=0)
    max_cost_usd: float = Field(default=5.0, gt=0)
    max_wall_seconds: float = Field(default=900.0, gt=0)
    max_repeats: int = Field(default=3, gt=0)
    """How many times the same action with the same payload may run."""
    max_no_progress_steps: int = Field(default=15, gt=0)
    """How many steps in a row may pass without ``record_progress``."""


class Usage(BaseModel):
    """Snapshot of consumed resources."""

    model_config = ConfigDict(frozen=True)

    steps: int
    llm_calls: int
    tokens: int
    cost_usd: float
    wall_seconds: float
    steps_since_progress: int


def fingerprint(action: str, payload: Payload = None) -> str:
    """Stable short hash of an action and its payload; mapping key order does not matter."""
    body = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(f"{action}\x00{body}".encode()).hexdigest()[:16]


class LoopGuard:
    """Enforces a ``Budget`` and detects repeated actions and lack of progress."""

    def __init__(
        self, budget: Budget | None = None, *, clock: Callable[[], float] = time.monotonic
    ) -> None:
        self.budget = budget or Budget()
        self._clock = clock
        self._started = clock()
        self._steps = 0
        self._llm_calls = 0
        self._tokens = 0
        self._cost_usd = 0.0
        self._steps_since_progress = 0
        self._seen: Counter[str] = Counter()

    def check_step(self, action: str, payload: Payload = None) -> None:
        """Register one loop iteration; raise if a budget is exhausted or a loop is detected."""
        self._steps += 1
        self._steps_since_progress += 1
        key = fingerprint(action, payload)
        self._seen[key] += 1
        self._check_budgets()

        repeats = self._seen[key]
        if repeats > self.budget.max_repeats:
            raise LoopDetectedError(
                f"action {action!r} ran {repeats} times with identical payload "
                f"(max_repeats={self.budget.max_repeats})",
                usage=self.usage().model_dump(),
            )
        if self._steps_since_progress > self.budget.max_no_progress_steps:
            raise LoopDetectedError(
                f"no progress for {self._steps_since_progress} steps "
                f"(max_no_progress_steps={self.budget.max_no_progress_steps})",
                usage=self.usage().model_dump(),
            )

    def record_llm_call(self, *, tokens: int, cost_usd: float) -> None:
        """Account for one LLM call; raise if the call pushed the run over a budget."""
        if tokens < 0 or cost_usd < 0:
            raise ValueError("tokens and cost_usd must be non-negative")
        self._llm_calls += 1
        self._tokens += tokens
        self._cost_usd += cost_usd
        self._check_budgets()

    def record_progress(self, new_items: int = 1) -> None:
        """Mark progress, e.g. verified claims added to the ledger; zero items is not progress."""
        if new_items < 0:
            raise ValueError("new_items must be non-negative")
        if new_items > 0:
            self._steps_since_progress = 0

    def usage(self) -> Usage:
        return Usage(
            steps=self._steps,
            llm_calls=self._llm_calls,
            tokens=self._tokens,
            cost_usd=self._cost_usd,
            wall_seconds=self._clock() - self._started,
            steps_since_progress=self._steps_since_progress,
        )

    def _check_budgets(self) -> None:
        usage = self.usage()
        limits: list[tuple[str, float, float]] = [
            ("steps", usage.steps, self.budget.max_steps),
            ("llm_calls", usage.llm_calls, self.budget.max_llm_calls),
            ("tokens", usage.tokens, self.budget.max_tokens),
            ("cost_usd", usage.cost_usd, self.budget.max_cost_usd),
            ("wall_seconds", usage.wall_seconds, self.budget.max_wall_seconds),
        ]
        for name, value, limit in limits:
            if value > limit:
                raise BudgetExceededError(
                    f"budget {name} exceeded: {value:g} > {limit:g}",
                    usage=usage.model_dump(),
                )
