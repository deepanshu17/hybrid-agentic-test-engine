"""Shared data contracts for the backend.

Read this file first when trying to understand the project. Phase 1 is only a
stubbed spine, but these models are intentionally close to the final product so
Phase 2 can replace stubbed behavior without changing the API shape.
"""

from typing import Literal

from pydantic import BaseModel, Field


ExecutionMode = Literal[
    "deterministic",
    "deterministic_with_fallback",
    "agentic",
]

StepStatus = Literal["passed", "failed", "recovered"]
ModeUsed = Literal["deterministic", "ai_recovery", "agentic"]
PromotionStatus = Literal["pending", "approved", "rejected"]


class TestIntent(BaseModel):
    """Request body from the UI when the user starts a test run."""

    intent: str = Field(..., min_length=1)
    execution_mode: ExecutionMode = "deterministic_with_fallback"


class TestStep(BaseModel):
    """A single executable step.

    In Phase 1 these are only embedded in stub results. In Phase 2, Claude will
    generate this shape and Playwright will execute it directly.
    """

    step_id: str
    description: str
    action: str
    selector: str | None = None
    value: str | None = None
    url: str | None = None
    expected_outcome: str


class StepResult(BaseModel):
    """One row in the decision trace table.

    This object is deliberately UI-friendly: it carries engineering details
    (`agent_reasoning`) and customer-facing language (`customer_explanation`) in
    the same payload so the frontend can show both without extra calls.
    """

    step_id: str
    description: str
    status: StepStatus
    mode_used: ModeUsed
    error: str | None = None
    agent_action: str | None = None
    agent_reasoning: str | None = None
    customer_explanation: str | None = None
    duration_ms: int
    is_promotion_candidate: bool = False
    promotion_candidate_id: str | None = None
    failed_step: TestStep | None = None
    recovered_step: TestStep | None = None


class PromotionDecisionRequest(BaseModel):
    """Request body for approving or rejecting a promotion candidate."""

    candidate_id: str


class PromotionCandidate(BaseModel):
    """A recovered step waiting for human review.

    Phase 3 will persist this to disk and let the next run use approved
    recoveries deterministically.
    """

    candidate_id: str
    run_id: str
    intent_hash: str
    original_intent: str
    step_id: str
    original_step: TestStep
    failed_step: TestStep | None = None
    recovered_step: TestStep
    agent_reasoning: str
    status: PromotionStatus = "pending"
    approved_at: str | None = None
