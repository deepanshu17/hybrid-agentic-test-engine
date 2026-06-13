## The Core Concept: Hybrid Test Execution

The system must support **three execution modes**:


| Mode                            | What it means                                                                  |
| ------------------------------- | ------------------------------------------------------------------------------ |
| **Deterministic**               | Classic Playwright — click selector, assert result. Fast, cheap.               |
| **Deterministic + AI Fallback** | Runs deterministically, fails on UI drift → AI agent recovers → learning loop. |
| **Agentic Primary**             | AI agent drives the whole flow from a plain-English intent.                    |


The **learning loop** is the crown jewel: agent recovers a failed step → human reviews → approves promotion → next run is deterministic again.

---

## Two Deliverables

### Component A — Working Prototype

Five things it must do end-to-end:

1. Accept a plain-English test intent → LLM converts it to structured steps
2. Run those steps deterministically via Playwright
3. Force one step to fail (fake UI drift) → AI agent recovers
4. Show the **"promotion candidate"** — human approves the agent's recovery back into the script
5. Show a **per-step decision trace** (which mode, what the agent did, why)

### Component B — Leadership Document (4–6 pages, 6 sections)

1. Diagnosis of what's broken in the inherited v0 (3 known bugs)
2. 90-day plan (30 / 60 / 90 with specific goals)
3. SLOs for all 3 execution modes (latency + reliability + accuracy)
4. Customer-facing story (how does a CTO trust what the agent did?)
5. Team structure (one team or two? trade-offs)
6. Hardest conversation you'd have with the founding team

---

## One-Day Minimal Viable Prototype

### The 4-layer flow (all required, but can be thin)

```
[UI text box]  →  LLM (Claude)  →  structured steps JSON
                                          ↓
                          [Playwright runs steps]  →  one step intentionally fails
                                          ↓
                          [LLM agent recovers]  →  finds the right selector/action
                                          ↓
                          [UI shows recovery]  →  "Promote to deterministic?" button
                                          ↓
                          [Decision trace]  →  per-step table: mode, action, reason
```

### Minimal Tech Stack


| Layer             | Choice                       | Notes                               |
| ----------------- | ---------------------------- | ----------------------------------- |
| **Frontend**      | React (or plain HTML)        | Text box, Run button, results table |
| **Backend**       | FastAPI (Python)             | REST API for test execution         |
| **Execution**     | Playwright (Python)          | Against any public demo site        |
| **LLM**           | Claude API                   | Step generation + agent recovery    |
| **Fake UI drift** | Hardcoded wrong CSS selector | One step that is designed to fail   |


**Target app:** Any public site with a login + simple flow (e.g. `demo.playwright.dev`, `automationexercise.com`)

---

## What Can Be Faked / Stubbed Honestly


| Allowed to stub                               | Cannot fake                                                  |
| --------------------------------------------- | ------------------------------------------------------------ |
| Target app (any public site)                  | Actual fallback detection and recovery (must be real)        |
| Neo4j / knowledge graph (explicitly excluded) | The promotion flow (must update something, even a JSON file) |
| Polish and elaborate UI                       | The decision trace (must show per-step mode + reasoning)     |


> "A working three-step flow beats an elaborate UI with faked fallback." — assignment brief

---

## Evaluation Priority (High → Low)

1. **Fallback + recovery is real** — if faked, instant fail
2. **Decision trace** — differentiates senior-engineer thinking
3. **Leadership document** — especially SLO reasoning and the "hardest conversation" section
4. **Learning loop** — promotion candidate UI shows you understood the product vision
5. **Architecture diagram** — how you think about system design

---

## Final Problem Statement

> Build a minimal but honest prototype of a **hybrid test execution engine** where:
>
> 1. A user describes a test in plain English
> 2. An LLM converts it to structured Playwright steps and runs them
> 3. One step intentionally fails due to simulated UI drift, triggering an AI agent that recovers the intent and continues
> 4. The agent's recovery is surfaced as a human-reviewable **"promotion candidate"** that, when approved, updates the deterministic script
> 5. Every step shows a **decision trace** (mode used, agent reasoning, customer-readable explanation)
>
> Alongside this, write a 4–6 page leadership document diagnosing 3 known production bugs, proposing a 90-day fix plan with SLOs, and demonstrating you can have the hard conversations a founding team needs to hear early.

