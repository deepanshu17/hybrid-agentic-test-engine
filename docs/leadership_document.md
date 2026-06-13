# Leadership Document — Hybrid Test Execution Engine

## Executive Summary

The inherited v0 appears to have the right ambition but the wrong operating model: it tries to make AI feel magical before making execution observable, recoverable, and accountable. For enterprise test automation, the trust boundary is not "did the AI pass the test?" The trust boundary is "can a customer understand what changed, why the system acted, and how that behavior becomes deterministic again?"

The prototype demonstrates the core product loop I would prioritize: deterministic execution first, AI recovery only when needed, human approval before promotion, and a per-step decision trace that explains every choice. The leadership plan below turns that loop into a production system with reliability targets, customer trust artifacts, and a team structure that can deliver both platform quality and AI velocity.

---

## 1. Diagnosis: What Is Broken In The Inherited v0

### Bug 1: Agent Recovery Is Not Auditable

**Observed failure mode:** The agent can recover a failed step, but the system does not record enough context to explain the recovery later. A user may see a passing test without knowing whether it passed deterministically, passed through AI intervention, or passed because the agent clicked a nearby but incorrect element.

**Root cause:** The execution engine treats agent behavior as a black-box fallback instead of a first-class execution mode. The trace lacks structured fields for original step, failed runtime selector, recovered selector, agent reasoning, and customer-readable explanation.

**Customer impact:** Enterprise buyers cannot trust the system for release gating. A CTO or QA leader needs to know not only that a test passed, but whether the pass was deterministic, recovered, or uncertain.

**Fix direction:** Every step must produce a decision trace. Recovery must create a reviewable promotion candidate with original, failed, and recovered step data.

### Bug 2: Recovery Does Not Close The Learning Loop

**Observed failure mode:** The same UI drift can trigger the same agent recovery repeatedly. That makes the system slower, more expensive, and less predictable over time.

**Root cause:** The system recovers at runtime but does not promote successful recoveries back into the deterministic script after human review.

**Customer impact:** Customers pay repeated latency and token costs for a problem already solved once. Worse, they start to see the agent as a permanent crutch instead of a path back to stable automation.

**Fix direction:** Recovery should create a pending promotion candidate. Approval should update the deterministic source of truth. The next run should use the approved selector without invoking AI.

### Bug 3: Execution Modes Are Not Separated Operationally

**Observed failure mode:** Deterministic execution, deterministic-plus-fallback, and agentic execution are blurred together. That makes it hard to reason about reliability, latency, cost, and correctness.

**Root cause:** The system lacks explicit mode contracts and SLOs. "AI ran the test" is treated as a product feature, but not as an operational category with different failure modes.

**Customer impact:** Support and engineering cannot answer basic production questions: which mode failed, whether the failure was selector drift or agent error, and what the user should trust.

**Fix direction:** Define execution modes as separate products inside the platform. Each needs its own metrics, SLOs, customer messaging, and escalation path.

---

## 2. 90-Day Plan

### First 30 Days: Stabilize The Core Loop

**Goal:** Make deterministic execution and AI fallback observable, reviewable, and demo-safe.

Milestones:

- Ship structured data contracts for `TestIntent`, `TestStep`, `StepResult`, and `PromotionCandidate`.
- Add per-step decision traces for every run.
- Implement controlled AI recovery from a compact DOM snapshot.
- Add human approval/rejection for promotion candidates.
- Persist approved recoveries and use them on the next run.
- Add a minimal trace UI that shows mode, status, timing, agent reasoning, and customer explanation.

Success metrics:

- 100% of executed steps produce trace rows.
- 100% of AI recoveries produce promotion candidates.
- Approved recoveries are reused deterministically on the next matching run.
- Support can inspect a run without reading backend logs.

### Days 31-60: Make It Reliable And Measurable

**Goal:** Move from prototype behavior to production-grade reliability signals.

Milestones:

- Replace JSON persistence with Postgres tables for runs, steps, candidates, approvals, and audit events.
- Add run IDs, test case IDs, versioning, and rollback for promoted steps.
- Add confidence scoring for recovery candidates.
- Add retry policy for infrastructure failures, but not for semantic agent failures.
- Add browser/session isolation and artifact capture: screenshots, DOM snapshots, console logs, and network errors.
- Add dashboards for latency, recovery rate, approval rate, and false recovery rate.

Success metrics:

- 95% of deterministic runs complete within target latency.
- Recovery candidates include all review artifacts.
- Rejected candidates are tracked and reviewed weekly.
- No approved promotion is applied without audit history.

### Days 61-90: Productize For Enterprise Trust

**Goal:** Make the system credible for release-gating customers.

Milestones:

- Add organization-level configuration for allowed recovery policies.
- Add RBAC for who can approve promotions.
- Add customer-facing run reports.
- Add side-by-side diff view for failed and recovered selectors.
- Add a queue-based execution service and stream trace updates to the UI.
- Define escalation paths for unsafe recoveries, flaky sites, and repeated agent failures.

