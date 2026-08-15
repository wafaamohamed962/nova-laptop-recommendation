import type { ChatService } from "./chatService";
import type { ChatRequest, ChatResponse } from "../types/chat";

/**
 * Minimal local stand-in for the future backend/AI agent — just enough to
 * exercise the send/receive UI (loading state, message rendering) without
 * a server. Deliberately does not script a conversation or return
 * recommendations: the real LangGraph agent and recommendation pipeline
 * will replace this file entirely, so nothing here is worth building out
 * further in the meantime.
 */

const SIMULATED_LATENCY_MS = [500, 900] as const;

function delay(): Promise<void> {
  const [min, max] = SIMULATED_LATENCY_MS;
  const ms = min + Math.random() * (max - min);
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export const mockChatService: ChatService = {
  async sendMessage(request: ChatRequest): Promise<ChatResponse> {
    await delay();

    return {
      conversationId: request.conversationId ?? crypto.randomUUID(),
      message: {
        id: crypto.randomUUID(),
        role: "assistant",
        content:
          "This is a placeholder response — NOVA isn't connected to the real recommendation engine yet.",
        timestamp: new Date().toISOString(),
        status: "sent",
      },
    };
  },
};
