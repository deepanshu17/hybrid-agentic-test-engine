import type { PromotionCandidate, StepResult, TestIntent } from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

// Look here after `App.tsx`: this is the single boundary between React and
// FastAPI. Later phases should keep this small and add backend behavior instead
// of spreading fetch calls throughout components.
export async function runTest(payload: TestIntent): Promise<StepResult[]> {
  const response = await fetch(`${API_BASE_URL}/run-test`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || "Failed to run test");
  }

  return response.json();
}

export async function getPromotions(): Promise<PromotionCandidate[]> {
  const response = await fetch(`${API_BASE_URL}/promotions`);

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || "Failed to load promotion candidates");
  }

  return response.json();
}

async function decidePromotion(
  endpoint: "/promote" | "/reject-promotion",
  candidateId: string,
): Promise<PromotionCandidate> {
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ candidate_id: candidateId }),
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || "Failed to update promotion candidate");
  }

  return response.json();
}

export function approvePromotion(candidateId: string) {
  return decidePromotion("/promote", candidateId);
}

export function rejectPromotion(candidateId: string) {
  return decidePromotion("/reject-promotion", candidateId);
}
