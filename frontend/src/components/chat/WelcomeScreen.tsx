interface WelcomeScreenProps {
  onPromptSelect: (prompt: string) => void;
}

/**
 * UI placeholders only — not tied to any real recommendation flow yet.
 * Selecting one simply drops a starter message into the normal send path.
 */
const CATEGORIES = ["Gaming", "Programming", "College", "Design", "Work", "Budget"];

export function WelcomeScreen({ onPromptSelect }: WelcomeScreenProps) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-5 text-center">
      <p className="max-w-xs text-sm text-text-secondary">
        Tell NOVA what you need a laptop for.
      </p>

      <div className="flex flex-col items-center gap-2">
        <span className="text-[11px] uppercase tracking-wide text-text-muted">
          Starting points
        </span>
        <div className="flex max-w-sm flex-wrap items-center justify-center gap-2">
          {CATEGORIES.map((category) => (
            <button
              key={category}
              type="button"
              onClick={() => onPromptSelect(`I need a laptop for ${category.toLowerCase()}.`)}
              className="rounded-full border border-border px-3.5 py-1.5 text-xs text-text-secondary transition-colors hover:border-border-strong hover:text-text-primary"
            >
              {category}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
