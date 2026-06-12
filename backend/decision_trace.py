"""Helpers for building customer-readable decision trace rows."""

from backend.models import ModeUsed, StepResult, StepStatus, TestStep


def trace_row(
    *,
    step: TestStep,
    status: StepStatus,
    mode_used: ModeUsed,
    duration_ms: int,
    error: str | None = None,
    agent_action: str | None = None,
    agent_reasoning: str | None = None,
    customer_explanation: str | None = None,
    failed_step: TestStep | None = None,
    recovered_step: TestStep | None = None,
) -> StepResult:
    """Create the single object the UI renders as one decision-trace row."""

    return StepResult(
        step_id=step.step_id,
        description=step.description,
        status=status,
        mode_used=mode_used,
        error=error,
        agent_action=agent_action,
        agent_reasoning=agent_reasoning,
        customer_explanation=customer_explanation
        or _default_customer_explanation(status, mode_used),
        duration_ms=duration_ms,
        is_promotion_candidate=recovered_step is not None,
        failed_step=failed_step,
        recovered_step=recovered_step,
    )


def _default_customer_explanation(status: StepStatus, mode_used: ModeUsed) -> str:
    if status == "recovered" and mode_used == "ai_recovery":
        return "The deterministic selector failed, so AI recovered the intended action."

    if status == "failed":
        return "The step failed and could not be recovered automatically."

    return "The deterministic step completed successfully."
