import type { StepResult } from "../types";

interface ExecutionTraceProps {
  results: StepResult[];
}

function formatMode(mode: StepResult["mode_used"]) {
  if (mode === "ai_recovery") {
    return "AI recovery";
  }

  if (mode === "agentic") {
    return "Agentic";
  }

  return "Deterministic";
}

// This table is the main artifact of the product: every execution decision
// should eventually be explainable from one row here.
export function ExecutionTrace({ results }: ExecutionTraceProps) {
  if (results.length === 0) {
    return (
      <section className="card empty-state">
        <h2>Decision trace</h2>
        <p>Run a test intent to see the per-step trace.</p>
      </section>
    );
  }

  return (
    <section className="card">
      <div className="section-heading">
        <p className="eyebrow">Output</p>
        <h2>Decision trace</h2>
      </div>

      <div className="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>Step</th>
              <th>Status</th>
              <th>Mode</th>
              <th>Duration</th>
              <th>Explanation</th>
            </tr>
          </thead>
          <tbody>
            {results.map((result) => (
              <tr key={result.step_id}>
                <td>
                  <strong>{result.step_id}</strong>
                  <span>{result.description}</span>
                </td>
                <td>
                  <span className={`badge ${result.status}`}>
                    {result.status}
                  </span>
                  {result.is_promotion_candidate ? (
                    <span className="promotion-pill">Promotion candidate</span>
                  ) : null}
                  {result.promotion_candidate_id ? (
                    <span className="candidate-id">
                      {result.promotion_candidate_id}
                    </span>
                  ) : null}
                </td>
                <td>{formatMode(result.mode_used)}</td>
                <td>{result.duration_ms}ms</td>
                <td>
                  <p>{result.customer_explanation ?? "No explanation provided."}</p>
                  {result.error ? <p className="error-text">{result.error}</p> : null}
                  {result.agent_action ? (
                    <p className="agent-text">{result.agent_action}</p>
                  ) : null}
                  {result.agent_reasoning ? (
                    <details>
                      <summary>Agent reasoning</summary>
                      <p>{result.agent_reasoning}</p>
                    </details>
                  ) : null}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
