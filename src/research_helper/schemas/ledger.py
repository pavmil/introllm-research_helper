"""Evidence ledger records (design-doc §5.6, docs/context/glossary.md).

Records are immutable: the ledger is append-only within a run. ``PaperCard`` and evidence
features are added by the Reader and Consolidator tasks.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class _Record(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class TextLevel(StrEnum):
    FULL = "full"
    ABSTRACT = "abstract"


class SpanKind(StrEnum):
    TEXT = "text"
    TABLE = "table"
    CAPTION = "caption"


class VerificationLabel(StrEnum):
    SUPPORTS = "SUPPORTS"
    REFUTES = "REFUTES"
    NEI = "NEI"


class EvidenceLevel(StrEnum):
    STRONG = "strong"
    MODERATE = "moderate"
    LIMITED = "limited"
    CONFLICTING = "conflicting"
    INSUFFICIENT = "insufficient"


class ConflictKind(StrEnum):
    DIRECT = "direct"
    DIFFERENT_CONDITIONS = "different_conditions"
    DIFFERENT_METRICS = "different_metrics"
    DIFFERENT_POPULATIONS = "different_populations"


class ModelRef(_Record):
    """Which model and prompt version produced a record (for traces and ablations)."""

    model: str = Field(min_length=1)
    prompt_version: str | None = None


class Paper(_Record):
    paper_id: str = Field(min_length=1)
    """Semantic Scholar corpus ID — the primary key."""
    title: str = Field(min_length=1)
    year: int | None = Field(default=None, ge=1600, le=2100)
    venue: str | None = None
    authors: tuple[str, ...] = ()
    doi: str | None = None
    arxiv_id: str | None = None
    peer_reviewed: bool = False
    is_retracted: bool = False
    text_level: TextLevel = TextLevel.ABSTRACT
    url: str | None = None


class Span(_Record):
    """Consecutive sentences ``sent_start..sent_end`` (inclusive) of one section of a paper."""

    paper_id: str = Field(min_length=1)
    section_idx: int = Field(ge=0)
    sent_start: int = Field(ge=0)
    sent_end: int = Field(ge=0)
    section_path: str = ""
    kind: SpanKind = SpanKind.TEXT
    text: str = Field(min_length=1)

    @model_validator(mode="after")
    def _check_sentence_range(self) -> Self:
        if self.sent_end < self.sent_start:
            raise ValueError("sent_end must be >= sent_start")
        return self

    @property
    def span_id(self) -> str:
        return f"{self.paper_id}:{self.section_idx}:{self.sent_start}-{self.sent_end}"


class Claim(_Record):
    """Atomic checkable statement from one paper, grounded in at least one of its spans."""

    claim_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    paper_id: str = Field(min_length=1)
    span_ids: tuple[str, ...] = Field(min_length=1)
    perspective_id: str | None = None
    produced_by: ModelRef

    @model_validator(mode="after")
    def _spans_belong_to_paper(self) -> Self:
        foreign = [s for s in self.span_ids if not s.startswith(f"{self.paper_id}:")]
        if foreign:
            raise ValueError(f"span_ids must belong to paper {self.paper_id!r}: {foreign}")
        return self


class Verification(_Record):
    claim_id: str = Field(min_length=1)
    span_id: str = Field(min_length=1)
    label: VerificationLabel
    prob: float = Field(ge=0.0, le=1.0)
    verifier: ModelRef


class Proposition(_Record):
    """Statement merged from claims of several papers, with its evidence level."""

    prop_id: str = Field(min_length=1)
    canonical_text: str = Field(min_length=1)
    subquestion_id: str = Field(min_length=1)
    supporting: tuple[str, ...] = ()
    refuting: tuple[str, ...] = ()
    level: EvidenceLevel = EvidenceLevel.INSUFFICIENT
    level_reasons: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _check_claim_sets(self) -> Self:
        overlap = set(self.supporting) & set(self.refuting)
        if overlap:
            raise ValueError(f"claims cannot both support and refute: {sorted(overlap)}")
        if self.level is EvidenceLevel.CONFLICTING and not (self.supporting and self.refuting):
            raise ValueError("level 'conflicting' needs both supporting and refuting claims")
        return self


class Conflict(_Record):
    prop_id: str = Field(min_length=1)
    claim_a: str = Field(min_length=1)
    claim_b: str = Field(min_length=1)
    kind: ConflictKind
    explanation: str = ""

    @model_validator(mode="after")
    def _distinct_claims(self) -> Self:
        if self.claim_a == self.claim_b:
            raise ValueError("a conflict needs two different claims")
        return self
