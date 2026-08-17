/**
 * The personalized check-in greeting (round 3) — a template, not an LLM
 * generation, mirroring `backend/app/schemas/auth.py`'s
 * `resolve_greeting_name` exactly (see that function's docstring for why
 * both sides carry this same small piece of logic rather than only one).
 */

/**
 * The name to greet a student by: their own choice, or a graceful fallback.
 *
 * Never returns blank or broken text — a missing/blank `displayName` falls
 * back to the part of the email before `@`, which always exists for an
 * authenticated student.
 *
 * @param displayName - The student's own chosen name, or `null`/blank if
 *   never set.
 * @param email - Always present — the fallback source.
 */
export function resolveGreetingName(displayName: string | null, email: string): string {
  const trimmed = displayName?.trim();
  if (trimmed) return trimmed;
  return email.split("@")[0];
}

/** The fixed greeting template shown as the first message of a check-in. */
export function checkinGreeting(displayName: string | null, email: string): string {
  return `Hi ${resolveGreetingName(displayName, email)}, ready for your check-in?`;
}
