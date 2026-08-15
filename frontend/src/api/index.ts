import type { ChatService } from "./chatService";
import { mockChatService } from "./mockChatService";
import { httpChatService } from "./httpChatService";

/**
 * Single point of truth for which ChatService implementation is active.
 * The rest of the app imports `chatService` from here and never touches
 * mockChatService/httpChatService directly, so going live with the real
 * backend later is a one-line change (VITE_USE_MOCK_API=false).
 */
const useMock = import.meta.env.VITE_USE_MOCK_API !== "false";

export const chatService: ChatService = useMock
  ? mockChatService
  : httpChatService;

export type { ChatService } from "./chatService";
export { ApiError } from "./client";
