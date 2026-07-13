import type {
  ActionCard,
  Citation,
  Identity,
  Order,
  ServiceRequest,
  Ticket,
} from "./types";

const API_BASE = "/api";

export interface HistoryMessage {
  role: string;
  content: string;
}

export interface ChatApiResponse {
  request_id: string;
  conversation_id: string;
  answer: string;
  intent: string;
  citations: Citation[];
  action_taken: string | null;
  action_card: ActionCard | null;
  confirmation_prompt: string | null;
  tools_used: string[];
  iterations: number;
  history: HistoryMessage[];
  evaluation?: Record<string, unknown> | null;
}

interface TokenResponse {
  access_token: string;
  token_type: string;
}

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem("token");
}

async function request<T>(
  path: string,
  init: RequestInit = {},
  authenticated = true
): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");

  if (init.body) {
    headers.set("Content-Type", "application/json");
  }

  if (authenticated) {
    const token = getToken();
    if (token) headers.set("Authorization", "Bearer " + token);
  }

  const response = await fetch(API_BASE + path, { ...init, headers });

  if (!response.ok) {
    let message = "Request failed (" + response.status + ")";
    try {
      const error = (await response.json()) as { detail?: string };
      if (error.detail) message = error.detail;
    } catch {
      // Keep the safe status-based message for non-JSON responses.
    }
    throw new Error(message);
  }

  return (await response.json()) as T;
}

export const api = {
  register(email: string, password: string, customerId: string) {
    return request<Identity>(
      "/auth/register",
      {
        method: "POST",
        body: JSON.stringify({ email, password, customer_id: customerId }),
      },
      false
    );
  },

  login(email: string, password: string) {
    return request<TokenResponse>(
      "/auth/login",
      { method: "POST", body: JSON.stringify({ email, password }) },
      false
    );
  },

  me() {
    return request<Identity>("/auth/me");
  },

  orders() {
    return request<Order[]>("/orders");
  },

  tickets() {
    return request<Ticket[]>("/orders/tickets");
  },

  requests() {
    return request<ServiceRequest[]>("/orders/requests");
  },

  allTickets() {
    return request<Ticket[]>("/orders/admin/tickets");
  },

  chat(
    message: string,
    history: HistoryMessage[] = [],
    conversationId: string | null = null
  ) {
    return request<ChatApiResponse>("/chat", {
      method: "POST",
      body: JSON.stringify({
        message,
        history,
        conversation_id: conversationId,
      }),
    });
  },
};
