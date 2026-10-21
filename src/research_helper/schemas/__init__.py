"""Pydantic contracts shared between modules (design-doc §5.6, docs/context/glossary.md)."""

from research_helper.schemas.ledger import (
    Claim,
    Conflict,
    ConflictKind,
    EvidenceLevel,
    ModelRef,
    Paper,
    Proposition,
    Span,
    SpanKind,
    TextLevel,
    Verification,
    VerificationLabel,
)

__all__ = [
    "Claim",
    "Conflict",
    "ConflictKind",
    "EvidenceLevel",
    "ModelRef",
    "Paper",
    "Proposition",
    "Span",
    "SpanKind",
    "TextLevel",
    "Verification",
    "VerificationLabel",
]
