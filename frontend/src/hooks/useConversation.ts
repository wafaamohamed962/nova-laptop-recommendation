import { useCallback, useReducer } from "react";
import { chatService } from "../api";
import { ApiError } from "../api/client";
import type { ChatMessage, Conversation } from "../types/chat";

interface State {
  conversation: Conversation;
  isSending: boolean;
  error: string | null;
}

type Action =
  | { type: "SEND_START"; userMessage: ChatMessage }
  | {
      type: "SEND_SUCCESS";
      userMessageId: string;
      conversationId: string;
      assistantMessage: ChatMessage;
    }
  | { type: "SEND_ERROR"; userMessageId: string; error: string }
  | { type: "DISMISS_ERROR" };

function createEmptyConversation(): Conversation {
  const now = new Date().toISOString();
  return {
    id: crypto.randomUUID(),
    messages: [],
    createdAt: now,
    updatedAt: now,
  };
}

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case "SEND_START":
      return {
        ...state,
        isSending: true,
        error: null,
        conversation: {
          ...state.conversation,
          messages: [...state.conversation.messages, action.userMessage],
          updatedAt: new Date().toISOString(),
        },
      };
    case "SEND_SUCCESS":
      return {
        ...state,
        isSending: false,
        conversation: {
          ...state.conversation,
          id: action.conversationId,
          messages: [
            ...state.conversation.messages.map((message) =>
              message.id === action.userMessageId
                ? { ...message, status: "sent" as const }
                : message,
            ),
            action.assistantMessage,
          ],
          updatedAt: new Date().toISOString(),
        },
      };
    case "SEND_ERROR":
      return {
        ...state,
        isSending: false,
        error: action.error,
        conversation: {
          ...state.conversation,
          messages: state.conversation.messages.map((message) =>
            message.id === action.userMessageId
              ? { ...message, status: "error" as const }
              : message,
          ),
        },
      };
    case "DISMISS_ERROR":
      return { ...state, error: null };
    default:
      return state;
  }
}

export function useConversation() {
  const [state, dispatch] = useReducer(reducer, undefined, () => ({
    conversation: createEmptyConversation(),
    isSending: false,
    error: null,
  }));

  const send = useCallback(
    async (text: string) => {
      const trimmed = text.trim();
      if (!trimmed || state.isSending) return;

      const userMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: "user",
        content: trimmed,
        timestamp: new Date().toISOString(),
        status: "sending",
      };

      dispatch({ type: "SEND_START", userMessage });

      try {
        const response = await chatService.sendMessage({
          conversationId: state.conversation.messages.length
            ? state.conversation.id
            : null,
          message: trimmed,
        });

        dispatch({
          type: "SEND_SUCCESS",
          userMessageId: userMessage.id,
          conversationId: response.conversationId,
          assistantMessage: response.message,
        });
      } catch (err) {
        const message =
          err instanceof ApiError
            ? err.message
            : "Something went wrong while reaching NOVA. Please try again.";
        dispatch({ type: "SEND_ERROR", userMessageId: userMessage.id, error: message });
      }
    },
    [state.conversation.id, state.conversation.messages.length, state.isSending],
  );

  const retry = useCallback(() => {
    const lastFailed = [...state.conversation.messages]
      .reverse()
      .find((message) => message.status === "error");
    if (lastFailed) {
      void send(lastFailed.content);
    }
  }, [state.conversation.messages, send]);

  const dismissError = useCallback(() => dispatch({ type: "DISMISS_ERROR" }), []);

  return {
    conversation: state.conversation,
    isSending: state.isSending,
    error: state.error,
    sendMessage: send,
    retry,
    dismissError,
  };
}
