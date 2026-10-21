from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from research_helper.controller import Budget, LoopGuard, fingerprint
from research_helper.errors import AgentHaltError, BudgetExceededError, LoopDetectedError


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def make_guard(**limits: Any) -> tuple[LoopGuard, FakeClock]:
    clock = FakeClock()
    return LoopGuard(Budget(**limits), clock=clock), clock


def test_check_step_within_budget_counts_steps() -> None:
    guard, _ = make_guard(max_steps=5)
    for i in range(5):
        guard.check_step("search", {"query": f"q{i}"})
    assert guard.usage().steps == 5


def test_check_step_over_max_steps_raises_budget_exceeded() -> None:
    guard, _ = make_guard(max_steps=3)
    for i in range(3):
        guard.check_step("search", {"query": f"q{i}"})
    with pytest.raises(BudgetExceededError, match="steps") as excinfo:
        guard.check_step("search", {"query": "q3"})
    assert isinstance(excinfo.value, AgentHaltError)
    assert excinfo.value.usage["steps"] == 4


def test_identical_action_over_max_repeats_raises_loop_detected() -> None:
    guard, _ = make_guard(max_repeats=2)
    guard.check_step("search", {"query": "same"})
    guard.check_step("search", {"query": "same"})
    with pytest.raises(LoopDetectedError, match="'search'"):
        guard.check_step("search", {"query": "same"})


def test_fingerprint_ignores_mapping_key_order() -> None:
    assert fingerprint("search", {"q": "x", "k": 5}) == fingerprint("search", {"k": 5, "q": "x"})
    assert fingerprint("search", {"q": "x"}) != fingerprint("search", {"q": "y"})
    assert fingerprint("search", {"q": "x"}) != fingerprint("expand", {"q": "x"})


def test_different_payloads_are_not_counted_as_repeats() -> None:
    guard, _ = make_guard(max_repeats=1)
    for i in range(10):
        guard.check_step("search", {"query": f"q{i}"})


def test_no_progress_raises_loop_detected_and_progress_resets_counter() -> None:
    guard, _ = make_guard(max_no_progress_steps=3)
    for i in range(3):
        guard.check_step("ask", {"turn": i})
    guard.record_progress(2)
    for i in range(3, 6):
        guard.check_step("ask", {"turn": i})
    with pytest.raises(LoopDetectedError, match="no progress"):
        guard.check_step("ask", {"turn": 6})


def test_record_progress_with_zero_items_is_not_progress() -> None:
    guard, _ = make_guard(max_no_progress_steps=1)
    guard.check_step("ask", {"turn": 0})
    guard.record_progress(0)
    with pytest.raises(LoopDetectedError):
        guard.check_step("ask", {"turn": 1})


@pytest.mark.parametrize(
    ("limits", "calls", "budget_name"),
    [
        ({"max_tokens": 100}, [(60, 0.0), (40, 0.0), (1, 0.0)], "tokens"),
        ({"max_cost_usd": 1.0}, [(0, 0.6), (0, 0.5)], "cost_usd"),
        ({"max_llm_calls": 2}, [(1, 0.0), (1, 0.0), (1, 0.0)], "llm_calls"),
    ],
)
def test_llm_budgets_raise_on_the_call_that_exceeds_them(
    limits: dict[str, Any], calls: list[tuple[int, float]], budget_name: str
) -> None:
    guard, _ = make_guard(**limits)
    *within, last = calls
    for tokens, cost in within:
        guard.record_llm_call(tokens=tokens, cost_usd=cost)
    with pytest.raises(BudgetExceededError, match=budget_name):
        guard.record_llm_call(tokens=last[0], cost_usd=last[1])


def test_wall_time_budget_uses_injected_clock() -> None:
    guard, clock = make_guard(max_wall_seconds=10)
    clock.now = 10.0
    guard.check_step("search", {"query": "a"})
    clock.now = 10.5
    with pytest.raises(BudgetExceededError, match="wall_seconds"):
        guard.check_step("search", {"query": "b"})


@pytest.mark.parametrize(("tokens", "cost"), [(-1, 0.0), (0, -0.1)])
def test_record_llm_call_rejects_negative_usage(tokens: int, cost: float) -> None:
    guard, _ = make_guard()
    with pytest.raises(ValueError, match="non-negative"):
        guard.record_llm_call(tokens=tokens, cost_usd=cost)


def test_record_progress_rejects_negative_items() -> None:
    guard, _ = make_guard()
    with pytest.raises(ValueError, match="non-negative"):
        guard.record_progress(-1)


def test_usage_snapshot_reflects_all_counters() -> None:
    guard, clock = make_guard()
    guard.check_step("search", "q")
    guard.record_llm_call(tokens=12, cost_usd=0.25)
    clock.now = 3.0
    usage = guard.usage()
    assert (usage.steps, usage.llm_calls, usage.tokens) == (1, 1, 12)
    assert usage.cost_usd == pytest.approx(0.25)
    assert usage.wall_seconds == pytest.approx(3.0)
    assert usage.steps_since_progress == 1


@pytest.mark.parametrize("bad", [{"max_steps": 0}, {"max_cost_usd": -1}, {"max_stepz": 5}])
def test_budget_rejects_non_positive_and_unknown_fields(bad: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        Budget(**bad)


def test_budget_is_immutable() -> None:
    budget = Budget()
    with pytest.raises(ValidationError):
        budget.max_steps = 1  # type: ignore[misc]