Success metrics:

- Customers can export a run report that explains every AI action.
- Promotion approvals are tied to named users and timestamps.
- Deterministic mode remains the default for release gates.
- Agentic primary mode is clearly labeled as exploratory/non-gating unless configured otherwise.

---

## 3. SLOs For The Three Execution Modes

### Deterministic Mode

Purpose: Fast, cheap, reliable execution for stable test scripts.

Targets:

- **Latency:** p95 step latency under 1 second, excluding page load time.
- **Run reliability:** 99% infrastructure success for healthy target apps.
- **Accuracy:** 99.5% selector/action correctness for approved deterministic steps.
- **Cost:** no LLM call during normal execution.

Why this matters: Deterministic mode is the release-gating foundation. It must remain boring and predictable.

### Deterministic + AI Fallback

Purpose: Recover from UI drift while preserving a path back to deterministic execution.

Targets:

- **Latency:** p95 recovered step under 15 seconds.
- **Recovery success:** 80%+ successful recovery for simple selector drift.
- **Approval precision:** 95%+ of approved promotions should pass on the next run.
- **False recovery rate:** below 2% for approved candidates.
- **Trace completeness:** 100% of recovery attempts include original step, failed runtime step, recovered step, and reasoning.

Why this matters: This is the product wedge. It gives customers resilience without asking them to blindly trust autonomous agents.

### Agentic Primary Mode

Purpose: Explore or execute tests from high-level intent when deterministic scripts do not exist yet.

Targets:

- **Latency:** p95 run planning under 30 seconds for short flows.
- **Task completion:** 70%+ completion on supported app patterns.
- **Human review requirement:** 100% of generated durable steps require review before becoming release-gating assets.
- **Safety:** no destructive actions unless explicitly allowed by policy.

Why this matters: Agentic primary is powerful but least predictable. It should be framed as authoring/exploration first, not as the default release gate.

---

## 4. Customer-Facing Trust Story

The trust story should be simple enough for a CTO and detailed enough for a QA lead.

Customer-facing explanation:

> "Your test normally runs deterministically. If the UI changes and a selector breaks, the system can use AI to recover the intended action. That recovery is not silently accepted. You see what failed, what the AI changed, and why. Once your team approves it, the system updates the deterministic script so future runs are fast and predictable again."

The run report should answer five questions:

1. Which steps ran deterministically?
2. Which steps required AI recovery?
3. What exactly failed?
4. What did the AI do instead?
5. Was the recovery approved and reused later?

This is how the product avoids the most common AI automation trap: "it passed, but nobody knows why."

---

## 5. Team Structure

I would start with one cross-functional team for the first 90 days, then split once the interface between execution and intelligence stabilizes.

### First 90 Days: One Team

Recommended team:

- 1 engineering manager / technical lead
- 2 backend/platform engineers
- 1 AI/product engineer
- 1 frontend engineer
- 1 QA/customer engineer embedded part-time

Why one team:

- The product contract is still forming.
- Trace data, recovery prompts, Playwright behavior, and UI review flows need tight iteration.
- Splitting too early creates handoff friction around the most important boundary: what the agent did and how the platform explains it.

### After 90 Days: Two Workstreams

Once the contracts stabilize, split into:

- **Execution Platform:** Playwright infrastructure, queues, browser isolation, persistence, SLOs, artifacts.
- **AI Recovery and Authoring:** prompts, DOM summarization, recovery ranking, confidence scoring, agentic primary workflows.

The boundary should be the trace schema. The AI team can improve recovery quality, but the platform team owns whether every action is observable, auditable, and safe.

---

## 6. Hardest Conversation With The Founding Team

The hardest conversation is that "agentic testing" cannot be sold as magic for release gates before the trust layer exists.

I would say:

> "The product vision is right, but if we lead with autonomous agents and hide uncertainty, we will lose enterprise trust. The winning product is not the agent that clicks around the most. The winning product is the system that uses AI to recover intelligently, explains exactly what happened, and turns good recoveries back into deterministic automation."

The trade-off:

- Slower near-term demos if we insist on traceability and approval.
- Much stronger long-term enterprise credibility.

The risk of avoiding this conversation:

- Customers see impressive demos but do not trust the system in CI.
- Support cannot debug failures.
- AI costs grow because the same problems are recovered repeatedly.
- The team optimizes for agent novelty instead of release confidence.

The recommendation:

- Make deterministic execution the foundation.
- Make AI fallback the differentiated product loop.
- Make agentic primary an authoring/exploration mode until its SLOs justify broader use.
- Treat trust artifacts as product features, not internal logs.

---

## Closing Position

This product should not ask customers to trust AI blindly. It should give them a system where AI helps when deterministic automation breaks, humans approve durable changes, and every run produces a trace that explains what happened. That is how an AI-native testing company earns the right to sit in the release pipeline.
