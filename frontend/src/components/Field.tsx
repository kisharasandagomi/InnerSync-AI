import type { FeatureField } from "../services/featureSchema";

interface ScaleFieldProps {
  field: FeatureField;
  value: number;
  onChange: (name: string, value: number) => void;
}

/**
 * One questionnaire item.
 *
 * Binary items render as a two-way choice; everything else as a labelled slider.
 * The current value is always shown numerically as well as positionally, so the
 * answer is unambiguous without relying on the slider thumb.
 */
export function ScaleField({ field, value, onChange }: ScaleFieldProps) {
  const isBinary = field.min === 0 && field.max === 1;
  const inputId = `field-${field.name}`;

  return (
    <fieldset className="border-b border-line py-5 last:border-b-0">
      <legend className="sr-only">{field.label}</legend>
      <label htmlFor={inputId} className="block text-sm font-medium text-ink">
        {field.label}
      </label>
      <p className="mt-1 text-xs text-ink-faint">{field.help}</p>

      {isBinary ? (
        <div className="mt-3 flex gap-2" role="group" aria-label={field.label}>
          {[
            { v: 0, text: field.lowLabel },
            { v: 1, text: field.highLabel },
          ].map((opt) => (
            <button
              key={opt.v}
              type="button"
              aria-pressed={value === opt.v}
              onClick={() => onChange(field.name, opt.v)}
              className={`rounded-md border px-4 py-1.5 text-sm transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-accent ${
                value === opt.v
                  ? "border-accent bg-accent-soft font-medium text-accent-strong"
                  : "border-line text-ink-soft hover:bg-accent-soft/50"
              }`}
            >
              {opt.text}
            </button>
          ))}
          {/* Keeps the value present for form serialisation and tests. */}
          <input type="hidden" id={inputId} name={field.name} value={value} readOnly />
        </div>
      ) : (
        <div className="mt-3">
          <input
            id={inputId}
            name={field.name}
            type="range"
            min={field.min}
            max={field.max}
            step={1}
            value={value}
            onChange={(e) => onChange(field.name, Number(e.target.value))}
            className="w-full accent-[var(--color-accent)]"
            aria-describedby={`${inputId}-value`}
          />
          <div className="mt-1 flex items-center justify-between text-xs text-ink-faint">
            <span>{field.lowLabel}</span>
            <span
              id={`${inputId}-value`}
              className="rounded bg-accent-soft px-2 py-0.5 font-medium text-accent-strong"
            >
              {value}
            </span>
            <span>{field.highLabel}</span>
          </div>
        </div>
      )}
    </fieldset>
  );
}
