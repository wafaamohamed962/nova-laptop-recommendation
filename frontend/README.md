# NOVA — Your Intelligent Laptop Advisor

NOVA is a chat-first frontend for a laptop recommendation assistant. This
package is **frontend only**: there is no backend, model, RAG, or database in
this repository yet. The app runs fully standalone today against a local
mock service and is architected so a real backend can be plugged in later
without touching any UI code.

## Install

```bash
npm install
```

## Run locally

```bash
npm run dev
```

Opens the dev server (default `http://localhost:5173`) with the chat
experience running against the mock service — no backend required.

Other scripts:

```bash
npm run build    # type-check + production build to dist/
npm run preview  # preview the production build locally
npm run lint      # oxlint
```

## Environment variables

Copy `.env.example` to `.env` and adjust as needed:

| Variable              | Purpose                                                                                   | Default |
| ---------------------- | ------------------------------------------------------------------------------------------ | ------- |
| `VITE_API_BASE_URL`    | Base URL of the future backend API. Unused while mocking is on.                            | — |
| `VITE_USE_MOCK_API`    | `"true"` uses the local mock chat service; `"false"` calls `VITE_API_BASE_URL` for real.    | `true` |

Never commit a real `.env` file — only `.env.example` (with placeholder
values) is tracked.

## Project structure

```
src/
├── api/            # Service layer — the only place that knows about HTTP/mocking
│   ├── client.ts          # fetch wrapper, reads VITE_API_BASE_URL
│   ├── chatService.ts     # ChatService interface — the contract the UI depends on
│   ├── httpChatService.ts # real implementation (POSTs to the future backend)
│   ├── mockChatService.ts # local scripted implementation used today
│   ├── mockLaptops.ts     # fixture data used only by the mock service
│   └── index.ts           # exports the active `chatService` based on env vars
├── types/          # Shared domain types (ChatMessage, Conversation, Laptop, Recommendation, ...)
├── hooks/
│   └── useConversation.ts # owns conversation state, calls chatService, exposes send/retry
├── components/
│   ├── chat/              # ChatWindow, MessageList, MessageBubble, ChatInput, etc.
│   ├── recommendations/   # RecommendationList/Card, CategoryBadge
│   └── layout/             # AppShell, Header
├── pages/
│   └── ChatPage.tsx        # composes layout + hook + chat window
├── styles/ + index.css     # Tailwind v4 + design tokens (colors, radii, animations)
└── utils/format.ts         # timestamp/price formatting helpers
```

UI components never import `fetch` or talk to `mockChatService` /
`httpChatService` directly — they only see the `ChatService` interface via
`useConversation`, which imports `chatService` from `src/api/index.ts`.

## How the mock API works

`src/api/mockChatService.ts` implements the same `ChatService` interface a
real backend will. It's intentionally thin: it simulates network latency
and returns one placeholder assistant message per request — just enough to
exercise sending, loading, and rendering. It does not script a
conversation or return recommendations, since the real LangGraph agent and
recommendation pipeline will replace this file outright once built. The
recommendation UI (`components/recommendations/`) and fixture data
(`api/mockLaptops.ts`) already exist and are typed against `Recommendation`
in `types/laptop.ts`, ready to render whatever the real backend eventually
returns on `ChatMessage.recommendations` — the frontend never computes or
hardcodes recommendation logic itself.

## Where the future backend connects

1. Implement the real API (backend, LangGraph, RAG, scoring pipeline) and
   expose a `POST /chat` endpoint that accepts a `ChatRequest` and returns a
   `ChatResponse` (see `src/types/chat.ts`).
2. Set `VITE_API_BASE_URL` to that backend's URL and `VITE_USE_MOCK_API=false`
   in `.env`.
3. `src/api/index.ts` will automatically switch from `mockChatService` to
   `httpChatService` — no component, hook, or type changes required.

If the request/response shape needs to change, update the types in
`src/types/chat.ts` and `src/types/laptop.ts`; both mock and real
implementations, and every component that renders them, are typed against
those shared definitions.
