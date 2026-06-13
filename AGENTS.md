# AGENTS.md — Hybrid Test Execution Engine

> Build plan for the Testsigma EM take-home. Each phase is a **self-contained, runnable module** that delivers value on its own. Never break the working state between phases.

---

## Project Structure (Final)

```
TestSigma/
│
├── backend/
│   ├── main.py                  # FastAPI app — routes, orchestration
│   ├── models.py                # Pydantic data contracts (TestIntent, TestStep, StepResult, PromotionCandidate)
│   ├── step_generator.py        # Phase 2 — Claude: plain English → steps JSON
│   ├── playwright_runner.py     # Phase 2 — deterministic Playwright execution
│   ├── failure_injector.py      # Phase 2 — controlled fake UI drift
│   ├── ai_recovery.py           # Phase 2 — Claude agent: recover failed step from DOM snapshot
│   ├── decision_trace.py        # Phase 2 — build per-step trace entries
│   ├── promotion.py             # Phase 3 — approve/reject recovery candidates
│   └── data/
│       └── promoted_steps.json  # Phase 3 — persisted learning loop state
│
├── frontend/
│   ├── index.html
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── api.ts               # All fetch calls to backend
│   │   └── components/
│   │       ├── IntentInput.tsx       # Phase 1 — text box + run button
│   │       ├── ExecutionTrace.tsx    # Phase 1 (stub) → Phase 2 (real)
│   │       └── PromotionPanel.tsx    # Phase 3 — approve/reject UI
│   └── package.json
│
├── docs/
│   └── leadership_document.md   # Phase 4 — Component B (6 sections)
│
├── .env.example                 # ANTHROPIC_API_KEY placeholder
├── README.md
├── solution.md
└── AGENTS.md                    ← this file
```

---

## Data Contracts (shared across all phases)

Defined in `backend/models.py`. All phases speak these shapes — do not skip this.

```python
# What the user sends in
class TestIntent(BaseModel):
    intent: str
    execution_mode: Literal["deterministic", "deterministic_with_fallback", "agentic"]

# What the LLM generates per step
class TestStep(BaseModel):
    step_id: str
    description: str
    action: str                  # "navigate" | "click" | "fill" | "assert"
    selector: str | None
    value: str | None            # for fill actions
    url: str | None              # for navigate actions
    expected_outcome: str

# What the execution engine returns per step
class StepResult(BaseModel):
    step_id: str
    description: str
    status: Literal["passed", "failed", "recovered"]
    mode_used: Literal["deterministic", "ai_recovery", "agentic"]
    error: str | None
    agent_action: str | None
    agent_reasoning: str | None
    customer_explanation: str | None
    duration_ms: int
    is_promotion_candidate: bool
    recovered_step: TestStep | None

# What gets surfaced for human review
class PromotionCandidate(BaseModel):
    candidate_id: str
    run_id: str
    step_id: str
    original_step: TestStep
    recovered_step: TestStep
    agent_reasoning: str
    status: Literal["pending", "approved", "rejected"]
    approved_at: str | None
```

---

## Phase 1 — The Spine

**Goal:** End-to-end pipe works. User types text, clicks Run, sees a table. Nothing is real — all stubs. But the full system can breathe.

**What gets built:**

| File | What it does |
|---|---|
| `backend/main.py` | FastAPI app with `POST /run-test` returning hardcoded `StepResult` list |
| `backend/models.py` | All four Pydantic models defined |
| `frontend/src/components/IntentInput.tsx` | Text box + execution mode dropdown + Run button |
| `frontend/src/components/ExecutionTrace.tsx` | Table rendering a list of `StepResult` (hardcoded for now) |
| `frontend/src/api.ts` | `runTest(intent)` — calls backend, returns `StepResult[]` |
| `frontend/src/App.tsx` | Wires `IntentInput` → `api.runTest` → `ExecutionTrace` |

**Done when:**
- [ ] `uvicorn backend.main:app` starts without error
- [ ] `npm run dev` starts frontend without error
- [ ] Submitting any text returns a hardcoded 3-row trace table in the UI
- [ ] CORS is configured; frontend and backend talk to each other

**Not in scope:** Real Claude calls, real Playwright, anything async.

---

## Phase 2 — Fill the Layers (Real Execution)

**Goal:** The full deterministic + AI recovery flow works end-to-end with real Claude calls and real Playwright against `automationexercise.com`. The spine from Phase 1 is replaced with real implementations one layer at a time.

**What gets built:**

| File | What it does |
|---|---|
| `backend/step_generator.py` | Claude API call — converts plain English intent → `TestStep[]` JSON |
| `backend/playwright_runner.py` | Executes each `TestStep` via Playwright; returns `StepResult` per step |
| `backend/failure_injector.py` | Intercepts step 3, replaces its selector with a known-bad one. Documented. |
| `backend/ai_recovery.py` | On failure: extracts DOM snapshot → calls Claude agent → returns recovered selector + reasoning |
| `backend/decision_trace.py` | Attaches `mode_used`, `agent_reasoning`, `customer_explanation`, `duration_ms` to each result |
| `backend/main.py` | Updated `POST /run-test` — orchestrates real pipeline instead of stubs |
| `frontend/src/components/ExecutionTrace.tsx` | Updated to show real status badges, mode labels, agent reasoning |

