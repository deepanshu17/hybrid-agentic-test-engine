import type { ExecutionMode } from "../types";

interface IntentInputProps {
  intent: string;
  executionMode: ExecutionMode;
  isRunning: boolean;
  onIntentChange: (intent: string) => void;
  onExecutionModeChange: (mode: ExecutionMode) => void;
  onRun: () => void;
}

// This component is intentionally boring: one input path into the system.
// Phase 2 should improve backend behavior, not add UI complexity here.
export function IntentInput({
  intent,
  executionMode,
  isRunning,
  onIntentChange,
  onExecutionModeChange,
  onRun,
}: IntentInputProps) {
  return (
    <section className="card">
      <div className="section-heading">
        <p className="eyebrow">Phase 1 spine</p>
        <h2>Describe the test intent</h2>
      </div>

      <label className="field">
        <span>Plain-English intent</span>
        <textarea
          value={intent}
          onChange={(event) => onIntentChange(event.target.value)}
          placeholder="Example: search for a t-shirt and add the first result to cart"
          rows={4}
        />
      </label>

      <div className="controls">
        <label className="field compact">
          <span>Execution mode</span>
          <select
            value={executionMode}
            onChange={(event) =>
              onExecutionModeChange(event.target.value as ExecutionMode)
            }
          >
            <option value="deterministic">Deterministic</option>
            <option value="deterministic_with_fallback">
              Deterministic + AI fallback
            </option>
            <option value="agentic">Agentic primary</option>
          </select>
        </label>

        <button disabled={isRunning || intent.trim().length === 0} onClick={onRun}>
          {isRunning ? "Running..." : "Run test"}
        </button>
      </div>
    </section>
  );
}
