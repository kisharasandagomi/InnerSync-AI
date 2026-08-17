import { useEffect, useRef, useState, type FormEvent } from "react";
import { Link, useLocation } from "react-router-dom";
import { CheckinQuestionControl } from "../components/CheckinQuestion";
import {
  ApiError,
  getChatHistory,
  sendChatMessage,
  submitAssessment,
  type AssessmentResult,
  type ChatMessageItem,
  type PreviousEngagement,
} from "../services/api";
import {
  answerEngagement,
  answerFeature,
  currentQuestion,
  isComplete,
  startCheckin,
  toSubmission,
  type CheckinQuestion,
  type CheckinState,
} from "../services/checkinFlow";
import { useAuth } from "../services/auth";

type Mode = "menu" | "talk" | "checkin";

/**
 * Chat page (Module 3 — free-form conversation — plus the chat-delivered
 * check-in added this session).
 *
 * Two clearly separate modes, chosen explicitly by the student, never
 * blended:
 * - **"talk"**: the original free-form Gemini conversation. Unchanged —
 *   still never feeds into the prediction model (see
 *   `backend/app/chatbot/service.py`'s module docstring).
 * - **"checkin"**: the 14 questions from `feature_schema.json`, asked one at
 *   a time as chat messages, each answered through a bounded quick-select
 *   control (`CheckinQuestionControl`) — never free text, never interpreted
 *   by the LLM. On completion this calls the **same, unchanged**
 *   `submitAssessment` → `POST /assessments` the slider form
 *   (`AssessmentPage.tsx`) has always used. See
 *   `services/checkinFlow.ts` for the state machine and
 *   `docs/research/methodology.md` § Chat-Driven Check-In Delivery for why
 *   the LLM has no role in capturing these answers.
 */
const INTRO_MESSAGE =
  "Hi, I'm here to talk through how things are going. I'm an AI wellbeing " +
  "check-in, not a counsellor — if you'd rather talk to a person, your " +
  "university wellbeing service is a great place to start. What's on your mind?";

interface LocalMessage {
  id: string;
  role: "assistant" | "user";
  content: string;
}

