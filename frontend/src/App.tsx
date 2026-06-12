import { useState } from "react";

import {
  approvePromotion,
  getPromotions,
  rejectPromotion,
  runTest,
} from "./api";
import { ExecutionTrace } from "./components/ExecutionTrace";
import { IntentInput } from "./components/IntentInput";
import { PromotionPanel } from "./components/PromotionPanel";
import type { ExecutionMode, PromotionCandidate, StepResult } from "./types";

const DEFAULT_INTENT =
  "Search for a t-shirt and add the first result to the cart.";

// Read this frontend file first. It shows the browser flow:
// user intent -> API call -> decision trace -> human promotion review.
function App() {
  const [intent, setIntent] = useState(DEFAULT_INTENT);
  const [executionMode, setExecutionMode] = useState<ExecutionMode>(
    "deterministic_with_fallback",
  );
  const [results, setResults] = useState<StepResult[]>([]);
  const [promotionCandidates, setPromotionCandidates] = useState<
    PromotionCandidate[]
  >([]);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [isUpdatingPromotion, setIsUpdatingPromotion] = useState(false);

  async function handleRun() {
    setIsRunning(true);
    setError(null);
    setNotice(null);

    try {
      const trace = await runTest({
        intent,
        execution_mode: executionMode,
      });
      setResults(trace);
      setPromotionCandidates(await getPromotions());
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : "Something went wrong while running the test.",
      );
    } finally {
      setIsRunning(false);
    }
  }

  async function handleApprovePromotion(candidateId: string) {
    setIsUpdatingPromotion(true);
    setError(null);
    setNotice(null);

    try {
      await approvePromotion(candidateId);
      setPromotionCandidates(await getPromotions());
      setNotice(
        "Promotion approved. Run the same intent again to see the recovered step execute deterministically.",
      );
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : "Could not approve the promotion candidate.",
      );
    } finally {
      setIsUpdatingPromotion(false);
    }
  }

  async function handleRejectPromotion(candidateId: string) {
    setIsUpdatingPromotion(true);
    setError(null);
    setNotice(null);

    try {
      await rejectPromotion(candidateId);
      setPromotionCandidates(await getPromotions());
      setNotice("Promotion rejected. The recovery was kept in the audit trail.");
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : "Could not reject the promotion candidate.",
      );
    } finally {
      setIsUpdatingPromotion(false);
    }
  }

  return (
    <main className="app-shell">
      <header className="hero">
        <p className="eyebrow">Testsigma EM take-home</p>
        <h1>Hybrid Agentic Test Engine</h1>
        <p>
          React sends a plain-English intent to FastAPI, Playwright runs the
          generated steps, AI recovers drifted selectors, and humans approve
          which recoveries become deterministic.
        </p>
      </header>

      <IntentInput
        intent={intent}
        executionMode={executionMode}
        isRunning={isRunning}
        onIntentChange={setIntent}
        onExecutionModeChange={setExecutionMode}
        onRun={handleRun}
      />

      {error ? <div className="error-banner">{error}</div> : null}
      {notice ? <div className="notice-banner">{notice}</div> : null}

      <ExecutionTrace results={results} />

      <PromotionPanel
        candidates={promotionCandidates}
        isUpdating={isUpdatingPromotion}
        onApprove={handleApprovePromotion}
        onReject={handleRejectPromotion}
      />
    </main>
  );
}

export default App;
