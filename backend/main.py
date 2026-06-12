"""FastAPI entrypoint for the hybrid agentic test engine.

Look here second, after `models.py`.

In Phase 2 this file is intentionally thin: the route accepts an intent, asks
Claude to generate steps, asks Playwright to execute them, and returns the
decision trace. The interesting behavior lives in the smaller modules this file
calls.
"""

from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.models import (
    PromotionCandidate,
    PromotionDecisionRequest,
    StepResult,
    TestIntent,
)
from backend.playwright_runner import PlaywrightRunError, run_steps
from backend.promotion import (
    PromotionError,
    approve_candidate,
    get_pending_candidates,
    get_promoted_steps,
    intent_hash,
    register_promotion_candidates,
    reject_candidate,
)
from backend.step_generator import StepGenerationError, generate_steps


app = FastAPI(
    title="Hybrid Agentic Test Engine",
    description="Phase 3 learning-loop prototype for the Testsigma EM take-home.",
    version="0.3.0",
)

# Phase 1 runs the React dev server on port 5173 and FastAPI on port 8000.
# CORS lets the browser call the backend during local development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    """Small smoke-test endpoint for checking that FastAPI is alive."""

    return {"status": "ok", "phase": "3-learning-loop"}


@app.post("/run-test", response_model=list[StepResult])
async def run_test(request: TestIntent) -> list[StepResult]:
    """Run the Phase 3 pipeline.

    The extra Phase 3 behavior is the learning loop: recovered rows are saved as
    pending promotion candidates, and approved candidates are used
    deterministically on later runs of the same intent.
    """

    try:
        run_id = f"run_{uuid4().hex[:8]}"
        intent_key = intent_hash(request.intent)
        steps = await generate_steps(request.intent)
        results = await run_steps(
            steps,
            execution_mode=request.execution_mode,
            promoted_steps=get_promoted_steps(intent_key),
        )
        return register_promotion_candidates(
            run_id=run_id,
            intent_key=intent_key,
            original_intent=request.intent,
            original_steps=steps,
            results=results,
        )
    except StepGenerationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except PromotionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except PlaywrightRunError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected Phase 3 execution error: {exc}",
        ) from exc


@app.get("/promotions", response_model=list[PromotionCandidate])
def list_promotions() -> list[PromotionCandidate]:
    """Return pending promotion candidates for the review panel."""

    return get_pending_candidates()


@app.post("/promote", response_model=PromotionCandidate)
def promote(request: PromotionDecisionRequest) -> PromotionCandidate:
    """Approve a recovered step so the next matching run uses it deterministically."""

    try:
        return approve_candidate(request.candidate_id)
    except PromotionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/reject-promotion", response_model=PromotionCandidate)
def reject_promotion(request: PromotionDecisionRequest) -> PromotionCandidate:
    """Reject a recovered step while keeping an audit trail."""

    try:
        return reject_candidate(request.candidate_id)
    except PromotionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
