# Solution Approach — Hybrid Test Execution Engine

> This document explains how to think through and build this system the way it would actually happen at a real company — not just what to code, but *how to reason about it*.

---

## Step 0: Understand the Real Problem Before Writing Code

Before any code, ask: **what is the system fundamentally doing?**

This is a **state machine with an escape hatch**.

```
Normal path:  Intent → Steps → Playwright (deterministic) → Pass ✓

Escape hatch: Intent → Steps → Playwright → FAIL → AI Recovery → Continue
                                                           ↓
                                                   Human reviews recovery
                                                           ↓
                                                   Approve → update deterministic script
                                                   (next run: normal path again, no AI needed)
```

The "learning loop" is just this: the escape hatch eventually closes itself. The system gets smarter every time a human approves a recovery. That's the whole product vision in one sentence.

Once you see it as a state machine, the architecture becomes obvious: you need something that can **pause mid-execution**, **hand off to an agent**, **resume**, and **record what happened at each step**.

---

## Step 1: Define the Data Contracts First (not the UI, not the DB)

In real companies, the first thing a senior engineer does before writing any implementation is define the **data shapes** that flow between layers. This is the API contract — if you do this right, frontend and backend can develop in parallel and integration is smooth.

### The three key data structures:

**1. `TestIntent` — what comes in**

```json
{
  "intent": "Go to automationexercise.com, search for a t-shirt, and add the first result to cart",
  "execution_mode": "deterministic_with_fallback"
}
```

**2. `TestStep` — what the LLM generates**

```json
{
  "step_id": "step_3",
  "description": "Click the first search result",
  "action": "click",
  "selector": "#search-results .product-item:first-child",
  "expected_outcome": "Product detail page loads",
  "mode": "deterministic"
}
```

**3. `StepResult` — what the execution engine produces**

```json
{
  "step_id": "step_3",
  "status": "failed | recovered | passed",
  "mode_used": "deterministic | ai_recovery | agentic",
  "error": "Element not found: #search-results .product-item:first-child",
  "agent_action": "Found alternative selector: .productinfo h2",
  "agent_reasoning": "The original selector targeted a CSS class that no longer exists in the DOM. Located the product title element using a more semantic selector.",
  "customer_explanation": "The page layout changed. The AI found the same element using a different path and continued the test.",
  "duration_ms": 1240,
  "is_promotion_candidate": true,
  "recovered_step": { ...updated TestStep with new selector... }
}
```

**4. `PromotionCandidate` — what the human reviews**

```json
{
  "candidate_id": "promo_abc123",
  "run_id": "run_xyz",
  "step_id": "step_3",
  "original_step": { ...original TestStep... },
  "recovered_step": { ...recovered TestStep... },
  "agent_reasoning": "...",
  "status": "pending | approved | rejected",
  "approved_at": null
}
```

Why do this first? Because every layer — the LLM prompts, the Playwright runner, the recovery agent, the UI — is just transforming data from one of these shapes to another. Once the shapes are clear, every component's job is obvious.

---

## Step 2: Build the Spine, Not the Features

In real companies, a common mistake is building features before the spine. The spine is the **end-to-end flow with stubs** — get data flowing through every layer first, even if each layer does almost nothing.

### Build order: Spine first

```
Day 1 morning: Make the pipe work
  1. FastAPI endpoint: POST /run-test → returns a hardcoded StepResult list
  2. React UI: text box + button → calls that endpoint → shows the results list
  3. Confirm: you can submit text and see a table. Nothing is real yet.

Day 1 afternoon: Fill in each layer, bottom-up
  4. Claude step generation (real): plain English → structured steps JSON
  5. Playwright runner (real): execute steps against a site
  6. Inject the fake failure: hardcode step 3 selector as wrong
  7. AI recovery (real): on failure, call Claude agent with DOM snapshot → get new selector
  8. Decision trace: attach metadata to every step result
  9. Promotion UI: show recovered steps with Approve button
  10. Promotion persistence: Approve → write to promoted_steps.json
```

This order matters. At every point you have a working system — it just has stubs. You never have a broken system waiting for three things to be done simultaneously.

---

## Step 3: The Hardest Part — The AI Recovery Agent

This is the piece they will scrutinize most. Here's how to think about it.

### What the agent actually needs to do:

When a Playwright step fails, the agent needs to answer: **"Given that I wanted to `{action}` on `{original_selector}`, but that element doesn't exist, what should I do instead?"**

To answer this, the agent needs **context**:

