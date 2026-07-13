"use client";
import { useState, useRef, useEffect } from "react";
import { api, HistoryMessage, ChatApiResponse } from "@/lib/api";
import MessageBubble from "./MessageBubble";
import { ChatMessage } from "@/lib/types";

export default function ChatBox() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    { role: "assistant", content: "Hello! How can I help you today?" },
  ]);
  const [history, setHistory]             = useState<HistoryMessage[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [input, setInput]   = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef             = useRef<HTMLDivElement>(null);

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
    setMessages([{ role: "assistant", content: "Hello! How can I help you today?" }]);
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