**The core question:** *Can you both build the hardest part of an AI-native product AND lead the team that owns it?*

---

## Run The Prototype

The current build is **Phase 4 / demo-ready**: React calls FastAPI, Claude generates
structured steps, Playwright executes them, one selector is intentionally
drifted, Claude attempts real AI recovery from a DOM snapshot, and a human can
approve the recovery so the next run uses it deterministically.

### Backend

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
python -m playwright install chromium
export ANTHROPIC_API_KEY="your_key_here"
uvicorn backend.main:app --reload
```

Backend health check:

```bash
curl http://localhost:8000/health
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`, submit the default intent, and confirm the UI
shows a real decision trace plus a promotion candidate after AI recovery.

Recommended test intent:

```text
Search for a t-shirt and add the first result to the cart.
```

### Demo Flow

1. Run the recommended intent once.
2. Confirm one row is marked as a promotion candidate.
3. Approve the candidate in the Promotion Panel.
4. Run the same intent again.
5. Confirm the approved step runs deterministically instead of triggering AI recovery.

The approval writes to `backend/data/promoted_steps.json`.

To reset the demo and show the learning loop again:

```bash
rm -f backend/data/promotion_candidates.json backend/data/promoted_steps.json
```

Refresh the UI and run the same intent again.

### Phase 4 Docs

- `docs/architecture.md` — system diagram, runtime flow, and production gaps.
- `docs/leadership_document.md` — Component B leadership document with all 6 required sections.

### Standalone Checks

Run these from the repository root after installing backend dependencies:

```bash
source .venv/bin/activate
python -m backend.step_generator "Search for a t-shirt and add the first result to the cart."
python -m backend.playwright_runner --mode deterministic_with_fallback
```

### Where To Read First

1. `backend/models.py` — the shared data contracts.
2. `backend/main.py` — the `/run-test` orchestration route.
3. `backend/step_generator.py` — Claude intent-to-steps translation.
4. `backend/failure_injector.py` — the documented fake UI drift.
5. `backend/ai_recovery.py` — Claude selector recovery from DOM snapshot.
6. `backend/playwright_runner.py` — deterministic execution + AI fallback.
7. `backend/promotion.py` — pending candidates and approved promoted steps.
8. `docs/architecture.md` — the system map for walkthroughs.
9. `docs/leadership_document.md` — the EM-level written component.
10. `frontend/src/App.tsx` — the frontend flow from intent to trace to review.
11. `frontend/src/components/ExecutionTrace.tsx` — how the decision trace is rendered.
12. `frontend/src/components/PromotionPanel.tsx` — human approval/rejection UI.

---

## Planned Project Structure

```
TestSigma/
├── backend/
│   ├── main.py                  # FastAPI app — orchestrates all execution modes
│   ├── step_generator.py        # Claude: plain-English → structured steps JSON
│   ├── playwright_runner.py     # Deterministic Playwright execution
│   ├── ai_recovery.py           # Claude agent: recover from failed step
│   ├── promotion.py             # Promotion candidate: approve → update script
│   ├── decision_trace.py        # Per-step trace builder
│   └── promoted_steps.json      # Persisted approved recoveries (source of truth)
├── frontend/
│   ├── index.html               # Entry point
│   ├── App.tsx                  # Main React app
│   └── components/
│       ├── IntentInput.tsx      # Plain-English text box + Run button
│       ├── ExecutionTrace.tsx   # Per-step decision trace table
│       └── PromotionPanel.tsx   # "Promote to deterministic?" review UI
├── docs/
│   ├── architecture.md         # System diagram and runtime flow
│   └── leadership_document.md  # Component B — 4–6 page leadership doc
└── README.md
```