**Layer-by-layer fill order (do not skip):**
1. `step_generator.py` — test it standalone: `python -m backend.step_generator "search for a t-shirt"` → prints steps JSON
2. `playwright_runner.py` — test it standalone: `python -m backend.playwright_runner --mode deterministic_with_fallback` → confirm steps execute on the site
3. `failure_injector.py` — confirm step 3 reliably fails with the bad selector
4. `ai_recovery.py` — test it standalone: pass a failed step + DOM snapshot → confirm Claude returns a valid recovered selector
5. Wire all four into `main.py`
6. Update `ExecutionTrace.tsx` to show real data

**Done when:**
- [ ] Submitting "search for a t-shirt and add it to cart" produces a real trace
- [ ] Step 3 fails (logged as `status: "failed"`)
- [ ] AI recovery runs and step 3 shows `status: "recovered"` with agent reasoning
- [ ] Per-step trace shows `mode_used`, `duration_ms`, `customer_explanation`
- [ ] `is_promotion_candidate: true` is set on the recovered step

**Not in scope:** Promotion UI, persistence, polish.

---

## Phase 3 — The Learning Loop

**Goal:** The promotion flow works end-to-end. Human can review recovered steps, approve or reject, and the approval persists to `promoted_steps.json`. On the next run, the promoted selector is used instead of triggering AI recovery.

**What gets built:**

| File | What it does |
|---|---|
| `backend/promotion.py` | `approve(candidate_id)` → writes to `promoted_steps.json`; `reject(candidate_id)` → logs; `get_pending()` → list |
| `backend/data/promoted_steps.json` | Created on first approval. Keyed by intent hash. |
| `backend/main.py` | `POST /promote` — calls `promotion.approve()`; `GET /promotions` — returns pending candidates |
| `backend/playwright_runner.py` | Updated — checks `promoted_steps.json` before running a step; uses promoted selector if found |
| `frontend/src/components/PromotionPanel.tsx` | Shows recovered steps with Approve / Reject buttons; calls `POST /promote` |
| `frontend/src/App.tsx` | Updated — shows `PromotionPanel` below trace when candidates exist |

**Done when:**
- [ ] After a run with a recovery, `PromotionPanel` shows the recovered step
- [ ] Clicking Approve calls `POST /promote` and shows a confirmation
- [ ] `promoted_steps.json` is updated with the approved selector
- [ ] Running the same intent again uses the promoted selector — step 3 passes as `mode_used: "deterministic"`, no AI call

**Not in scope:** Leadership doc, visual polish.

---

## Phase 4 — Polish + Leadership Document

**Goal:** Demo-ready. Every piece works and is presentable. Component B (leadership document) is written.

**What gets built:**

| Deliverable | What it covers |
|---|---|
| Visual polish | Status badges (green/red/yellow), mode chips, collapsible reasoning rows, clean layout |
| `customer_explanation` visible | Shown inline in trace — non-technical language for every step |
| Architecture diagram | ASCII diagram in UI or a PNG in `/docs` |
| `.env.example` | Documents `ANTHROPIC_API_KEY` requirement |
| `docs/leadership_document.md` | Component B — all 6 sections (see below) |

**Leadership document sections:**
1. **Bug Diagnosis** — 3 known production bugs in the inherited v0, root cause + impact
2. **90-Day Plan** — 30 / 60 / 90 milestones with specific, measurable goals
3. **SLOs** — Latency, reliability, accuracy targets for all 3 execution modes
4. **Customer Trust Story** — How a CTO reads the decision trace and trusts the system
5. **Team Structure** — One team or two? Trade-offs argued explicitly
6. **Hardest Conversation** — What you'd tell the founding team that they don't want to hear

**Done when:**
- [ ] Full demo flow runs cleanly: intent → execution → recovery → promotion → re-run (deterministic)
- [ ] All trace fields visible and readable in UI
- [ ] Leadership document is 4–6 pages, all 6 sections complete
- [ ] `README.md` has setup instructions (how to run backend + frontend)

---

## Phase Completion Checklist

| Phase | Status | Exit condition |
|---|---|---|
| **Phase 1 — Spine** | `[x] Built` | UI ↔ backend pipe works with stub data |
| **Phase 2 — Real Execution** | `[x] Built` | Real trace with real recovery in UI |
| **Phase 3 — Learning Loop** | `[x] Built` | Approved promotion changes next run's behavior |
| **Phase 4 — Polish + Docs** | `[x] Built` | Demo-ready + leadership document complete |

---

## Key Rules for the Agent Building This

1. **Never break the working state.** Each phase starts from a working system and ends in a working system. No "we'll fix it in the next phase."
2. **Test each layer standalone before wiring.** `step_generator.py`, `ai_recovery.py`, and `playwright_runner.py` should all be testable with a `python file.py` one-liner before they touch `main.py`.
3. **Do not mock the recovery.** The Claude agent recovery must be real. If it is mocked, the assignment fails.
4. **Do not skip models.py.** All four Pydantic models must be defined before Phase 2 begins. They are the contract everything else builds against.
5. **Commit at the end of each phase.** Each phase is a clean git commit so the progression is visible.
