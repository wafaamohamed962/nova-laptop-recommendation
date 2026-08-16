import type { ChatMessage } from "../../types/chat";
import { formatTimestamp } from "../../utils/format";
import { RecommendationList } from "../recommendations/RecommendationList";

interface MessageBubbleProps {
  message: ChatMessage;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";

  return (
    <div
      className={`animate-message-in flex w-full flex-col gap-1.5 ${
        isUser ? "items-end" : "items-start"
      }`}
    >
      <div
        className={`max-w-[85%] sm:max-w-[75%] ${
          isUser
            ? "rounded-2xl rounded-br-sm border border-accent-500/20 bg-accent-500/10 px-4 py-3 text-text-primary"
            : "rounded-2xl rounded-bl-sm border border-border bg-surface-elevated px-4 py-3 text-text-primary"
        }`}
      >
        <p className="whitespace-pre-wrap text-[15px] leading-relaxed">
          {message.content}
        </p>
      </div>

      {message.recommendations && message.recommendations.length > 0 && (
        <div className="w-full">
          <RecommendationList recommendations={message.recommendations} />
        </div>
      )}

      <div className="flex items-center gap-1.5 px-1 text-xs text-text-muted">
        <span>{formatTimestamp(message.timestamp)}</span>
        {message.status === "sending" && <span>Sending…</span>}
        {message.status === "error" && (
          <span className="text-error-400">Failed to send</span>
        )}
      </div>
    </div>
  );
}
