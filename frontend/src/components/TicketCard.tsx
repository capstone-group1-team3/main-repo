"use client";
import { Ticket, Order, ServiceRequest, OrderItem } from "@/lib/types";

// ── Status badge ─────────────────────────────────────────────────────────────
function StatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    delivered:     "approved",
    canceled:      "rejected",
    open:          "open",
    pending_proof: "pending",
    approved:      "approved",
    resolved:      "resolved",
    rejected:      "rejected",
    shipped:       "pending",
    processing:    "open",
  };
  const cls = map[status] ?? "open";
  return <span className={`badge badge-${cls}`}>{status}</span>;
}

// ── Divider ───────────────────────────────────────────────────────────────────
function Divider() {
  return (
    <hr
      style={{
        border: "none",
        borderTop: "1px solid var(--border-soft)",
        margin: "10px 0",
      }}
    />
  );
}

// ── OrderCard — full details ──────────────────────────────────────────────────
export function OrderCard({ order }: { order: Order }) {
  const statusColor =
    order.status === "delivered"
      ? "approved"
      : order.status === "canceled"
      ? "rejected"
      : order.status === "shipped"
      ? "pending"
      : "open";

  const isLate =
    order.delivered_date &&
    order.estimated_delivery_date &&
    new Date(order.delivered_date) > new Date(order.estimated_delivery_date);

  const validItems = (order.items ?? []).filter(
    (it) => it && it.product_id
  );

  return (
    <div className="card" style={{ marginBottom: 14 }}>
      {/* ── Header ── */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 10,
        }}
      >
        <div>
          <span style={{ fontWeight: 700, fontSize: 15 }}>{order.order_id}</span>
          {isLate && (
            <span
              style={{
                marginLeft: 10,
                fontSize: 11,
                color: "var(--warning)",
                background: "#fef3c7",
                borderRadius: 4,
                padding: "1px 6px",
              }}
            >
              ⚠ Late delivery
            </span>
          )}
        </div>
        <span className={`badge badge-${statusColor}`}>{order.status}</span>
      </div>

      {/* ── Dates ── */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr 1fr",
          gap: 8,
          marginBottom: 10,
        }}
      >
        <div>
          <p style={{ fontSize: 10, color: "var(--muted)", marginBottom: 2 }}>
            ORDERED
          </p>
          <p style={{ fontSize: 13, fontWeight: 500 }}>
            {order.purchase_date ?? "—"}
          </p>
        </div>
        <div>
          <p style={{ fontSize: 10, color: "var(--muted)", marginBottom: 2 }}>
            EST. DELIVERY
          </p>
          <p style={{ fontSize: 13, fontWeight: 500 }}>
            {order.estimated_delivery_date ?? "—"}
          </p>
        </div>
        <div>
          <p style={{ fontSize: 10, color: "var(--muted)", marginBottom: 2 }}>
            DELIVERED
          </p>
          <p
            style={{
              fontSize: 13,
              fontWeight: 500,
              color: order.delivered_date
                ? "var(--success, #16a34a)"
                : "var(--muted)",
            }}
          >
            {order.delivered_date ?? "Pending"}
          </p>
        </div>
      </div>

      {/* ── Payment ── */}
      {(order.payment_type || order.payment_value) && (
        <>
          <Divider />
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: 10,
            }}
          >
            <div>
              <p style={{ fontSize: 10, color: "var(--muted)", marginBottom: 2 }}>
                PAYMENT METHOD
              </p>
              <p style={{ fontSize: 13, fontWeight: 500 }}>
                {order.payment_type ?? "—"}
                {order.installments && order.installments > 1
                  ? ` · ${order.installments} installments`
                  : ""}
              </p>
            </div>
            <div style={{ textAlign: "right" }}>
              <p style={{ fontSize: 10, color: "var(--muted)", marginBottom: 2 }}>
                TOTAL
              </p>
              <p style={{ fontSize: 16, fontWeight: 700, color: "var(--ink)" }}>
                ${order.payment_value?.toFixed(2) ?? "—"}
              </p>
            </div>
          </div>
        </>
      )}

      {/* ── Items ── */}
      {validItems.length > 0 && (
        <>
          <Divider />
          <p
            style={{
              fontSize: 10,
              textTransform: "uppercase",
              letterSpacing: ".1em",
              color: "var(--muted)",
              marginBottom: 6,
            }}
          >
            Items in this order ({validItems.length})
          </p>
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {validItems.map((item, i) => (
              <div
                key={i}
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  background: "var(--border-soft, #f1f5f9)",
                  borderRadius: 8,
                  padding: "8px 12px",
                }}
              >
                <div>
                  <p style={{ fontSize: 13, fontWeight: 600 }}>
                    {item.product_name ?? item.product_id}
                  </p>
                  <p style={{ fontSize: 11, color: "var(--muted)" }}>
                    {item.category ?? "—"} · Qty: {item.quantity}
                  </p>
                </div>
                <p style={{ fontSize: 13, fontWeight: 600 }}>
                  ${((item.unit_price ?? 0) * (item.quantity ?? 1)).toFixed(2)}
                </p>
              </div>
            ))}
          </div>
        </>
      )}

      {validItems.length === 0 && (
        <p style={{ fontSize: 12, color: "var(--muted)", marginTop: 6 }}>
          No item details available.
        </p>
      )}
    </div>
  );
}

