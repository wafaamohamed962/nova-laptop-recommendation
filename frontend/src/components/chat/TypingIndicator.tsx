export function TypingIndicator() {
  return (
    <div className="flex w-fit items-center gap-1.5 rounded-2xl rounded-bl-sm border border-border bg-surface-elevated px-4 py-3.5">
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="animate-typing-dot h-1.5 w-1.5 rounded-full bg-text-muted"
          style={{ animationDelay: `${i * 160}ms` }}
        />
      ))}
    </div>
  );
}
