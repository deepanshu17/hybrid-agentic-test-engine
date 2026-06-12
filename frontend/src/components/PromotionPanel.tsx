import type { PromotionCandidate } from "../types";

interface PromotionPanelProps {
  candidates: PromotionCandidate[];
  isUpdating: boolean;
  onApprove: (candidateId: string) => void;
  onReject: (candidateId: string) => void;
}

// Phase 3 lives here in the UI: the AI can suggest a recovery, but a human must
// approve it before the system learns and uses it deterministically next time.
export function PromotionPanel({
  candidates,
  isUpdating,
  onApprove,
  onReject,
}: PromotionPanelProps) {
  if (candidates.length === 0) {
    return null;
  }

  return (
    <section className="card promotion-panel">
      <div className="section-heading">
        <p className="eyebrow">Learning loop</p>
        <h2>Promotion candidates</h2>
        <p>
          Review recovered steps. Approving one writes it to
          <code> promoted_steps.json</code>, so the next matching run can use it
          deterministically.
        </p>
      </div>

      <div className="promotion-list">
        {candidates.map((candidate) => (
          <article className="promotion-card" key={candidate.candidate_id}>
            <div>
              <p className="candidate-id">{candidate.candidate_id}</p>
              <h3>
                {candidate.step_id}: {candidate.original_step.description}
              </h3>
            </div>

            <dl className="selector-diff">
              <div>
                <dt>Generated deterministic selector</dt>
                <dd>{candidate.original_step.selector ?? "n/a"}</dd>
              </div>
              <div>
                <dt>Failed runtime selector</dt>
                <dd>{candidate.failed_step?.selector ?? "n/a"}</dd>
              </div>
              <div>
                <dt>Recovered selector</dt>
                <dd>{candidate.recovered_step.selector ?? "n/a"}</dd>
              </div>
            </dl>

            <details>
              <summary>Why the agent suggested this</summary>
              <p>{candidate.agent_reasoning}</p>
            </details>

            <div className="promotion-actions">
              <button
                disabled={isUpdating}
                onClick={() => onApprove(candidate.candidate_id)}
              >
                Approve promotion
              </button>
              <button
                className="secondary-button"
                disabled={isUpdating}
                onClick={() => onReject(candidate.candidate_id)}
              >
                Reject
              </button>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
