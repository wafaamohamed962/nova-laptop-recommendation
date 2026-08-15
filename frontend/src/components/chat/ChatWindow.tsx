import type { ChatMessage } from "../../types/chat";
import { ChatInput } from "./ChatInput";
import { ErrorBanner } from "./ErrorBanner";
import { MessageList } from "./MessageList";
import { WelcomeScreen } from "./WelcomeScreen";

interface ChatWindowProps {
  messages: ChatMessage[];
  isSending: boolean;
  error: string | null;
  onSend: (text: string) => void;
  onRetry: () => void;
  onDismissError: () => void;
}

export function ChatWindow({
  messages,
  isSending,
  error,
  onSend,
  onRetry,
  onDismissError,
}: ChatWindowProps) {
  const hasMessages = messages.length > 0;

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      {hasMessages ? (
        <MessageList messages={messages} isSending={isSending} />
      ) : (
        <WelcomeScreen onPromptSelect={onSend} />
      )}

      <div className="flex flex-col gap-3 pb-6 pt-2">
        {error && (
          <ErrorBanner message={error} onRetry={onRetry} onDismiss={onDismissError} />
        )}
        <ChatInput onSend={onSend} disabled={isSending} />
      </div>
    </div>
  );
}
