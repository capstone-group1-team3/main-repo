"use client";
import { ChatMessage } from "@/lib/types";

interface ActionCard {
  action:     string;
  request_id?: string | null;
  ticket_id?:  string | null;
  order_id?:   string | null;
  amount?:     number | null;
  status?:     string | null;
  next_step?:  string | null;
  reason?:     string | null;
  success?:    boolean;
}

function ActionCardView({ card }: { card: ActionCard }) {
  const success = card.success !== false;
  const label   = card.action.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
  const color   = success ? { bg: "#f0fdf4", border: "#86efac", icon: "✓", ic: "#16a34a" }
                          : { bg: "#fef2f2", border: "#fca5a5", icon: "✗", ic: "#dc2626" };

  return (
    <div style={{ border: `1px solid ${color.border}`, background: color.bg,
      borderRadius: 10, padding: "12px 16px", marginTop: 8, fontSize: 13 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
        <span style={{ fontWeight: 700, fontSize: 18, color: color.ic }}>{color.icon}</span>
        <span style={{ fontWeight: 700, color: color.ic }}>{label}</span>
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
        {card.order_id   && <Row k="Order"      v={card.order_id} />}
        {card.request_id && <Row k="Request ID" v={card.request_id} />}
        {card.ticket_id  && <Row k="Ticket ID"  v={card.ticket_id} />}
        {card.amount     && <Row k="Amount"     v={`$${card.amount.toFixed(2)}`} />}
        {card.status     && <Row k="Status"     v={card.status.replace(/_/g, " ")} />}
        {card.next_step  && (
          <div style={{ marginTop: 6, padding: "6px 10px", background: "rgba(0,0,0,.04)",
            borderRadius: 6, fontSize: 12, color: "#374151" }}>
            📌 {card.next_step}
          </div>
        )}
        {card.reason && !success && (
          <div style={{ marginTop: 6, fontSize: 12, color: "#991b1b" }}>
            Reason: {card.reason}
          </div>
        )}
      </div>
    </div>
  );
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12 }}>
      <span style={{ color: "#6b7280" }}>{k}</span>
      <span style={{ fontWeight: 600, color: "#111827" }}>{v}</span>
    </div>
  );
}

function ConfirmationBanner() {
  return (
    <div style={{ background: "#fffbeb", border: "1px solid #fbbf24",
      borderRadius: 8, padding: "8px 12px", marginTop: 8, fontSize: 12,
      color: "#92400e", display: "flex", alignItems: "center", gap: 6 }}>
      ⚠ Reply <strong>yes</strong> to confirm or <strong>no</strong> to cancel.
    </div>
  );
}

export default function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";

  return (
    <div style={{ display: "flex", justifyContent: isUser ? "flex-end" : "flex-start" }}>
      <div style={{
        maxWidth: "72%",
        padding: "10px 14px",
        borderRadius: isUser ? "18px 18px 4px 18px" : "18px 18px 18px 4px",
        background: isUser ? "var(--accent)" : "var(--panel)",
        color: isUser ? "#fff" : "var(--ink)",
        border: isUser ? "none" : "1px solid var(--border)",
        fontSize: 14,
        lineHeight: 1.65,
        whiteSpace: "pre-wrap",
        wordBreak: "break-word",
      }}>
        {/* Message text */}
        <span>{message.content}</span>

        {/* Action card */}
        {message.action_card && (
          <ActionCardView card={message.action_card as ActionCard} />
        )}

        {/* Confirmation banner */}
        {message.confirmation_prompt && (
          <ConfirmationBanner />
        )}

        {/* Clean source labels — never raw chunk IDs */}
        {message.citations && message.citations.length > 0 && (
          <div style={{ marginTop: 8, paddingTop: 6,
            borderTop: `1px solid ${isUser ? "rgba(255,255,255,0.2)" : "var(--border)"}`,
            fontSize: 11, color: isUser ? "rgba(255,255,255,0.7)" : "var(--muted)" }}>
            {message.citations
              .map((c: any) => c.source || c.chunk_id)
              .filter(Boolean)
              .filter((v: string, i: number, a: string[]) => a.indexOf(v) === i)
              .map((src: string, i: number) => (
                <span key={i} style={{ marginRight: 8 }}>📄 {src}</span>
              ))}
          </div>
        )}
      </div>
    </div>
  );
}
