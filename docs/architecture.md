# Architecture — Hybrid Agentic Test Engine

This prototype demonstrates the narrow but important product loop:

```text
Plain-English intent
  -> Claude generates deterministic TestStep[]
  -> Playwright executes the steps
  -> a controlled selector drift is injected for step_3
  -> Playwright fails on the drifted runtime selector
  -> Claude recovers from a compact interactive DOM snapshot
  -> human approves the recovered step
  -> next run uses the approved selector deterministically
```

## System Diagram

```text
┌────────────────────────────────────────────────────────────────────┐
│                         React Frontend                             │
│                                                                    │
│  IntentInput                                                       │
│    └─ user writes a plain-English test intent                      │
│                                                                    │
│  ExecutionTrace                                                    │
│    └─ shows per-step status, execution mode, timing, reasoning     │
│                                                                    │
│  PromotionPanel                                                    │
│    └─ human approves/rejects recovered selectors                   │
└───────────────────────────────┬────────────────────────────────────┘
                                │ HTTP
                                ▼
┌────────────────────────────────────────────────────────────────────┐
│                         FastAPI Backend                            │
│                                                                    │
│  POST /run-test                                                    │
│    ├─ step_generator.generate_steps()                              │
│    │    └─ Claude: intent -> TestStep[]                            │
│    │                                                               │
│    ├─ promotion.get_promoted_steps()                               │
│    │    └─ loads approved selectors for this intent hash           │
│    │                                                               │
│    ├─ playwright_runner.run_steps()                                │
│    │    ├─ deterministic Playwright execution                      │
│    │    ├─ failure_injector.apply_failure_injection()              │
│    │    ├─ ai_recovery.extract_interactive_dom()                   │
│    │    └─ ai_recovery.recover_step()                              │
│    │                                                               │
│    └─ promotion.register_promotion_candidates()                    │
│         └─ saves recovered rows for human review                   │
│                                                                    │
│  GET /promotions                                                   │
│    └─ returns pending promotion candidates                         │
│                                                                    │
│  POST /promote                                                     │
│    └─ approves one candidate and writes promoted_steps.json        │
│                                                                    │
│  POST /reject-promotion                                            │
│    └─ rejects one candidate while preserving audit history         │
└───────────────────────────────┬────────────────────────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────────┐
│                         Local Persistence                          │
│                                                                    │
│  backend/data/promotion_candidates.json                            │
│    └─ pending/approved/rejected recovery review records            │
│                                                                    │
│  backend/data/promoted_steps.json                                  │
│    └─ approved recovered selectors keyed by intent hash + step id  │
└────────────────────────────────────────────────────────────────────┘
```

## Runtime Data Flow

1. The frontend sends `TestIntent` to `POST /run-test`.
2. `backend/main.py` computes a stable `intent_hash`.
3. `backend/step_generator.py` asks Claude for structured `TestStep[]`.
4. `backend/promotion.py` loads approved promoted steps for the same intent.
5. `backend/playwright_runner.py` runs each step.
6. If no promoted step exists for `step_3`, `backend/failure_injector.py` replaces the runtime selector with a known-bad selector.
7. Playwright fails on the runtime selector.
8. `backend/ai_recovery.py` sends Claude the original step, failed runtime step, error, and compact DOM snapshot.
9. Claude returns a recovered selector/action plus technical and customer-readable reasoning.
10. The runner retries the recovered step.
11. `backend/decision_trace.py` builds `StepResult` rows for the UI.
12. `backend/promotion.py` stores recovered rows as pending promotion candidates.
13. The frontend shows the review panel.
14. Approval writes `promoted_steps.json`.
15. The next matching run uses the promoted step deterministically and skips drift injection for that step.

## Why The Prototype Is Honest

- The target site is real: `automationexercise.com`.
- Playwright execution is real.
- The failure is simulated, but isolated and documented in `failure_injector.py`.
- Claude recovery is real: the agent receives the failed selector and current DOM snapshot.
- Promotion persistence is real: approval writes local JSON, and the next run reads it.
- The trace is real product output, not console-only debugging.

## What Is Intentionally Not Production-Grade

- JSON files stand in for a database.
- Intent hashing is enough for a demo, but production would need test case IDs and versioning.
- There is no auth, tenancy, RBAC, or audit UI beyond local JSON.
- The DOM snapshot is compact but naive; production should score candidates and include DOM diffs.
- The job runs in the request path; production should use a queue and stream trace events.
