export type Lesson = {
  id: string;
  title: string;
  eyebrow: string;
  objective: string;
  definition: string;
  importance: string;
  safety: string;
  activity: string;
  observe: string;
  logs: string;
  features: Record<string, string>;
  rule: string;
  ml: string;
  limitations: string;
  mitigation: string;
  objectives: string[];
  steps: string[];
  references: { title: string; url: string }[];
  questions: { id: string; prompt: string; options: string[] }[];
};
export const base = import.meta.env.VITE_API_BASE_URL || window.location.origin;
let token: Promise<string> | null = null;
export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  headers.set("Content-Type", "application/json");
  if (init?.method && init.method !== "GET")
    headers.set(
      "X-Capstone-Token",
      await (token ||= fetch(base + "/training/session")
        .then((r) => r.json())
        .then((r) => r.token)),
    );
  const response = await fetch(base + path, { ...init, headers });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(
      typeof body.detail === "string"
        ? body.detail
        : `Request failed (${response.status}).`,
    );
  }
  return response.json();
}
export function navigate(path: string) {
  window.location.hash = path;
}
export type Exercise = {
  id: string;
  scenario: string;
  mode: "live" | "sample";
  status: string;
  stage: string;
  error: string;
  completed: boolean;
  history: { stage: string; at: string }[];
  result: {
    run_id: string;
    expected_label: string;
    ground_truth_reason: string;
    redaction_notice: string;
    hashes: Record<string, string>;
    records: {
      number: number;
      event_id: string;
      sanitized_log: string;
      normalized: Record<string, string | number>;
    }[];
    observations: {
      event_ids: string[];
      features: Record<string, number | boolean>;
      rule: { label: string };
      ml: { label: string };
    }[];
    detection_ids: string[];
  };
  quiz_attempts?: {
    score: number;
    passed: boolean;
    answers: number[];
    at: string;
  }[];
};
export function progress(): Record<string, string> {
  try {
    return JSON.parse(localStorage.getItem("training-exercises") || "{}");
  } catch {
    return {};
  }
}
export function remember(scenario: string, id: string) {
  try {
    localStorage.setItem(
      "training-exercises",
      JSON.stringify({ ...progress(), [scenario]: id }),
    );
  } catch {
    /* The current journey still works without browser persistence. */
  }
}
