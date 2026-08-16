import type { Recommendation } from "./laptop";

/**
 * Chat/conversation types. These define the contract between the frontend
 * and whatever backend eventually drives the conversation (LangGraph, RAG,
 * etc.) — the frontend only renders what it's given.
 */

export type MessageRole = "user" | "assistant" | "system";

export type MessageStatus = "sending" | "sent" | "error";

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  /** ISO 8601 timestamp. */
  timestamp: string;
  status?: MessageStatus;
  /** Present on a final assistant answer that includes laptop picks. */
  recommendations?: Recommendation[];
}

export interface Conversation {
  id: string;
  messages: ChatMessage[];
  createdAt: string;
  updatedAt: string;
}

export interface ChatRequest {
  /** null on the first message of a new conversation. */
  conversationId: string | null;
  message: string;
}

export interface ChatResponse {
  conversationId: string;
  message: ChatMessage;
  /** True when the backend considers the conversation resolved. */
  done?: boolean;
}
