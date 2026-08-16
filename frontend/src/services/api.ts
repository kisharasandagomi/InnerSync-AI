/**
 * Thin client over the FastAPI backend.
 *
 * This module contains no ML, SHAP, or explanation logic — the explanation text
 * and recommendations are produced server-side (where they pass the vocabulary
 * safety gate) and are rendered here verbatim.
 *
 * Token handling: see `auth.ts`.
 */

import type { AssessmentPayload } from "./featureSchema";

const BASE = "/api";

export interface RecommendationItem {
  priority: number;
  title: string;
  action: string;
  rationale: string;
  category: string;
}

export interface AssessmentResult {
  assessment_id: number;
  created_at: string;
  stress_level: 0 | 1 | 2;
  stress_level_label: string;
  explanation: string;
  recommendations: RecommendationItem[];
  is_affirmation: boolean;
  affirmation: string | null;
}

export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

/** Pull a human-usable message out of FastAPI's error shapes. */
async function toError(response: Response): Promise<ApiError> {
  let detail = response.statusText;
  try {
    const body = await response.json();
    if (typeof body.detail === "string") {
      detail = body.detail;
    } else if (Array.isArray(body.detail) && body.detail.length > 0) {
      // Pydantic validation errors.
      const first = body.detail[0];
      const field = Array.isArray(first.loc) ? first.loc.at(-1) : "input";
      detail = `${field}: ${first.msg}`;
    }
  } catch {
    // Non-JSON body; keep statusText.
  }
  return new ApiError(response.status, detail);
}

async function request<T>(
  path: string,
  init: RequestInit,
  token?: string | null,
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init.headers as Record<string, string> | undefined),
  };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(`${BASE}${path}`, { ...init, headers });
  if (!response.ok) {
    throw await toError(response);
  }
  return (await response.json()) as T;
}

export function register(email: string, password: string) {
  return request<{ id: number; email: string; created_at: string }>(
    "/auth/register",
    { method: "POST", body: JSON.stringify({ email, password }) },
  );
}

export function login(email: string, password: string) {
  return request<{ access_token: string; token_type: string }>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export function submitAssessment(answers: AssessmentPayload, token: string) {
  return request<AssessmentResult>(
    "/assessments",
    { method: "POST", body: JSON.stringify(answers) },
    token,
  );
}
