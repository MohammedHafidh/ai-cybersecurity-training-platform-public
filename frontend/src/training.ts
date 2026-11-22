export type Lesson = {
  id: string; title: string; eyebrow: string; objective: string; definition: string; importance: string;
  safety: string; activity: string; observe: string; logs: string; features: Record<string, string>;
  rule: string; ml: string; limitations: string; mitigation: string; objectives: string[]; steps: string[];
  references: { title: string; url: string }[];
  questions: { id: string; prompt: string; options: string[] }[];
}
export const base = import.meta.env.VITE_API_BASE_URL || window.location.origin
export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(base + path, { ...init, headers: { 'Content-Type': 'application/json', ...init?.headers } })
  if (!response.ok) { const body = await response.json().catch(() => ({})); throw new Error(typeof body.detail === 'string' ? body.detail : `Request failed (${response.status}).`) }
  return response.json()
}
export function navigate(path: string) { window.location.hash = path }
