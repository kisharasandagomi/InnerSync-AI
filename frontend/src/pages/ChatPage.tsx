import { useEffect, useRef, useState, type FormEvent } from "react";
import { Link, useLocation } from "react-router-dom";
import { CheckinQuestionControl } from "../components/CheckinQuestion";
import {
  ApiError,
  getChatHistory,
  sendChatMessage,
  submitAssessment,
  type AssessmentResult,
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
import { checkinGreeting } from "../services/greeting";
import { useAuth } from "../services/auth";

type Mode = "menu" | "talk" | "checkin";

/**
 * Chat page (Module 3 — free-form conversation, plus the chat-delivered
 * check-in).
 *
 * One message list (`messages`) backs both modes, so completing a check-in
 * and continuing to chat freely afterwards reads as one continuous thread,
 * not a reset — see § "Continue chatting after a check-in completes" in
 * `docs/research/methodology.md`. `mode` controls which *input* is active
 * (the bounded quick-select control during a check-in; free text once it's
 * done or in "talk" mode from the start), not which messages are visible.
 *
 * - **"talk"**: free-form Gemini conversation. Still never feeds into the
 *   prediction model (see `backend/app/chatbot/service.py`'s docstring).
 * - **"checkin"**: the 14 questions from `feature_schema.json`, one at a
 *   time, each answered through a bounded control
 *   (`CheckinQuestionControl`) — never free text, never LLM-interpreted.
 *   On completion this calls the **unchanged** `submitAssessment` →
 *   `POST /assessments`, then the page transitions to "talk" automatically
 *   so the student can keep chatting in the same window without navigating
 *   away or restarting.
 */
const INTRO_MESSAGE =
  "Hi, I'm here to talk through how things are going. I'm an AI wellbeing " +
  "check-in, not a counsellor. If you'd rather talk to a person, your " +
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
  const { token, email, displayName } = useAuth();
  const bottomRef = useRef<HTMLDivElement>(null);

  // Backs both modes — see module docstring. Seeded either from real chat
  // history (fresh "talk" entry) or from the check-in's own question/answer
  // bubbles (fresh "checkin" entry); never both at once.
  const [messages, setMessages] = useState<LocalMessage[]>([]);
  const [historyLoaded, setHistoryLoaded] = useState(false);
  const [draft, setDraft] = useState("");
  const [talkError, setTalkError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);

  // --- "checkin"-specific state ---
  const [checkinState, setCheckinState] = useState<CheckinState>(startCheckin);
  const [checkinBusy, setCheckinBusy] = useState(false);
  const [checkinError, setCheckinError] = useState<string | null>(null);
  const [checkinResult, setCheckinResult] = useState<AssessmentResult | null>(null);

  // Fresh entry into "talk" mode (from the menu, not from a completed
  // check-in) loads real history. Guarded on an empty transcript, so a
  // post-check-in transition — where `messages` already holds the check-in
  // thread — never overwrites it with unrelated past conversation.
  useEffect(() => {
    if (mode !== "talk" || messages.length > 0 || historyLoaded || !token) return;
    setHistoryLoaded(true);
    getChatHistory(token)
      .then((items) => {
        setMessages([
          { id: "intro", role: "assistant", content: INTRO_MESSAGE },
          ...items.map((m) => ({ id: String(m.id), role: m.role, content: m.content })),
        ]);
      })
      .catch((err) => {
        setTalkError(
          err instanceof ApiError
            ? err.message
            : "Could not reach the server. Is the backend running?",
        );
        setMessages([{ id: "intro", role: "assistant", content: INTRO_MESSAGE }]);
      });
  }, [mode, messages.length, historyLoaded, token]);

  // Fresh entry into "checkin" mode: a personalized greeting (a fixed
  // template — see services/greeting.ts — not an LLM generation), then the
  // first question.
  useEffect(() => {
    if (mode !== "checkin" || messages.length > 0) return;
    const question = currentQuestion(checkinState);
    if (question) {
      setMessages([
        { id: "greeting", role: "assistant", content: checkinGreeting(displayName, email ?? "") },
        { id: "q-0", role: "assistant", content: questionPrompt(question) },
      ]);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, checkinResult]);

  async function handleTalkSubmit(event: FormEvent) {
    event.preventDefault();
    const content = draft.trim();
    if (!content || !token || sending) return;

    setTalkError(null);
    setSending(true);
    setDraft("");
    setMessages((prev) => [...prev, { id: `local-${Date.now()}`, role: "user", content }]);
    try {
      const result = await sendChatMessage(content, token);
      setMessages((prev) => [
        ...prev.filter((m) => !m.id.startsWith("local-")),
        { id: String(result.user_message.id), role: "user", content: result.user_message.content },
        {
          id: String(result.assistant_message.id),
          role: "assistant",
          content: result.assistant_message.content,
        },
      ]);
    } catch (err) {
      setTalkError(
        err instanceof ApiError
          ? err.message
          : "Could not reach the server. Is the backend running?",
      );
      setDraft(content);
      setMessages((prev) => prev.filter((m) => !m.id.startsWith("local-")));
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
      setMessages((prev) => [
        ...prev,
        { id: `q-${prev.length}`, role: "assistant", content: questionPrompt(question) },
      ]);
    }
  }

  function handleEngagementAnswer(value: PreviousEngagement) {
    const label = ENGAGEMENT_LABELS[value] ?? value;
    setMessages((prev) => [...prev, { id: "a-engagement", role: "user", content: label }]);
    advanceCheckin(answerEngagement(checkinState, value));
  }

  function handleFeatureAnswer(value: number) {
    const question = currentQuestion(checkinState);
    if (!question || question.kind !== "feature") return;
    const label = describeFeatureAnswer(question, value);
    setMessages((prev) => [
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
      setMessages((prev) => [...prev, ...resultMessages(result)]);
      // Automatic hand-off to free-form chat: the same thread continues,
      // now backed by the real chat endpoint instead of the check-in state
      // machine. No restart, no navigation — see module docstring.
      setMode("talk");
      setHistoryLoaded(true); // messages is non-empty already; skip the history fetch
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
    setMessages(
      question
        ? [
            { id: "greeting", role: "assistant", content: checkinGreeting(displayName, email ?? "") },
            { id: "q-0", role: "assistant", content: questionPrompt(question) },
          ]
        : [],
    );
    setMode("checkin");
  }

  if (mode === "menu") {
    return <ModeMenu onChoose={setMode} />;
  }

  const activeQuestion =
    mode === "checkin" && !checkinResult ? currentQuestion(checkinState) : null;

  return (
    <div className="chat-shell flex h-[calc(100vh-7rem)] flex-col">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm uppercase tracking-wider text-ink-faint">
            {activeQuestion ? "Check-in" : "Chat"}
          </p>
          <h1 className="mt-1 text-xl font-semibold tracking-tight text-ink">
            {activeQuestion ? "Let's talk through your check-in" : "Talk it through"}
          </h1>
        </div>
        <button
          type="button"
          onClick={() => setMode("menu")}
          className="rounded-md border border-line px-3 py-1.5 text-sm text-ink-soft transition-colors hover:bg-accent-soft hover:text-ink focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
        >
          Change mode
        </button>
      </div>

      {activeQuestion?.kind === "feature" && (
        <p className="mt-3 text-sm font-medium text-ink">
          Question {activeQuestion.index} of {activeQuestion.total}
        </p>
      )}

      <div className="mt-4 flex-1 space-y-5 overflow-y-auto rounded-2xl border border-line bg-[var(--chat-surface)] p-6 sm:p-8">
        {messages.map((message, i) => (
          <div key={message.id}>
            <Bubble role={message.role} content={message.content} />
            {/* The control only ever appears under the single most recent
                assistant message, and only while a check-in question is
                still unanswered. */}
            {message.role === "assistant" &&
              i === messages.length - 1 &&
              !checkinBusy &&
              activeQuestion && (
                <CheckinQuestionControl
                  question={activeQuestion}
                  onAnswerFeature={handleFeatureAnswer}
                  onAnswerEngagement={handleEngagementAnswer}
                />
              )}
          </div>
        ))}
        {checkinBusy && <p className="text-base text-ink-faint">Working out what this means…</p>}
        <div ref={bottomRef} />
      </div>

      {talkError && (
        <p className="mt-3 rounded-md border border-line bg-accent-soft/40 p-3 text-base text-ink-soft">
          {talkError}
        </p>
      )}
      {checkinError && (
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
            className="rounded-full border border-accent bg-accent-soft px-5 py-2.5 text-base font-medium text-ink transition-colors hover:bg-accent-soft/70 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent disabled:cursor-not-allowed disabled:opacity-50"
          >
            {sending ? "Sending…" : "Send"}
          </button>
        </form>
      )}

      {checkinResult && (
        <div className="mt-3 flex flex-wrap items-center gap-4">
          <button
            type="button"
            onClick={startOver}
            className="rounded-md border border-line px-4 py-2 text-base text-ink-soft transition-colors hover:bg-accent-soft hover:text-ink focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
          >
            Start another check-in
          </button>
          <Link
            to="/progress"
            className="text-base text-ink-soft underline-offset-4 hover:text-ink hover:underline"
          >
            See My Trends
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
          <p className="text-base font-semibold text-ink">Start a check-in</p>
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
        className={`max-w-[85%] whitespace-pre-line rounded-2xl px-5 py-3 text-base leading-7 sm:max-w-[70%] ${
          isUser
            ? "bg-accent-strong text-ink"
            : "border border-line/60 bg-[var(--chat-bubble-assistant)] text-ink"
        }`}
      >
        {content}
      </p>
    </div>
  );
}

/**
 * Turns the assessment response into sequential local messages.
 *
 * Every piece of text here — the explanation paragraph, the escalation
 * message, the affirmation, each recommendation's title/action/rationale,
 * and the comparative trend message — is used **exactly as
 * `POST /assessments` returned it**. It already passed the safety gate
 * server-side; nothing here re-words, truncates, or re-generates any of it,
 * the same discipline `ResultsPage.tsx` follows for the slider-form path.
 *
 * `comparative_trend_message` is deliberately placed **last** — after the
 * escalation signpost/affirmation/recommendations, not competing with them
 * for the first thing a student reads. The backend has already coordinated
 * its content with escalation (a brief, secondary note when escalation is
 * also firing, never a second heavy message stacked on top) — this
 * component's only job is to keep that same secondary positioning visually,
 * by ordering it last rather than, say, right after the level statement.
 */
function resultMessages(result: AssessmentResult): LocalMessage[] {
  const messages: LocalMessage[] = [
    { id: "r-level", role: "assistant", content: `Things look ${result.stress_level_label} right now.` },
    { id: "r-explanation", role: "assistant", content: result.explanation },
  ];
  if (result.is_escalation) {
    messages.push({ id: "r-escalation", role: "assistant", content: result.escalation_message ?? "" });
  } else if (result.is_affirmation) {
    messages.push({ id: "r-affirmation", role: "assistant", content: result.affirmation ?? "" });
  } else {
    for (const rec of result.recommendations) {
      messages.push({
        id: `r-rec-${rec.priority}`,
        role: "assistant",
        content: `${rec.title}\n${rec.action}\n${rec.rationale}`,
      });
    }
  }
  if (result.comparative_trend_message) {
    messages.push({
      id: "r-comparative",
      role: "assistant",
      content: result.comparative_trend_message,
    });
  }
  return messages;
}

const ENGAGEMENT_LABELS: Record<PreviousEngagement, string> = {
  no_previous_checkin: "This is my first check-in",
  yes: "Yes, I tried them",
  partially: "I tried some of them",
  no: "No, I didn't get to them",
};

function questionPrompt(question: CheckinQuestion): string {
  if (question.kind === "engagement") {
    return "Before we start, did you try the suggestions from your last check-in?";
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