// ── TicketCard ────────────────────────────────────────────────────────────────
export function TicketCard({ ticket }: { ticket: Ticket }) {
  return (
    <div className="card" style={{ marginBottom: 12 }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 6,
        }}
      >
        <span style={{ fontWeight: 600, fontSize: 14 }}>{ticket.ticket_id}</span>
        <StatusBadge status={ticket.status} />
      </div>
      <p style={{ fontSize: 13, color: "var(--ink-soft)", marginBottom: 4 }}>
        {ticket.subject}
      </p>
      <p style={{ fontSize: 12, color: "var(--muted)" }}>
        {ticket.category} · {ticket.created_at}
        {ticket.order_id && ` · Order: ${ticket.order_id}`}
      </p>
    </div>
  );
}

// ── RequestCard ───────────────────────────────────────────────────────────────
export function RequestCard({ req }: { req: ServiceRequest }) {
  const typeColors: Record<string, string> = {
    refund:      "#dbeafe",
    return:      "#fef3c7",
    replacement: "#f3e8ff",
    warranty:    "#dcfce7",
  };
  const typeColor = typeColors[req.type] ?? "var(--border-soft)";

  return (
    <div className="card" style={{ marginBottom: 12 }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 8,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ fontWeight: 700, fontSize: 14 }}>{req.request_id}</span>
          <span
            style={{
              fontSize: 11,
              background: typeColor,
              borderRadius: 4,
              padding: "2px 8px",
              fontWeight: 600,
            }}
          >
            {req.type}
          </span>
        </div>
        <StatusBadge status={req.status} />
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: 8,
          marginBottom: 8,
        }}
      >
        <div>
          <p style={{ fontSize: 10, color: "var(--muted)", marginBottom: 2 }}>
            REASON
          </p>
          <p style={{ fontSize: 13 }}>{req.reason}</p>
        </div>
        {req.order_id && (
          <div>
            <p style={{ fontSize: 10, color: "var(--muted)", marginBottom: 2 }}>
              ORDER
            </p>
            <p style={{ fontSize: 13, fontWeight: 500 }}>{req.order_id}</p>
          </div>
        )}
      </div>

      {req.evidence && (
        <div
          style={{
            background: "#fef3c7",
            borderRadius: 6,
            padding: "6px 10px",
            marginBottom: 8,
            fontSize: 12,
            color: "#92400e",
          }}
        >
          📎 Evidence required: {req.evidence}
        </div>
      )}

      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          fontSize: 11,
          color: "var(--muted)",
        }}
      >
        <span>Created: {req.created_at}</span>
        {req.resolved_at && <span>Resolved: {req.resolved_at}</span>}
      </div>
    </div>
  );
}