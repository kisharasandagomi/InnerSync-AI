import { useState } from "react";
import type { PreviousEngagement } from "../services/api";
import { iconSetFor, widgetStyleFor } from "../services/checkinPresentation";
import type { CheckinQuestion as CheckinQuestionType } from "../services/checkinFlow";
import type { FeatureField } from "../services/featureSchema";

interface Props {
  question: CheckinQuestionType;
  onAnswerFeature: (value: number) => void;
  onAnswerEngagement: (value: PreviousEngagement) => void;
}

/**
 * The inline quick-select control shown inside a chat bubble for one
 * check-in question.
 *
 * **Only ever emits a precise value already validated against the field's
 * own bounds** — a chip for a specific integer, or a slider clamped to
 * `[min, max]`. There is no free-text path here and nothing is interpreted;
 * the LLM is not involved in answering these questions at all (see
 * `services/checkinFlow.ts`'s module docstring). This component's only job
 * is presenting the same bounded choices `Field.tsx`'s `ScaleField` always
 * has, just laid out to sit inside a chat bubble instead of a form.
 */
export function CheckinQuestionControl({ question, onAnswerFeature, onAnswerEngagement }: Props) {
  if (question.kind === "engagement") {
    return (
      <div className="mt-3 flex flex-wrap gap-2">
        {question.options.map((opt) => (
          <button
            key={opt.value}
            type="button"
            onClick={() => onAnswerEngagement(opt.value as PreviousEngagement)}
            className="rounded-full border border-line bg-card px-4 py-2 text-base text-ink-soft transition-colors hover:border-accent hover:bg-accent-soft hover:text-ink focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
          >
            {opt.label}
          </button>
        ))}
      </div>
    );
  }

  const { field } = question;
  const isBinary = field.min === 0 && field.max === 1;

  // Binary fields always render as their own two-way toggle, regardless of
  // the assigned widget style — a slider or icon-scale for a yes/no answer
  // would be a worse interaction, not a more varied one.
  if (isBinary) {
    return (
      <div className="mt-3 flex gap-2" role="group" aria-label={field.label}>
        <Chip label={field.lowLabel} onClick={() => onAnswerFeature(field.min)} />
        <Chip label={field.highLabel} onClick={() => onAnswerFeature(field.max)} />
      </div>
    );
  }

  const style = widgetStyleFor(field.name);

  if (style === "icon-scale") {
    const icons = iconSetFor(field.name);
    // Falls back to chips if a field is ever marked icon-scale without a
    // matching icon set — never silently renders nothing.
    if (icons && icons.length === field.max - field.min + 1) {
      return <IconScaleAnswer field={field} icons={icons} onAnswer={onAnswerFeature} />;
    }
  }

  if (style === "slider") {
    return <SliderAnswer field={field} onAnswer={onAnswerFeature} />;
  }

  const values = Array.from({ length: field.max - field.min + 1 }, (_, i) => field.min + i);
  return (
    <div className="mt-3">
      <div className="flex flex-wrap gap-2" role="group" aria-label={field.label}>
        {values.map((v) => (
          <Chip key={v} label={String(v)} onClick={() => onAnswerFeature(v)} />
        ))}
      </div>
      <div className="mt-1.5 flex justify-between text-sm text-ink-faint">
        <span>{field.lowLabel}</span>
        <span>{field.highLabel}</span>
      </div>
    </div>
  );
}

function Chip({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="rounded-full border border-line bg-card px-4 py-2 text-base text-ink-soft transition-colors hover:border-accent hover:bg-accent-soft hover:text-ink focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
    >
      {label}
    </button>
  );
}

/**
 * A face/mood icon per value, for subjective/emotional-register questions
 * (see `checkinPresentation.ts` for the assignment reasoning). Each icon is
 * its own tap target — no drag, no confirm step, same "one tap, one answer"
 * directness as the chip style, just a different visual language for
 * questions about how something *feels* rather than how much of it there is.
 */
function IconScaleAnswer({
  field,
  icons,
  onAnswer,
}: {
  field: FeatureField;
  icons: readonly string[];
  onAnswer: (value: number) => void;
}) {
  return (
    <div className="mt-3">
      <div className="flex flex-wrap gap-2" role="group" aria-label={field.label}>
        {icons.map((icon, i) => {
          const value = field.min + i;
          return (
            <button
              key={value}
              type="button"
              onClick={() => onAnswer(value)}
              aria-label={`${value}`}
              className="flex h-12 w-12 items-center justify-center rounded-full border border-line bg-card text-2xl transition-colors hover:border-accent hover:bg-accent-soft focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
            >
              <span aria-hidden="true">{icon}</span>
            </button>
          );
        })}
      </div>
      <div className="mt-1.5 flex justify-between text-sm text-ink-faint">
        <span>{field.lowLabel}</span>
        <span>{field.highLabel}</span>
      </div>
    </div>
  );
}

/** A wide-range field (only `self_esteem`, 0-30): a slider plus an explicit confirm step. */
function SliderAnswer({
  field,
  onAnswer,
}: {
  field: FeatureField;
  onAnswer: (value: number) => void;
}) {
  const [value, setValue] = useState(Math.round((field.min + field.max) / 2));

  return (
    <div className="mt-3 rounded-lg border border-line bg-card p-3">
      <input
        type="range"
        min={field.min}
        max={field.max}
        step={1}
        value={value}
        onChange={(e) => setValue(Number(e.target.value))}
        className="w-full accent-[var(--color-accent)]"
        aria-label={field.label}
      />
      <div className="mt-1 flex items-center justify-between text-sm text-ink-faint">
        <span>{field.lowLabel}</span>
        <span className="rounded bg-accent-soft px-2 py-0.5 font-medium text-ink">
          {value}
        </span>
        <span>{field.highLabel}</span>
      </div>
      <button
        type="button"
        onClick={() => onAnswer(value)}
        className="mt-3 w-full rounded-md bg-accent px-4 py-2 text-base font-medium text-ink transition-colors hover:bg-accent-strong focus:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2"
      >
        Continue
      </button>
    </div>
  );
}