1. What was the intended action and why (from the original step)
2. What does the current DOM look like (a snapshot — serialized as accessible text or simplified HTML)
3. What elements are available near the target area

### The recovery prompt (this is the real engineering work):

```
You are a test recovery agent. A Playwright test step has failed because the target element was not found.

ORIGINAL INTENT:
Action: {action}  (e.g. "click")
Target description: {description}  (e.g. "Click the first search result")
Original selector: {selector}  (e.g. "#search-results .product-item:first-child")
Expected outcome: {expected_outcome}

CURRENT DOM SNAPSHOT (simplified):
{dom_snapshot}

Your job:
1. Identify the element in the current DOM that best matches the original intent
2. Return the new selector
3. Explain your reasoning in two parts:
   - Technical: what changed and why your new selector works
   - Customer-facing: a one-sentence explanation a non-technical CTO can read

Return JSON only:
{
  "recovered_selector": "...",
  "recovered_action": "...",
  "technical_reasoning": "...",
  "customer_explanation": "..."
}
```

### The DOM snapshot problem:

You can't send the full HTML — it's too large and noisy for the LLM. In real companies this is solved by extracting only **interactive elements** from the page:

```python
# In Playwright, extract only the elements that matter
await page.evaluate("""
  () => Array.from(document.querySelectorAll(
    'a, button, input, select, [role="button"], [onclick]'
  )).map(el => ({
    tag: el.tagName,
    text: el.innerText?.trim().slice(0, 100),
    id: el.id,
    classes: el.className,
    href: el.href,
    type: el.type
  }))
""")
```

This gives the agent a focused, token-efficient view of what's actually actionable on the page.

---

## Step 4: The Decision Trace — Think Like a Debugger

Every step needs a trace entry. The trace is not an afterthought — it's the primary artifact of the system. Think of it like a structured log that is also a UI component.

### What makes a good trace:


| Field                     | For whom                        | Example                                                                            |
| ------------------------- | ------------------------------- | ---------------------------------------------------------------------------------- |
| Step number + description | Everyone                        | "Step 3: Click first search result"                                                |
| Mode used                 | Engineer                        | `deterministic` / `ai_recovery` / `agentic`                                        |
| Status                    | Everyone                        | `passed` / `failed` / `recovered`                                                  |
| Duration                  | Engineer                        | `240ms`                                                                            |
| Agent reasoning           | Engineer reviewing the recovery | "CSS class `.product-item` was renamed to `.product-card` after a frontend deploy" |
| Customer explanation      | CTO / non-technical stakeholder | "The page changed slightly. The AI adapted automatically and the test continued."  |
| Promotion badge           | Human reviewer                  | "⚠ Recovery — review and promote?"                                                 |


The key insight: **one trace, two audiences**. Engineers see the technical reasoning. Customers see the plain-English explanation. The same data object serves both.

---

## Step 5: The Promotion Flow — The Learning Loop Made Concrete

This is conceptually simple but needs to be implemented carefully because it's the part that makes the system feel real.

### What happens when a human clicks "Approve":

```
1. Frontend: POST /promote  { candidate_id: "promo_abc123" }
2. Backend:
   a. Load promoted_steps.json
   b. Find the original test intent
   c. Replace the failed step with the recovered step
   d. Write back to promoted_steps.json
   e. Mark the candidate as "approved"
3. Frontend: Show "✓ Promoted — next run will use deterministic selector"
```

### What `promoted_steps.json` looks like:

```json
{
  "intent_hash": "sha256_of_original_intent",
  "original_intent": "Search for t-shirt and add to cart",
  "steps": [
    { "step_id": "step_1", ... },
    { "step_id": "step_2", ... },
    {
      "step_id": "step_3",
      "selector": ".product-card:first-child",  ← updated by agent recovery
      "promoted_at": "2026-06-11T09:41:00Z",
      "promoted_from": "ai_recovery",
      "original_selector": "#search-results .product-item:first-child"
    }
  ]
}
```

On the next run, the backend checks `promoted_steps.json` first. If a promoted version of this step exists, it uses that selector — no AI needed. That is the learning loop.

---

## Step 6: The Target Site and the Fake Failure

Pick a site that is **stable, public, and has a simple flow**. `automationexercise.com` works well — it has login, search, and cart.

### How to inject the fake failure properly:

Do not randomly break things. Inject the failure in a **controlled, documented way**:

