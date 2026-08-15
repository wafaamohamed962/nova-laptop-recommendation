import { apiFetch } from "./client";
import type { ChatService } from "./chatService";
import type { ChatRequest, ChatResponse } from "../types/chat";

/**
 * Real backend implementation of ChatService. Not wired up by default
 * (no backend exists yet) — once one does, flip VITE_USE_MOCK_API to
 * "false" in .env and this becomes the active implementation with no
 * other code changes required.
 */
export const httpChatService: ChatService = {
  async sendMessage(request: ChatRequest): Promise<ChatResponse> {
    return apiFetch<ChatResponse>("/chat", {
      method: "POST",
      body: JSON.stringify(request),
    });
  },
};
