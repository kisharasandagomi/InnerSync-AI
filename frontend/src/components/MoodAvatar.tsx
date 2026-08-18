/**
 * Small rabbit mascot whose expression reflects the student's most recent
 * check-in level. Purely decorative and understated -- no numbers, no
 * streaks, no competitive framing attached to it, per round 4's brief.
 * Never renders the raw 0/1/2 score, only via the three named expressions
 * below, so it carries the same "plain-language only" discipline as the
 * rest of the app's user-facing surface.
 */

export type MoodLevel = 0 | 1 | 2;

const MOOD_LABEL: Record<MoodLevel, string> = {
  0: "Feeling calm after your last check-in",
  1: "Feeling steady after your last check-in",
  2: "Here for you after your last check-in",
};

interface MoodAvatarProps {
  /** The most recent check-in's stress_level, or null if there is none yet
   *  (a brand-new account) -- rendered with the same calm default as level 0
   *  rather than an alarming placeholder. */
  level: MoodLevel | null;
  className?: string;
}

export function MoodAvatar({ level, className }: MoodAvatarProps) {
  const resolved: MoodLevel = level ?? 0;
  const label = level === null ? "Say hello to InnerSync" : MOOD_LABEL[resolved];

  return (
    <svg
      viewBox="0 0 40 40"
      className={className}
      role="img"
      aria-label={label}
    >
      <title>{label}</title>
      {/* Ears */}
      <path
        d="M14 14 C12 6, 15 2, 17 3 C19 4, 18 10, 17 16 Z"
        fill="#f4f1ea"
        stroke="#14213d"
        strokeWidth="1.2"
        strokeLinejoin="round"
      />
      <path
        d="M26 14 C28 6, 25 2, 23 3 C21 4, 22 10, 23 16 Z"
        fill="#f4f1ea"
        stroke="#14213d"
        strokeWidth="1.2"
        strokeLinejoin="round"
      />
      {/* Head */}
      <circle cx="20" cy="23" r="12" fill="#f4f1ea" stroke="#14213d" strokeWidth="1.2" />

      {/* Cheeks: a small warm touch, same at every level */}
      <circle cx="14" cy="26" r="1.6" fill="#c99a2e" opacity="0.35" />
      <circle cx="26" cy="26" r="1.6" fill="#c99a2e" opacity="0.35" />

      {/* Eyes */}
      <circle cx="15.5" cy="22" r="1.4" fill="#14213d" />
      <circle cx="24.5" cy="22" r="1.4" fill="#14213d" />

      {/* Eyebrows: the only part that changes between "calm" and "caring". */}
      {resolved === 2 && (
        <>
          <path d="M13 18.5 Q15.5 17 17.5 19" stroke="#14213d" strokeWidth="1" fill="none" strokeLinecap="round" />
          <path d="M27 18.5 Q24.5 17 22.5 19" stroke="#14213d" strokeWidth="1" fill="none" strokeLinecap="round" />
        </>
      )}

      {/* Mouth: gentle smile (calm), soft neutral curve (moderate), small
          soft "o" (high -- caring, not alarmed). */}
      {resolved === 0 && (
        <path d="M16.5 27 Q20 30 23.5 27" stroke="#14213d" strokeWidth="1.2" fill="none" strokeLinecap="round" />
      )}
      {resolved === 1 && (
        <path d="M17 27.5 Q20 28.5 23 27.5" stroke="#14213d" strokeWidth="1.2" fill="none" strokeLinecap="round" />
      )}
      {resolved === 2 && (
        <ellipse cx="20" cy="27.5" rx="1.6" ry="1.9" fill="none" stroke="#14213d" strokeWidth="1.1" />
      )}
    </svg>
  );
}