export function ChatPage() {
  const location = useLocation();
  const requestedMode = (location.state as { mode?: Mode } | null)?.mode;
  const [mode, setMode] = useState<Mode>(requestedMode ?? "menu");
  const { token } = useAuth();
  const bottomRef = useRef<HTMLDivElement>(null);

  // --- "talk" mode state: unchanged from the original free-form chat ---
  const [history, setHistory] = useState<ChatMessageItem[] | null>(null);
  const [draft, setDraft] = useState("");
  const [talkError, setTalkError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);

  // --- "checkin" mode state ---
  const [checkinState, setCheckinState] = useState<CheckinState>(startCheckin);
  const [transcript, setTranscript] = useState<LocalMessage[]>([]);
  const [checkinBusy, setCheckinBusy] = useState(false);
  const [checkinError, setCheckinError] = useState<string | null>(null);
  const [checkinResult, setCheckinResult] = useState<AssessmentResult | null>(null);

  useEffect(() => {
    if (mode !== "talk" || !token) return;
    getChatHistory(token)
      .then(setHistory)
      .catch((err) => {
        setTalkError(
          err instanceof ApiError
            ? err.message
            : "Could not reach the server. Is the backend running?",
        );
        setHistory([]);
      });
  }, [mode, token]);

  useEffect(() => {
    if (mode !== "checkin" || transcript.length > 0) return;
    const question = currentQuestion(checkinState);
    if (question) {
      setTranscript([{ id: "q-0", role: "assistant", content: questionPrompt(question) }]);
    }
    // Only ever run once per entry into checkin mode — subsequent questions
    // are appended by advanceCheckin, not this effect.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [history, transcript, checkinResult]);

  async function handleTalkSubmit(event: FormEvent) {
    event.preventDefault();
    const content = draft.trim();
    if (!content || !token || sending) return;

    setTalkError(null);
    setSending(true);
    setDraft("");
    try {
      const result = await sendChatMessage(content, token);
      setHistory((prev) => [...(prev ?? []), result.user_message, result.assistant_message]);
    } catch (err) {
      setTalkError(
        err instanceof ApiError
          ? err.message
          : "Could not reach the server. Is the backend running?",
      );
      setDraft(content);
    } finally {
      setSending(false);
    }
  }

  function advanceCheckin(next: CheckinState) {
    setCheckinState(next);
    if (isComplete(next)) {
      submitCheckin(next);
      return;
    }
    const question = currentQuestion(next);
    if (question) {
      setTranscript((prev) => [
        ...prev,
        { id: `q-${prev.length}`, role: "assistant", content: questionPrompt(question) },
      ]);
    }
  }

  function handleEngagementAnswer(value: PreviousEngagement) {
    const label =
      ENGAGEMENT_LABELS[value] ??
      value; /* falls back to the raw value; every real option is covered above */
    setTranscript((prev) => [...prev, { id: "a-engagement", role: "user", content: label }]);
    advanceCheckin(answerEngagement(checkinState, value));
  }

  function handleFeatureAnswer(value: number) {
    const question = currentQuestion(checkinState);
    if (!question || question.kind !== "feature") return;
    const label = describeFeatureAnswer(question, value);
    setTranscript((prev) => [
      ...prev,
      { id: `a-${question.field.name}`, role: "user", content: label },
    ]);
    advanceCheckin(answerFeature(checkinState, value));
  }

  async function submitCheckin(finalState: CheckinState) {
    if (!token) return;
    setCheckinBusy(true);
    setCheckinError(null);
    try {
      const { answers, previousEngagement } = toSubmission(finalState);
      // The exact same call the slider form makes — POST /assessments is
      // completely unchanged by this chat-delivered flow.
      const result = await submitAssessment(answers, previousEngagement, token);
      setCheckinResult(result);
    } catch (err) {
      setCheckinError(
        err instanceof ApiError
          ? err.message
          : "Could not reach the server. Is the backend running?",
      );
    } finally {
      setCheckinBusy(false);
    }
  }

  function startOver() {
    const fresh = startCheckin();
    setCheckinState(fresh);
    setCheckinResult(null);
    setCheckinError(null);
    const question = currentQuestion(fresh);
    setTranscript(question ? [{ id: "q-0", role: "assistant", content: questionPrompt(question) }] : []);
  }

  if (mode === "menu") {
    return <ModeMenu onChoose={setMode} />;
  }

  const activeQuestion = mode === "checkin" ? currentQuestion(checkinState) : null;

  return (
    <div className="chat-shell flex h-[calc(100vh-11rem)] flex-col">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm uppercase tracking-wider text-ink-faint">
            {mode === "checkin" ? "Check-in" : "Chat"}
          </p>
          <h1 className="mt-1 text-xl font-semibold tracking-tight text-ink">
            {mode === "checkin" ? "Let's talk through your check-in" : "Talk it through"}
          </h1>
        </div>
        <button
          type="button"
          onClick={() => setMode("menu")}
          className="rounded-md border border-line px-3 py-1.5 text-sm text-ink-soft transition-colors hover:bg-accent-soft hover:text-accent-strong focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
        >
          Change mode
        </button>
      </div>

      {mode === "checkin" && activeQuestion?.kind === "feature" && !checkinResult && (
        <p className="mt-3 text-sm font-medium text-accent-strong">
          Question {activeQuestion.index} of {activeQuestion.total}
        </p>
      )}

      <div className="mt-4 flex-1 space-y-4 overflow-y-auto rounded-2xl border border-line bg-[var(--chat-surface)] p-5">
        {mode === "talk" && (
          <>
            <Bubble role="assistant" content={INTRO_MESSAGE} />
            {history === null && (
              <p className="text-base text-ink-faint">Loading your conversation…</p>
            )}
            {history?.map((message) => (
              <Bubble key={message.id} role={message.role} content={message.content} />
            ))}
          </>
        )}

        {mode === "checkin" && (
          <>
            {transcript.map((message, i) => (
              <div key={message.id}>
                <Bubble role={message.role} content={message.content} />
                {/* The control only ever appears under the single most recent
                    assistant message, and only while that question is still
                    unanswered — never re-shown for a question already answered. */}
                {message.role === "assistant" &&
                  i === transcript.length - 1 &&
                  !checkinBusy &&
                  !checkinResult &&
                  activeQuestion && (
                    <CheckinQuestionControl
                      question={activeQuestion}
                      onAnswerFeature={handleFeatureAnswer}
                      onAnswerEngagement={handleEngagementAnswer}
                    />
                  )}
              </div>
            ))}
            {checkinBusy && (
              <p className="text-base text-ink-faint">Working out what this means…</p>
            )}
            {checkinResult && <CheckinResultBubbles result={checkinResult} />}
          </>
        )}

        <div ref={bottomRef} />
      </div>

      {mode === "talk" && talkError && (
        <p className="mt-3 rounded-md border border-line bg-accent-soft/40 p-3 text-base text-ink-soft">
          {talkError}
        </p>
      )}
      {mode === "checkin" && checkinError && (
        <p className="mt-3 rounded-md border border-line bg-accent-soft/40 p-3 text-base text-ink-soft">
          {checkinError}
        </p>
      )}

      {mode === "talk" && (
        <form onSubmit={handleTalkSubmit} className="mt-3 flex gap-2">
          <label htmlFor="chat-input" className="sr-only">
            Your message
          </label>
          <input
            id="chat-input"
            type="text"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            disabled={sending}
            placeholder="Type a message…"
            maxLength={4000}
            className="flex-1 rounded-full border border-line bg-card px-4 py-2.5 text-base text-ink focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
          />
          <button
            type="submit"
            disabled={sending || draft.trim().length === 0}
            className="rounded-full border border-accent bg-accent-soft px-5 py-2.5 text-base font-medium text-accent-strong transition-colors hover:bg-accent-soft/70 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent disabled:cursor-not-allowed disabled:opacity-50"
          >
            {sending ? "Sending…" : "Send"}
          </button>
        </form>
      )}

      {mode === "checkin" && checkinResult && (
        <div className="mt-4 flex flex-wrap items-center gap-4">
          <button
            type="button"
            onClick={startOver}
            className="rounded-md border border-line px-4 py-2 text-base text-ink-soft transition-colors hover:bg-accent-soft hover:text-accent-strong focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
          >
            Start another check-in
          </button>
          <Link
            to="/progress"
            className="text-base text-ink-soft underline-offset-4 hover:text-accent-strong hover:underline"
          >
            See your trends
          </Link>
        </div>
      )}
    </div>
  );
}

function ModeMenu({ onChoose }: { onChoose: (mode: Mode) => void }) {
  return (
    <div className="mx-auto max-w-lg text-center">
      <p className="text-sm uppercase tracking-wider text-ink-faint">Chat</p>
      <h1 className="mt-2 text-xl font-semibold tracking-tight text-ink">
        What would help right now?
      </h1>
      <div className="mt-6 grid gap-3 sm:grid-cols-2">
        <button
          type="button"
          onClick={() => onChoose("checkin")}
          className="rounded-lg border border-accent bg-accent-soft px-5 py-6 text-left transition-colors hover:bg-accent-soft/70 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
        >
          <p className="text-base font-semibold text-accent-strong">Start a check-in</p>
          <p className="mt-1 text-sm text-ink-soft">
            14 quick questions, one at a time, then a plain-language read on
            things.
          </p>
        </button>
        <button
          type="button"
          onClick={() => onChoose("talk")}
          className="rounded-lg border border-line bg-card px-5 py-6 text-left transition-colors hover:bg-accent-soft/40 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
        >
          <p className="text-base font-semibold text-ink">Just talk</p>
          <p className="mt-1 text-sm text-ink-soft">
            An open conversation. Doesn't affect your check-in results.
          </p>
        </button>
      </div>
    </div>
  );
}

function Bubble({ role, content }: { role: "user" | "assistant"; content: string }) {
  const isUser = role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <p
        className={`max-w-[80%] whitespace-pre-line rounded-2xl px-5 py-3 text-base leading-7 ${
          isUser
            ? "bg-accent-strong text-white"
            : "border border-line/60 bg-[var(--chat-bubble-assistant)] text-ink"
        }`}
      >
        {content}
      </p>
    </div>
  );
}

/**
 * Renders the assessment response as sequential chat bubbles.
 *
 * Every piece of text here — the explanation paragraph, the escalation
 * message, the affirmation, and each recommendation's title/action/rationale
 * — is rendered **exactly as `POST /assessments` returned it**. It already
 * passed the safety gate server-side; nothing here re-words, truncates, or
 * re-generates any of it, the same discipline `ResultsPage.tsx` already
 * follows for the slider-form path.
 */
function CheckinResultBubbles({ result }: { result: AssessmentResult }) {
  return (
    <>
      <Bubble
        role="assistant"
        content={`Things look ${result.stress_level_label} right now.`}
      />
      <Bubble role="assistant" content={result.explanation} />
      {result.is_escalation ? (
        <Bubble role="assistant" content={result.escalation_message ?? ""} />
      ) : result.is_affirmation ? (
        <Bubble role="assistant" content={result.affirmation ?? ""} />
      ) : (
        result.recommendations.map((rec) => (
          <Bubble
            key={rec.priority}
            role="assistant"
            content={`${rec.title}\n${rec.action}\n${rec.rationale}`}
          />
        ))
      )}
    </>
  );
}

const ENGAGEMENT_LABELS: Record<PreviousEngagement, string> = {
  no_previous_checkin: "This is my first check-in",
  yes: "Yes, I tried them",
  partially: "I tried some of them",
  no: "No, I didn't get to them",
};

function questionPrompt(question: CheckinQuestion): string {
  if (question.kind === "engagement") {
    return "Before we start — did you try the suggestions from your last check-in?";
  }
  return `Question ${question.index} of ${question.total}: ${question.field.label}\n${question.field.help}`;
}

function describeFeatureAnswer(
  question: Extract<CheckinQuestion, { kind: "feature" }>,
  value: number,
): string {
  const { field } = question;
  if (field.min === 0 && field.max === 1) {
    return value === field.max ? field.highLabel : field.lowLabel;
  }
  return String(value);
}
