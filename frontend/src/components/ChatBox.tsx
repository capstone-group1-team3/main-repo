"use client";
import { useState, useRef, useEffect } from "react";
import { api, HistoryMessage, ChatApiResponse } from "@/lib/api";
import MessageBubble from "./MessageBubble";
import { ChatMessage } from "@/lib/types";

const CHAT_STORAGE_KEY = "fm_chat_state";
const DEFAULT_MESSAGES: ChatMessage[] = [
  { role: "assistant", content: "Hello! How can I help you today?" },
];

interface StoredChatState {
  messages: ChatMessage[];
  history: HistoryMessage[];
  conversationId: string | null;
}

// localStorage is unavailable during SSR and may contain invalid JSON.
function loadChatState(): StoredChatState | null {
  if (typeof window === "undefined") return null;

  try {
    const raw = window.localStorage.getItem(CHAT_STORAGE_KEY);
    if (!raw) return null;

    const stored = JSON.parse(raw) as Partial<StoredChatState>;
    if (!Array.isArray(stored.messages) || !Array.isArray(stored.history)) {
      return null;
    }

    return {
      messages: stored.messages,
      history: stored.history,
      conversationId:
        typeof stored.conversationId === "string" ? stored.conversationId : null,
    };
  } catch {
    return null;
  }
}

export default function ChatBox() {
  const [messages, setMessages] = useState<ChatMessage[]>(
    () => loadChatState()?.messages ?? DEFAULT_MESSAGES
  );
  const [history, setHistory] = useState<HistoryMessage[]>(
    () => loadChatState()?.history ?? []
  );
  const [conversationId, setConversationId] = useState<string | null>(
    () => loadChatState()?.conversationId ?? null
  );
  const [input, setInput]   = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef             = useRef<HTMLDivElement>(null);
  const skipNextPersistenceRef = useRef(false);

  useEffect(() => {
    if (skipNextPersistenceRef.current) {
      skipNextPersistenceRef.current = false;
      return;
    }
    if (typeof window === "undefined") return;

    try {
      window.localStorage.setItem(
        CHAT_STORAGE_KEY,
        JSON.stringify({ messages, history, conversationId })
      );
    } catch {
      // Storage can be blocked or full; chat should continue in memory.
    }
  }, [messages, history, conversationId]);


  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function send() {
    const msg = input.trim();
    if (!msg || loading) return;
    setInput("");
    setMessages(prev => [...prev, { role: "user", content: msg }]);
    setLoading(true);

    try {
      // Always send conversation_id so backend can resume pending confirmation
      const resp: ChatApiResponse = await api.chat(msg, history, conversationId);

      // Store conversation_id from response (persist across turns)
      if (resp.conversation_id) {
        setConversationId(resp.conversation_id);
      }

      setMessages(prev => [
        ...prev,
        {
          role:                "assistant",
          content:             resp.answer,
          citations:           resp.citations,
          action_taken:        resp.action_taken,
          action_card:         resp.action_card ?? null,
          confirmation_prompt: resp.confirmation_prompt ?? null,
          intent:              resp.intent,
        } as ChatMessage,
      ]);

      if (resp.history) {
        setHistory(resp.history as HistoryMessage[]);
      }

      // If action was executed, clear conversation_id (fresh start)
      if (resp.action_card?.success) {
        setConversationId(null);
      }

    } catch {
      setMessages(prev => [
        ...prev,
        { role: "assistant", content: "Something went wrong. Please try again." },
      ]);
    } finally {
      setLoading(false);
    }
  }

  function newConversation() {
    skipNextPersistenceRef.current = true;
    if (typeof window !== "undefined") {
      try {
        window.localStorage.removeItem(CHAT_STORAGE_KEY);
      } catch {
        // Storage access must never prevent starting a new conversation.
      }
    }

    setMessages(DEFAULT_MESSAGES);
    setHistory([]);
    setConversationId(null);
    setInput("");
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", background: "var(--bg)" }}>
      {/* header */}
      <div style={{ padding: "8px 16px", borderBottom: "1px solid var(--border)",
        display: "flex", justifyContent: "space-between", alignItems: "center",
        background: "var(--panel)" }}>
        <span style={{ fontSize: 13, color: "var(--ink-soft)" }}>AI Support</span>
        <button onClick={newConversation}
          style={{ fontSize: 12, color: "var(--muted)", background: "none",
            border: "none", cursor: "pointer" }}>
          New conversation
        </button>
      </div>

      {/* messages */}
      <div style={{ flex: 1, overflowY: "auto", padding: "20px 16px" }}>
        <div style={{ maxWidth: 760, margin: "0 auto", display: "flex",
          flexDirection: "column", gap: 14 }}>
          {messages.map((m, i) => <MessageBubble key={i} message={m} />)}

          {loading && (
            <div style={{ display: "flex", gap: 5, padding: "8px 14px",
              background: "var(--panel)", border: "1px solid var(--border)",
              borderRadius: "18px 18px 18px 4px", width: "fit-content" }}>
              {[0,1,2].map(i => (
                <div key={i} style={{ width: 7, height: 7, borderRadius: "50%",
                  background: "var(--muted)",
                  animation: `bounce 1s ${i * 0.15}s infinite` }} />
              ))}
            </div>
          )}
          <div ref={bottomRef} />
        </div>
      </div>

      {/* input */}
      <div style={{ padding: "12px 16px", borderTop: "1px solid var(--border)",
        background: "var(--panel)" }}>
        <div style={{ maxWidth: 760, margin: "0 auto", display: "flex",
          gap: 10, alignItems: "flex-end" }}>
          <textarea
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }}
            placeholder="Type your message… (Enter to send)"
            rows={1}
            style={{ flex: 1, resize: "none", maxHeight: 120, overflowY: "auto" }}
          />
          <button className="btn-primary" onClick={send}
            disabled={loading || !input.trim()}
            style={{ padding: "9px 20px", flexShrink: 0 }}>
            Send
          </button>
        </div>
      </div>

      <style>{`
        @keyframes bounce {
          0%, 80%, 100% { transform: scale(0); }
          40%            { transform: scale(1); }
        }
      `}</style>
    </div>
  );
}
