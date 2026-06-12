// Frontend mirror of `backend/models.py`.
// Keep this file open beside the backend models when changing the API contract.

export type ExecutionMode =
  | "deterministic"
  | "deterministic_with_fallback"
  | "agentic";

export type StepStatus = "passed" | "failed" | "recovered";
export type ModeUsed = "deterministic" | "ai_recovery" | "agentic";

export interface TestIntent {
  intent: string;
  execution_mode: ExecutionMode;
}

export interface TestStep {
  step_id: string;
  description: string;
  action: string;
  selector: string | null;
  value: string | null;
  url: string | null;
  expected_outcome: string;
}

export interface StepResult {
  step_id: string;
  description: string;
  status: StepStatus;
  mode_used: ModeUsed;
  error: string | null;
  agent_action: string | null;
  agent_reasoning: string | null;
  customer_explanation: string | null;
  duration_ms: number;
  is_promotion_candidate: boolean;
  promotion_candidate_id: string | null;
  failed_step: TestStep | null;
  recovered_step: TestStep | null;
}

export type PromotionStatus = "pending" | "approved" | "rejected";

export interface PromotionCandidate {
  candidate_id: string;
  run_id: string;
  intent_hash: string;
  original_intent: string;
  step_id: string;
  original_step: TestStep;
  failed_step: TestStep | null;
  recovered_step: TestStep;
  agent_reasoning: string;
  status: PromotionStatus;
  approved_at: string | null;
}
