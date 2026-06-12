"""Human-in-the-loop promotion persistence.

Read this after `playwright_runner.py` for Phase 3.

The learning loop is deliberately implemented with JSON files for the take-home:
small enough to inspect in a walkthrough, but real enough that approving a
candidate changes the next run's deterministic behavior.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from backend.models import PromotionCandidate, StepResult, TestStep


DATA_DIR = Path(__file__).parent / "data"
CANDIDATES_FILE = DATA_DIR / "promotion_candidates.json"
PROMOTED_STEPS_FILE = DATA_DIR / "promoted_steps.json"


class PromotionError(RuntimeError):
    """Raised when a promotion candidate cannot be found or updated."""


def intent_hash(intent: str) -> str:
    """Stable key for connecting an intent to its approved deterministic steps."""

    normalized = " ".join(intent.lower().strip().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _read_json(path: Path, default: dict) -> dict:
    if not path.exists():
        return default

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _write_json(path: Path, payload: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(".tmp")
    with temp_path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2)
        file.write("\n")
    temp_path.replace(path)


def get_promoted_steps(intent_key: str) -> dict[str, TestStep]:
    """Return approved recovered steps for an intent, keyed by `step_id`."""

    payload = _read_json(PROMOTED_STEPS_FILE, default={})
    intent_record = payload.get(intent_key, {})
    raw_steps = intent_record.get("steps", {})
    return {
        step_id: TestStep.model_validate(step_payload)
        for step_id, step_payload in raw_steps.items()
    }


def register_promotion_candidates(
    *,
    run_id: str,
    intent_key: str,
    original_intent: str,
    original_steps: list[TestStep],
    results: list[StepResult],
) -> list[StepResult]:
    """Persist pending candidates for recovered rows and attach ids to results."""

    steps_by_id = {step.step_id: step for step in original_steps}
    candidates_payload = _read_json(CANDIDATES_FILE, default={})
    updated_results: list[StepResult] = []

    for result in results:
        if not result.is_promotion_candidate or not result.recovered_step:
            updated_results.append(result)
            continue

        original_step = steps_by_id.get(result.step_id)
        if not original_step:
            updated_results.append(result)
            continue

        candidate_id = f"promo_{uuid4().hex[:10]}"
        candidate = PromotionCandidate(
            candidate_id=candidate_id,
            run_id=run_id,
            intent_hash=intent_key,
            original_intent=original_intent,
            step_id=result.step_id,
            original_step=original_step,
            failed_step=result.failed_step,
            recovered_step=result.recovered_step,
            agent_reasoning=result.agent_reasoning or "No agent reasoning recorded.",
            status="pending",
        )
        candidate_record = candidate.model_dump()
        candidate_record["created_at"] = _now_iso()
        candidates_payload[candidate_id] = candidate_record
        updated_results.append(
            result.model_copy(update={"promotion_candidate_id": candidate_id})
        )

    _write_json(CANDIDATES_FILE, candidates_payload)
    return updated_results


def get_pending_candidates() -> list[PromotionCandidate]:
    """Return pending candidates for the review panel."""

    payload = _read_json(CANDIDATES_FILE, default={})
    return [
        PromotionCandidate.model_validate(record)
        for record in payload.values()
        if record.get("status") == "pending"
    ]


def approve_candidate(candidate_id: str) -> PromotionCandidate:
    """Approve a candidate and write its recovered step to `promoted_steps.json`."""

    candidates_payload = _read_json(CANDIDATES_FILE, default={})
    candidate_record = candidates_payload.get(candidate_id)
    if not candidate_record:
        raise PromotionError(f"Promotion candidate not found: {candidate_id}")

    candidate = PromotionCandidate.model_validate(candidate_record)
    if candidate.status != "pending":
        raise PromotionError(
            f"Promotion candidate {candidate_id} is already {candidate.status}."
        )

    promoted_payload = _read_json(PROMOTED_STEPS_FILE, default={})
    intent_record = promoted_payload.setdefault(
        candidate.intent_hash,
        {
            "original_intent": candidate.original_intent,
            "steps": {},
        },
    )
    intent_record["steps"][candidate.step_id] = {
        **candidate.recovered_step.model_dump(),
        "promoted_at": _now_iso(),
        "promoted_from": "ai_recovery",
        "original_selector": candidate.original_step.selector,
        "failed_runtime_selector": (
            candidate.failed_step.selector if candidate.failed_step else None
        ),
    }

    candidate_record["status"] = "approved"
    candidate_record["approved_at"] = _now_iso()
    candidates_payload[candidate_id] = candidate_record

    _write_json(PROMOTED_STEPS_FILE, promoted_payload)
    _write_json(CANDIDATES_FILE, candidates_payload)
    return PromotionCandidate.model_validate(candidate_record)


def reject_candidate(candidate_id: str) -> PromotionCandidate:
    """Reject a candidate while keeping the audit trail in JSON."""

    candidates_payload = _read_json(CANDIDATES_FILE, default={})
    candidate_record = candidates_payload.get(candidate_id)
    if not candidate_record:
        raise PromotionError(f"Promotion candidate not found: {candidate_id}")

    candidate = PromotionCandidate.model_validate(candidate_record)
    if candidate.status != "pending":
        raise PromotionError(
            f"Promotion candidate {candidate_id} is already {candidate.status}."
        )

    candidate_record["status"] = "rejected"
    candidate_record["approved_at"] = None
    candidate_record["rejected_at"] = _now_iso()
    candidates_payload[candidate_id] = candidate_record
    _write_json(CANDIDATES_FILE, candidates_payload)
    return PromotionCandidate.model_validate(candidate_record)
