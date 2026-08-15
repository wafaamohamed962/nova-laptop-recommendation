export function Header() {
  return (
    <header className="flex items-center justify-center gap-2.5 border-b border-border px-6 py-4">
      <div className="flex h-7 w-7 items-center justify-center rounded-lg border border-border-strong bg-surface">
        <span className="text-xs font-medium text-accent-500">N</span>
      </div>
      <div className="flex flex-col leading-tight">
        <span className="text-sm font-medium tracking-tight text-text-primary">
          NOVA
        </span>
        <span className="text-[11px] text-text-muted">
          Your Intelligent Laptop Advisor
        </span>
      </div>
    </header>
  );
}
