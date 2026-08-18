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

/**
 * Self-reported engagement with the *previous* check-in's recommendations.
 * Mirrors the backend's `PreviousEngagement` literal exactly — see
 * `backend/app/schemas/assessment.py`. Collected as part of every submission
 * so the Adaptive Recovery Framework has a signal to act on.
 */
export type PreviousEngagement = "yes" | "partially" | "no" | "no_previous_checkin";

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
  /**
   * True when sustained high stress across consecutive check-ins replaced
   * the normal recommendations with a wellbeing-service signpost, regardless
   * of engagement. Mutually exclusive with `is_affirmation` and with a
   * non-empty `recommendations` list.
   */
  is_escalation: boolean;
  escalation_message: string | null;
  /**
   * A short message comparing this result to the student's immediately
   * previous check-in, or `null` for a genuine first-ever check-in or when
   * the comparison is otherwise unavailable. Already safety-gated and
   * escalation-coordinated server-side (see
   * `docs/research/methodology.md` § Comparative Trend Message) — rendered
   * verbatim, never re-derived here.
   */
  comparative_trend_message: string | null;
}

/**
 * One past check-in, as returned by `GET /assessments/history`.
 *
 * Same non-technical discipline as `AssessmentResult`: no SHAP value, no raw
 * feature name, no numeric severity score. `top_factor_phrase` is the same
 * kind of pre-approved plain-language phrase already used in the explanation
 * paragraph, generated server-side, rendered here verbatim.
 */
export interface AssessmentHistoryItem {
  assessment_id: number;
  created_at: string;
  stress_level: 0 | 1 | 2;
  stress_level_label: string;
  previous_engagement: PreviousEngagement;
  adaptive_recovery_applied: boolean;
  is_escalation: boolean;
  top_factor_phrase: string | null;
  /** That check-in's full explanation paragraph, verbatim — see ProgressPage's expandable entries. */
  explanation: string;
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

/**
 * `displayName` and `hobby` are both optional, collected once at
 * registration — see `docs/research/methodology.md` § Personalized Greeting
 * and § Hobby-Personalized Recommendations. Neither adds a required step;
 * omitting either leaves the graceful fallbacks this project already uses
 * elsewhere.
 */
export function register(
  email: string,
  password: string,
  displayName?: string,
  hobby?: string,
) {
  return request<{ id: number; email: string; created_at: string; display_name: string | null }>(
    "/auth/register",
    {
      method: "POST",
      body: JSON.stringify({
        email,
        password,
        display_name: displayName || undefined,
        hobby: hobby || undefined,
      }),
    },
  );
}

/** Deactivate the caller's own account. Requires their current password. */
export function deactivateAccount(password: string, token: string) {
  return request<void>(
    "/auth/deactivate",
    { method: "POST", body: JSON.stringify({ password }) },
    token,
  );
}

/**
 * Request a password reset link. The backend always returns the same
 * generic confirmation, whether or not `email` belongs to a registered
 * account -- see `backend/app/api/auth.py`'s `forgot_password` docstring.
 */
export function forgotPassword(email: string) {
  return request<{ message: string }>(
    "/auth/forgot-password",
    { method: "POST", body: JSON.stringify({ email }) },
  );
}

/** Set a new password given a valid, unused, unexpired reset token. */
export function resetPassword(token: string, newPassword: string) {
  return request<void>(
    "/auth/reset-password",
    { method: "POST", body: JSON.stringify({ token, new_password: newPassword }) },
  );
}

export function login(email: string, password: string) {
  return request<{ access_token: string; token_type: string; display_name: string | null }>(
    "/auth/login",
    { method: "POST", body: JSON.stringify({ email, password }) },
  );
}

export function submitAssessment(
  answers: AssessmentPayload,
  previousEngagement: PreviousEngagement,
  token: string,
) {
  return request<AssessmentResult>(
    "/assessments",
    {
      method: "POST",
      // One flat object: the backend's AssessmentCreateRequest has
      // previous_engagement as a sibling field alongside the 14 features,
      // not a nested one.
      body: JSON.stringify({ ...answers, previous_engagement: previousEngagement }),
    },
    token,
  );
}

/** The caller's own past check-ins, oldest first. Read-only. */
export function getAssessmentHistory(token: string) {
  return request<AssessmentHistoryItem[]>(
    "/assessments/history",
    { method: "GET" },
    token,
  );
}

/**
 * One chatbot message (Module 3), either role. `fallback_reason` is set only
 * on an "assistant" message that is a fixed canned reply rather than
 * Gemini's own output (safety-gate rejection, rate limit, or an outage) —
 * see `backend/app/models/chat_message.py`. Rendered identically either way;
 * this page does not treat it as an error state, since the fallback text is
 * itself a normal, safe reply to show.
 */
export interface ChatMessageItem {
  id: number;
  role: "user" | "assistant";
  content: string;
  created_at: string;
  fallback_reason: string | null;
}

export interface ChatTurnResult {
  user_message: ChatMessageItem;
  assistant_message: ChatMessageItem;
}

/** The caller's own recent chat messages, oldest first. Read-only. */
export function getChatHistory(token: string) {
  return request<ChatMessageItem[]>("/chat/messages", { method: "GET" }, token);
}

/** Send one chat message and get the reply. */
export function sendChatMessage(content: string, token: string) {
  return request<ChatTurnResult>(
    "/chat/messages",
    { method: "POST", body: JSON.stringify({ content }) },
    token,
  );
}
