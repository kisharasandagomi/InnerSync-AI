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
  /**
   * Round 6: that check-in's ranked actions, verbatim -- empty when
   * `is_affirmation` or `is_escalation` is true, same mutual-exclusivity as
   * `AssessmentResult`.
   */
  recommendations: RecommendationItem[];
  is_affirmation: boolean;
  affirmation: string | null;
  escalation_message: string | null;
  /**
   * Round 7: "improved" | "same" | "worse" comparing this check-in to the
   * one before it, or null for a genuine first-ever check-in. The stored
   * value behind round 3's `comparative_trend_message`, exposed per-item
   * here for the first time so the development summary can aggregate it
   * without recomputing anything.
   */
  comparative_trend_outcome: "improved" | "same" | "worse" | null;
}

/**
 * The caller's own current profile — see `GET /auth/me` (round 7).
 */
export interface MeResponse {
  id: number;
  email: string;
  display_name: string | null;
  otp_enabled: boolean;
}

/**
 * `POST /auth/login`'s response (round 7): either a token directly (the
 * default, for every account that hasn't opted into OTP), or a request for
 * a one-time code. See `backend/app/schemas/auth.py`'s `LoginResponse`.
 */
export interface LoginResponse {
  otp_required: boolean;
  login_token: string | null;
  access_token: string | null;
  token_type: string;
  display_name: string | null;
}

/** Aggregated, plain-language pattern summary — see `GET /assessments/summary` (round 7). */
export interface DevelopmentSummaryResponse {
  checkins_considered: number;
  most_frequent_factor_label: string | null;
  most_frequent_factor_count: number;
  engaged_count: number;
  engaged_considered: number;
  summary_sentence: string;
  closing_message: string;
}

/**
 * Whether the profile page's persistent wellbeing signpost should show —
 * see `GET /assessments/escalation-status` (round 7). A direct read of the
 * caller's most recent check-in's own `is_escalation` flag, not a fresh
 * calculation.
 */
export interface EscalationStatusResponse {
  is_escalation: boolean;
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

/**
 * Exchange credentials for either an access token, or a request for a
 * one-time code (round 7) -- check `otp_required` on the result before
 * treating `access_token` as present. See `AuthPage.tsx`'s login handling.
 */
export function login(email: string, password: string) {
  return request<LoginResponse>(
    "/auth/login",
    { method: "POST", body: JSON.stringify({ email, password }) },
  );
}

/** Second step of an OTP-gated login: the code emailed to the account. */
export function verifyOtp(loginToken: string, code: string) {
  return request<{ access_token: string; token_type: string; display_name: string | null }>(
    "/auth/login/verify-otp",
    { method: "POST", body: JSON.stringify({ login_token: loginToken, code }) },
  );
}

/** The caller's own current profile, fresh from the database. */
export function getMe(token: string) {
  return request<MeResponse>("/auth/me", { method: "GET" }, token);
}

/** Update the caller's own display name. Pass `null`/blank to clear it. */
export function updateDisplayName(displayName: string | null, token: string) {
  return request<MeResponse>(
    "/auth/profile",
    { method: "PATCH", body: JSON.stringify({ display_name: displayName }) },
    token,
  );
}

/**
 * Change the caller's own password while signed in -- distinct from
 * `resetPassword`'s forgot-password flow: this requires the current
 * password, standard practice for an in-session credential change.
 */
export function changePassword(currentPassword: string, newPassword: string, token: string) {
  return request<void>(
    "/auth/change-password",
    {
      method: "POST",
      body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
    },
    token,
  );
}

/** Turn email one-time-code sign-in on or off. Opt-in; default off. */
export function updateOtpSetting(enabled: boolean, token: string) {
  return request<MeResponse>(
    "/auth/otp-setting",
    { method: "PATCH", body: JSON.stringify({ enabled }) },
    token,
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
 * Aggregated, plain-language summary across the caller's most recent
 * check-ins (round 7). Read-only, entirely server-computed and
 * safety-gate-validated -- see `app.services.development_summary`.
 */
export function getDevelopmentSummary(token: string) {
  return request<DevelopmentSummaryResponse>(
    "/assessments/summary",
    { method: "GET" },
    token,
  );
}

/**
 * Whether the caller's most recent check-in is a sustained-high-stress
 * escalation (round 7) -- powers the profile page's persistent wellbeing
 * signpost. Read-only; reflects `Recommendation.is_escalation` exactly as
 * already computed by the Adaptive Recovery Framework, never recalculated
 * here.
 */
export function getEscalationStatus(token: string) {
  return request<EscalationStatusResponse>(
    "/assessments/escalation-status",
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