```python
INJECTED_FAILURES = {
    "step_3": {
        "reason": "Simulated UI drift: CSS class renamed after frontend deploy",
        "bad_selector": "#search-results .product-item:first-child",  # wrong — forces failure
    }
}

async def run_step(page, step):
    if step.step_id in INJECTED_FAILURES:
        # Override the selector to simulate what would happen after a UI change
        step.selector = INJECTED_FAILURES[step.step_id]["bad_selector"]
    ...
```

This is honest: the code clearly documents what is simulated and why. In the live walkthrough, you can point to this exact code and explain the reasoning.

---

## Step 7: Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND (React)                        │
│  [Intent Input]  →  [Run Button]  →  [Decision Trace Table]     │
│                                  →  [Promotion Panel]           │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTP (REST)
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      BACKEND (FastAPI)                          │
│                                                                 │
│   POST /run-test                                                │
│   ┌──────────────┐   ┌──────────────────┐   ┌───────────────┐  │
│   │ Step         │   │ Playwright       │   │ AI Recovery   │  │
│   │ Generator    │──▶│ Runner           │──▶│ Agent         │  │
│   │ (Claude API) │   │ (deterministic)  │   │ (Claude API)  │  │
│   └──────────────┘   └──────────────────┘   └───────────────┘  │
│                              │                       │          │
│                              ▼                       ▼          │
│                      ┌───────────────────────────────────────┐  │
│                      │        Decision Trace Builder         │  │
│                      └───────────────────────────────────────┘  │
│                                                                 │
│   POST /promote                                                 │
│   ┌─────────────────────────────────────────────────────────┐  │
│   │  Promotion Service  →  promoted_steps.json              │  │
│   └─────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
                  ┌──────────────────────┐
                  │  automationexercise  │
                  │  .com (target site)  │
                  └──────────────────────┘
```

---

## Step 8: What a Real Company Would Do Next (Beyond the MVP)

This is important to understand because the leadership document asks about the 90-day plan. The MVP proves the concept — what comes after is where the real engineering begins.


| After MVP                | Real implementation                                                                      |
| ------------------------ | ---------------------------------------------------------------------------------------- |
| `promoted_steps.json`    | A proper database (Postgres) with versioning, rollback, and audit trail                  |
| One target site          | Multi-tenant: each customer registers their own app URL and auth credentials             |
| DOM snapshot via JS eval | A proper DOM diffing engine that detects what changed between runs                       |
| Claude recovery prompt   | Fine-tuned model on historical recovery successes/failures                               |
| Manual promotion UI      | Suggested promotions with confidence scores; auto-promote above threshold                |
| Single FastAPI process   | Job queue (Celery/Redis) for long-running tests; WebSocket for real-time trace streaming |
| No authentication        | Auth, org isolation, RBAC                                                                |


The MVP is one engineer in one day. The real product is 6 months and a team of 4–5.

---

## How to Walk Through This in the Live Interview

The 60-minute walkthrough will probe three things:

1. **"Walk me through the recovery flow"** — Open `ai_recovery.py`, show the prompt, show the DOM snapshot extraction, show what Claude returns. Explain the token efficiency decision.
2. **"What happens when the agent gets it wrong?"** — Show the rejection path in the promotion UI. Explain that rejected recoveries are logged and can be used to improve the prompt. This shows you've thought about the feedback loop.
3. **"How does this scale?"** — Answer with the table above. Show you understand the gap between prototype and production. This is where EM thinking shines — you're not just showing what you built, you're showing you know exactly where the bodies are buried.

---

## Summary: The Build Order in One View

```
Phase 1 — Spine (get data flowing, nothing real yet)
  □ FastAPI skeleton with stub endpoint
  □ React UI: text box + run button + results table (hardcoded data)
  □ Confirm end-to-end pipe works

Phase 2 — Fill in the layers (bottom-up)
  □ Claude step generation: plain English → steps JSON
  □ Playwright runner: execute steps against automationexercise.com
  □ Inject fake failure in step 3
  □ AI recovery agent: failed step + DOM snapshot → recovered selector
  □ Decision trace: attach metadata to every step

Phase 3 — The learning loop
  □ Promotion panel UI: show recovered steps, Approve/Reject buttons
  □ POST /promote endpoint → write to promoted_steps.json
  □ On next run: check promoted_steps.json first

Phase 4 — Polish enough to demo confidently
  □ Per-step status indicators (passed / failed / recovered)
  □ Customer-readable explanations visible in trace
  □ Architecture diagram (even hand-drawn is fine)
  □ Leadership document (Component B)
```

