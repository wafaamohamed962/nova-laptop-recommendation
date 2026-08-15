import type { ChatRequest, ChatResponse } from "../types/chat";

/**
 * Contract every chat backend implementation (mock or real) must satisfy.
 * UI components and hooks depend only on this interface, never on a
 * concrete implementation — see api/index.ts for how the active
 * implementation is selected.
 */
export interface ChatService {
  sendMessage(request: ChatRequest): Promise<ChatResponse>;
}
