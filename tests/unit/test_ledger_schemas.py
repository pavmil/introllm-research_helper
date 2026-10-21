from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from research_helper.schemas import (
    Claim,
    Conflict,
    ConflictKind,
    EvidenceLevel,
    ModelRef,
    Paper,
    Proposition,
    Span,
    Verification,
    VerificationLabel,
)

MODEL = ModelRef(model="test-model", prompt_version="expert.v1")


def make_claim(**overrides: Any) -> Claim:
    fields: dict[str, Any] = {
        "claim_id": "c1",
        "text": "X improves F1 on Y by 2 points.",
        "paper_id": "p1",
        "span_ids": ("p1:3:0-1",),
        "produced_by": MODEL,
    }
    fields.update(overrides)
    return Claim(**fields)


def test_span_id_encodes_paper_section_and_sentences() -> None:
    span = Span(paper_id="p1", section_idx=3, sent_start=4, sent_end=6, text="...")
    assert span.span_id == "p1:3:4-6"


def test_span_rejects_reversed_sentence_range() -> None:
    with pytest.raises(ValidationError, match="sent_end"):
        Span(paper_id="p1", section_idx=0, sent_start=5, sent_end=4, text="...")


def test_claim_requires_at_least_one_span() -> None:
    with pytest.raises(ValidationError):
        make_claim(span_ids=())


def test_claim_rejects_spans_of_another_paper() -> None:
    with pytest.raises(ValidationError, match="must belong to paper"):
        make_claim(span_ids=("p1:0:0-0", "p2:0:0-0"))


def test_valid_claim_is_frozen_and_forbids_extra_fields() -> None:
    claim = make_claim()
    with pytest.raises(ValidationError):
        claim.text = "changed"  # type: ignore[misc]
    with pytest.raises(ValidationError):
        make_claim(confidence=0.9)


@pytest.mark.parametrize("prob", [-0.01, 1.01])
def test_verification_probability_must_be_in_unit_interval(prob: float) -> None:
    with pytest.raises(ValidationError):
        Verification(
            claim_id="c1",
            span_id="p1:0:0-0",
            label=VerificationLabel.SUPPORTS,
            prob=prob,
            verifier=MODEL,
        )


def test_proposition_rejects_claim_both_supporting_and_refuting() -> None:
    with pytest.raises(ValidationError, match="both support and refute"):
        Proposition(
            prop_id="P1",
            canonical_text="X improves Y",
            subquestion_id="q1",
            supporting=("c1", "c2"),
            refuting=("c2",),
        )


def test_conflicting_level_requires_both_sides() -> None:
    with pytest.raises(ValidationError, match="conflicting"):
        Proposition(
            prop_id="P1",
            canonical_text="X improves Y",
            subquestion_id="q1",
            supporting=("c1",),
            level=EvidenceLevel.CONFLICTING,
        )
    prop = Proposition(
        prop_id="P1",
        canonical_text="X improves Y",
        subquestion_id="q1",
        supporting=("c1",),
        refuting=("c2",),
        level=EvidenceLevel.CONFLICTING,
    )
    assert prop.level is EvidenceLevel.CONFLICTING


def test_conflict_needs_two_different_claims() -> None:
    with pytest.raises(ValidationError, match="two different claims"):
        Conflict(prop_id="P1", claim_a="c1", claim_b="c1", kind=ConflictKind.DIRECT)


@pytest.mark.parametrize("year", [1500, 2200])
def test_paper_year_out_of_range_is_rejected(year: int) -> None:
    with pytest.raises(ValidationError):
        Paper(paper_id="p1", title="T", year=year)
