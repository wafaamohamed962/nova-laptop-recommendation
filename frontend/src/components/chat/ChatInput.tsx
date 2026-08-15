import { useRef, type KeyboardEvent } from "react";

interface ChatInputProps {
  onSend: (text: string) => void;
  disabled: boolean;
}

export function ChatInput({ onSend, disabled }: ChatInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const submit = () => {
    const value = textareaRef.current?.value ?? "";
    if (!value.trim() || disabled) return;
    onSend(value);
    if (textareaRef.current) {
      textareaRef.current.value = "";
      textareaRef.current.style.height = "auto";
    }
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      submit();
    }
  };

  const handleInput = () => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  };

  return (
    <div className="flex items-end gap-2 rounded-2xl border border-border bg-surface p-2 focus-within:border-border-strong">
      <textarea
        ref={textareaRef}
        rows={1}
        placeholder="Message NOVA…"
        disabled={disabled}
        onKeyDown={handleKeyDown}
        onInput={handleInput}
        className="max-h-40 flex-1 resize-none bg-transparent px-2 py-2 text-[15px] text-text-primary placeholder:text-text-muted focus:outline-none disabled:opacity-50"
      />
      <button
        type="button"
        onClick={submit}
        disabled={disabled}
        aria-label="Send message"
        className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-border text-accent-500 transition-colors hover:border-border-strong hover:text-accent-400 disabled:cursor-not-allowed disabled:opacity-40"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 20 20"
          fill="currentColor"
          className="h-4 w-4"
        >
          <path d="M2.94 2.94a.75.75 0 0 1 .82-.16l14 5.5a.75.75 0 0 1 0 1.44l-14 5.5a.75.75 0 0 1-1-.9l1.4-4.9 7.66-1.68-7.66-1.68-1.4-4.9a.75.75 0 0 1 .18-.72Z" />
        </svg>
      </button>
    </div>
  );
}
