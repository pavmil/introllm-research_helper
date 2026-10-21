from __future__ import annotations

from research_helper.errors import (
    AgentHaltError,
    BudgetExceededError,
    LoopDetectedError,
    RateLimitedError,
    ResearchHelperError,
    SourceError,
)


def test_hierarchy_lets_callers_catch_by_category() -> None:
    assert issubclass(RateLimitedError, SourceError)
    assert issubclass(BudgetExceededError, AgentHaltError)
    assert issubclass(LoopDetectedError, AgentHaltError)
    assert issubclass(AgentHaltError, ResearchHelperError)


def test_agent_halt_error_copies_usage_and_defaults_to_empty() -> None:
    usage = {"steps": 3.0}
    error = LoopDetectedError("stuck", usage=usage)
    usage["steps"] = 99.0
    assert error.usage == {"steps": 3.0}
    assert BudgetExceededError("over").usage == {}
    assert str(error) == "stuck"
