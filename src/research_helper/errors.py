"""Exception hierarchy of the project (CONTRIBUTING.md §4)."""

from __future__ import annotations

from collections.abc import Mapping


class ResearchHelperError(Exception):
    """Base class for all project errors."""


class ConfigError(ResearchHelperError):
    """A configuration file, environment variable or key is missing or invalid."""


class SourceError(ResearchHelperError):
    """An external source (search API, PDF host) failed after retries."""


class RateLimitedError(SourceError):
    """An external source kept rate-limiting requests after retries."""


class ParseError(ResearchHelperError):
    """A document could not be parsed into spans."""


class LLMOutputError(ResearchHelperError):
    """LLM output failed schema validation after the repair attempt."""


class AgentHaltError(ResearchHelperError):
    """An agent run must stop. Only the top-level controller catches this (ADR-0002).

    ``usage`` is a snapshot of consumed resources at the moment of the halt, so the run
    can record why and where it stopped.
    """

    def __init__(self, message: str, *, usage: Mapping[str, float] | None = None) -> None:
        super().__init__(message)
        self.usage: dict[str, float] = dict(usage or {})


class BudgetExceededError(AgentHaltError):
    """A hard budget (steps, LLM calls, tokens, cost, wall time) was exceeded."""


class LoopDetectedError(AgentHaltError):
    """The run repeats the same action or makes no progress."""
