import { AppShell } from "../components/layout/AppShell";
import { ChatWindow } from "../components/chat/ChatWindow";
import { useConversation } from "../hooks/useConversation";

export function ChatPage() {
  const { conversation, isSending, error, sendMessage, retry, dismissError } =
    useConversation();

  return (
    <AppShell>
      <ChatWindow
        messages={conversation.messages}
        isSending={isSending}
        error={error}
        onSend={sendMessage}
        onRetry={retry}
        onDismissError={dismissError}
      />
    </AppShell>
  );
}
