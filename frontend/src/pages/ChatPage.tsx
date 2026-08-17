import { useEffect, useRef, useState, type FormEvent } from "react";
import {
  ApiError,
  getChatHistory,
  sendChatMessage,
  type ChatMessageItem,
} from "../services/api";
import { useAuth } from "../services/auth";

/**
 * Chat page (Module 3 — Conversational Interaction Layer).
 *
 * A single message list plus an input box. This is data collection and
 * supportive conversation only: nothing on this page (or in the endpoints it
 * calls) feeds into the stress-prediction model or `POST /assessments` — see
 * `backend/app/chatbot/service.py`'s module docstring for the boundary this
 * mirrors on the server.
 *
 * The very first bubble is fixed, static text, not a message from the
 * conversation history or from Gemini — it exists purely so the "this is an
 * AI check-in, not a counsellor" disclaimer is guaranteed to appear, rather
 * than depending on the model remembering to say it (the system prompt also
 * asks it to, but this page does not rely on that alone).
 */
const INTRO_MESSAGE =
  "Hi, I'm here to talk through how things are going. I'm an AI wellbeing " +
  "check-in, not a counsellor — if you'd rather talk to a person, your " +
  "university wellbeing service is a great place to start. What's on your mind?";

export function ChatPage() {
  const { token } = useAuth();
  const [history, setHistory] = useState<ChatMessageItem[] | null>(null);
  const [draft, setDraft] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!token) return;
    getChatHistory(token)
      .then(setHistory)
      .catch((err) => {
        setError(
          err instanceof ApiError
            ? err.message
            : "Could not reach the server. Is the backend running?",
        );
        setHistory([]);
      });
  }, [token]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [history]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const content = draft.trim();
    if (!content || !token || sending) return;

    setError(null);
    setSending(true);
    setDraft("");
    try {
      const result = await sendChatMessage(content, token);
      setHistory((prev) => [...(prev ?? []), result.user_message, result.assistant_message]);
    } catch (err) {
      // A 429 (session length cap) or 503 (chat not configured) both carry a
      // clear, already-plain-language detail message from the backend —
      // shown as-is rather than re-worded here.
      setError(
        err instanceof ApiError
          ? err.message
          : "Could not reach the server. Is the backend running?",
      );
      setDraft(content); // let the student retry without retyping
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="flex h-[calc(100vh-12rem)] flex-col">
      <p className="text-xs uppercase tracking-wider text-ink-faint">Chat</p>
      <h1 className="mt-2 text-xl font-semibold tracking-tight text-ink">
        Talk it through
      </h1>

      <div className="mt-6 flex-1 space-y-3 overflow-y-auto rounded-lg border border-line bg-card p-4">
        <Bubble role="assistant" content={INTRO_MESSAGE} />
        {history === null && (
          <p className="text-sm text-ink-faint">Loading your conversation…</p>
        )}
        {history?.map((message) => (
          <Bubble key={message.id} role={message.role} content={message.content} />
        ))}
        <div ref={bottomRef} />
      </div>

      {error && (
        <p className="mt-3 rounded-md border border-line bg-accent-soft/40 p-3 text-sm text-ink-soft">
          {error}
        </p>
      )}

      <form onSubmit={handleSubmit} className="mt-3 flex gap-2">
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
          className="flex-1 rounded-md border border-line bg-surface px-3 py-2 text-[15px] text-ink focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
        />
        <button
          type="submit"
          disabled={sending || draft.trim().length === 0}
          className="rounded-md border border-accent bg-accent-soft px-4 py-2 text-sm font-medium text-accent-strong transition-colors hover:bg-accent-soft/70 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent disabled:cursor-not-allowed disabled:opacity-50"
        >
          {sending ? "Sending…" : "Send"}
        </button>
      </form>
    </div>
  );
}

function Bubble({ role, content }: { role: "user" | "assistant"; content: string }) {
  const isUser = role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <p
        className={`max-w-[80%] whitespace-pre-line rounded-lg px-4 py-2 text-[15px] leading-6 ${
          isUser
            ? "bg-accent-strong text-white"
            : "border border-line bg-surface text-ink"
        }`}
      >
        {content}
      </p>
    </div>
  );
}
