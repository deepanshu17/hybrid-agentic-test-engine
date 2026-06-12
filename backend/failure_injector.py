"""Controlled UI-drift simulation for Phase 2.

The assignment asks us to force one deterministic step to fail. This module
makes that failure explicit and reviewable instead of hiding it inside the
runner. In a walkthrough, this is the file to open when asked, "Where is the
fake drift?"
"""

from dataclasses import dataclass

from backend.models import TestStep


@dataclass(frozen=True)
class InjectedFailure:
    step_id: str
    bad_selector: str
    reason: str


INJECTED_FAILURES: dict[str, InjectedFailure] = {
    "step_3": InjectedFailure(
        step_id="step_3",
        bad_selector="#submit_search_after_ui_drift",
        reason=(
            "Simulated UI drift: the search button selector changed after a "
            "frontend deploy."
        ),
    )
}


def apply_failure_injection(step: TestStep) -> tuple[TestStep, InjectedFailure | None]:
    """Return a copy of `step` with a known-bad selector when drift is enabled."""

    injected = INJECTED_FAILURES.get(step.step_id)
    if not injected or not step.selector:
        return step, None

    drifted_step = step.model_copy(update={"selector": injected.bad_selector})
    return drifted_step, injected
