"""Run control: the deterministic controller (design-doc §5.5) and loop/budget protection.

Every loop that calls agents or LLMs must go through ``LoopGuard`` (ADR-0002).
"""

from research_helper.controller.loop_guard import Budget, LoopGuard, Usage, fingerprint

__all__ = ["Budget", "LoopGuard", "Usage", "fingerprint"]
