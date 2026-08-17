export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    credentials: "include",
    headers: {
      ...(init?.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      ...init?.headers,
    },
    cache: "no-store",
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    const detail = payload.detail;
    const message = Array.isArray(detail)
      ? detail.map((item) => {
          const field = Array.isArray(item.loc) ? item.loc[item.loc.length - 1] : "field";
          return `${String(field).replaceAll("_", " ")}: ${item.msg || "invalid value"}`;
        }).join(" · ")
      : typeof detail === "string" ? detail : `Request failed (${response.status})`;
    throw new Error(message);
  }
  if (response.status === 204) return undefined as T;
  return response.json();
}

export type Organization = { id: string; name: string; slug: string };
export type User = { id: string; email: string; display_name: string };
export type Auth = { user: User; organizations: Organization[] };
export type Job = { id: string; organization_id: string; title: string; location: string; active: boolean; created_at: string };
export type Requirement = { id: string; position: number; title: string; description: string; weight: number; keywords: string[]; anchors: Record<string, string> };
export type Rubric = { id: string; job_id: string; version: number; approved: boolean; approved_at: string | null; requirements: Requirement[] };
export type Candidate = { id: string; full_name: string; email: string };
export type Application = { id: string; status: string; aggregate_score: number | null; score_percentage: number | null; review_reason: string; created_at: string; candidate: Candidate };
export type Score = { id: string; score: number; confidence: number; rationale: string; evidence: { location: string; text: string; matched_terms: string[] }[]; gaps: string[]; needs_review: boolean; requirement: Requirement };
export type ApplicationDetail = Application & { job: Job; rubric: Rubric; scores: Score[] };
