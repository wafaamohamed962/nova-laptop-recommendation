interface ErrorBannerProps {
  message: string;
  onRetry: () => void;
  onDismiss: () => void;
}

export function ErrorBanner({ message, onRetry, onDismiss }: ErrorBannerProps) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-xl border border-error-500/30 bg-error-500/10 px-4 py-3 text-sm text-error-400">
      <span>{message}</span>
      <div className="flex shrink-0 items-center gap-3">
        <button
          type="button"
          onClick={onRetry}
          className="font-medium underline-offset-2 hover:underline"
        >
          Retry
        </button>
        <button
          type="button"
          onClick={onDismiss}
          aria-label="Dismiss error"
          className="text-text-muted hover:text-text-secondary"
        >
          ✕
        </button>
      </div>
    </div>
  );
}
