"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import { OrderCard, TicketCard, RequestCard } from "@/components/TicketCard";
import { Identity, Order, Ticket, ServiceRequest } from "@/lib/types";

type Tab = "overview" | "orders" | "tickets" | "requests";

export default function AccountPage() {
  const router = useRouter();
  const [tab, setTab]           = useState<Tab>("overview");
  const [identity, setIdentity] = useState<Identity | null>(null);
  const [orders, setOrders]     = useState<Order[]>([]);
  const [tickets, setTickets]   = useState<Ticket[]>([]);
  const [requests, setRequests] = useState<ServiceRequest[]>([]);
  const [loading, setLoading]   = useState(true);

  useEffect(() => {
    if (!localStorage.getItem("token")) {
      router.push("/login");
      return;
    }

    Promise.allSettled([
      api.me(),
      api.orders(),
      api.tickets(),
      api.requests(),
    ]).then(([meRes, ordsRes, tcksRes, reqsRes]) => {
      if (meRes.status === "fulfilled") {
        setIdentity(meRes.value as Identity);
      } else {
        router.push("/login");
        return;
      }
      if (ordsRes.status === "fulfilled")
        setOrders(ordsRes.value as Order[]);
      if (tcksRes.status === "fulfilled")
        setTickets(tcksRes.value as Ticket[]);
      if (reqsRes.status === "fulfilled")
        setRequests(reqsRes.value as ServiceRequest[]);
    }).finally(() => setLoading(false));
  }, [router]);

  function logout() {
    localStorage.removeItem("token");
    router.push("/login");
  }

  const openTickets   = tickets.filter((t) => t.status === "open").length;
  const openRequests  = requests.filter((r) =>
    ["open", "pending_proof"].includes(r.status)
  ).length;
  const deliveredOrds = orders.filter((o) => o.status === "delivered").length;

  const tabs: { key: Tab; label: string; count?: number }[] = [
    { key: "overview",  label: "Overview" },
    { key: "orders",    label: "Orders",   count: orders.length },
    { key: "tickets",   label: "Tickets",  count: tickets.length },
    { key: "requests",  label: "Requests", count: requests.length },
  ];

  return (
    <div style={{ minHeight: "100vh", background: "var(--bg)" }}>
      {/* header */}
      <header style={{ padding: "12px 24px", background: "var(--panel)",
        borderBottom: "1px solid var(--border)", display: "flex",
        alignItems: "center", justifyContent: "space-between" }}>
        <span style={{ fontWeight: 700, color: "var(--accent)", fontSize: 17 }}>
          My Account
        </span>
        <div style={{ display: "flex", gap: 16, alignItems: "center" }}>
          <Link href="/chat" style={{ fontSize: 13, color: "var(--ink-soft)" }}>
            💬 Chat
          </Link>
          <button className="btn-outline" onClick={logout}
            style={{ fontSize: 12, padding: "5px 14px" }}>
            Sign out
          </button>
        </div>
      </header>

      <div style={{ maxWidth: 820, margin: "0 auto", padding: "28px 20px" }}>
        {loading && (
          <p style={{ color: "var(--muted)", fontSize: 14 }}>
            Loading your account…
          </p>
        )}

        {!loading && (
          <>
            {/* customer profile card */}
            {identity && (
              <div className="card" style={{ marginBottom: 20,
                background: "linear-gradient(135deg, #eff6ff, #f8fafc)" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
                  <div style={{ width: 56, height: 56, borderRadius: "50%",
                    background: "linear-gradient(135deg, #2563eb, #7c3aed)",
                    display: "flex", alignItems: "center", justifyContent: "center",
                    color: "#fff", fontWeight: 700, fontSize: 22, flexShrink: 0 }}>
                    {identity.email?.[0]?.toUpperCase() ?? "?"}
                  </div>
                  <div style={{ flex: 1 }}>
                    <p style={{ fontWeight: 700, fontSize: 17, marginBottom: 4 }}>
                      {identity.email}
                    </p>
                    <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
                      <span style={{ fontSize: 12, color: "var(--ink-soft)" }}>
                        🆔 {identity.customer_id}
                      </span>
                      <span style={{ fontSize: 12, color: "var(--ink-soft)" }}>
                        🔑 Role: {identity.role}
                      </span>
                    </div>
                  </div>
                  <div style={{ display: "flex", gap: 20, flexShrink: 0 }}>
                    {[
                      { label: "Orders",    value: orders.length,  color: "#2563eb" },
                      { label: "Delivered", value: deliveredOrds,  color: "#16a34a" },
                      { label: "Tickets",   value: openTickets,    color: "#d97706" },
                    ].map((s) => (
                      <div key={s.label} style={{ textAlign: "center" }}>
                        <p style={{ fontSize: 24, fontWeight: 700, color: s.color, lineHeight: 1 }}>
                          {s.value}
                        </p>
                        <p style={{ fontSize: 10, color: "var(--muted)", marginTop: 3 }}>
                          {s.label}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* tab nav */}
            <div style={{ display: "flex", gap: 4, marginBottom: 20,
              borderBottom: "1px solid var(--border)" }}>
              {tabs.map((t) => (
                <button key={t.key} onClick={() => setTab(t.key)}
                  style={{ padding: "8px 18px", borderRadius: "8px 8px 0 0",
                    border: "1px solid",
                    borderColor: tab === t.key ? "var(--border)" : "transparent",
                    borderBottom: tab === t.key
                      ? "1px solid var(--panel)"
                      : "1px solid var(--border)",
                    background: tab === t.key ? "var(--panel)" : "transparent",
                    color: tab === t.key ? "var(--accent)" : "var(--ink-soft)",
                    fontWeight: tab === t.key ? 600 : 400,
                    fontSize: 13, marginBottom: -1, cursor: "pointer" }}>
                  {t.label}
                  {t.count !== undefined && (
                    <span style={{ marginLeft: 6, borderRadius: 10, fontSize: 10,
                      padding: "1px 6px",
                      background: tab === t.key ? "var(--accent)" : "var(--border)",
                      color: tab === t.key ? "#fff" : "var(--ink-soft)" }}>
                      {t.count}
                    </span>
                  )}
                </button>
              ))}
            </div>

            {/* OVERVIEW */}
            {tab === "overview" && (
              <div>
                {openRequests > 0 && (
                  <div style={{ background: "#fef3c7", border: "1px solid #fbbf24",
                    borderRadius: 10, padding: "12px 16px", marginBottom: 16,
                    fontSize: 13, color: "#92400e" }}>
                    📋 You have <strong>{openRequests}</strong> active service request(s) pending action.
                    <button onClick={() => setTab("requests")}
                      style={{ marginLeft: 10, color: "#2563eb", background: "none",
                        border: "none", cursor: "pointer", fontSize: 13, padding: 0 }}>
                      View →
                    </button>
                  </div>
                )}
                <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 10, color: "var(--ink)" }}>
                  Recent Orders
                </h3>
                {orders.length === 0 && (
                  <p style={{ color: "var(--muted)", fontSize: 13 }}>No orders yet.</p>
                )}
                {orders.slice(0, 3).map((o, i) => <OrderCard key={i} order={o} />)}
                {orders.length > 3 && (
                  <button onClick={() => setTab("orders")}
                    style={{ fontSize: 13, color: "var(--accent)", background: "none",
                      border: "none", cursor: "pointer", padding: "4px 0" }}>
                    View all {orders.length} orders →
                  </button>
                )}
                {requests.length > 0 && (
                  <>
                    <h3 style={{ fontSize: 14, fontWeight: 600,
                      margin: "20px 0 10px", color: "var(--ink)" }}>
                      Recent Service Requests
                    </h3>
                    {requests.slice(0, 2).map((r, i) => <RequestCard key={i} req={r} />)}
                    {requests.length > 2 && (
                      <button onClick={() => setTab("requests")}
                        style={{ fontSize: 13, color: "var(--accent)", background: "none",
                          border: "none", cursor: "pointer", padding: "4px 0" }}>
                        View all {requests.length} requests →
                      </button>
                    )}
                  </>
                )}
              </div>
            )}

            {/* ORDERS */}
            {tab === "orders" && (
              <div>
                {orders.length === 0 && (
                  <p style={{ color: "var(--muted)", fontSize: 14 }}>No orders found.</p>
                )}
                {orders.map((o, i) => <OrderCard key={i} order={o} />)}
              </div>
            )}

            {/* TICKETS */}
            {tab === "tickets" && (
              <div>
                {tickets.length === 0 && (
                  <p style={{ color: "var(--muted)", fontSize: 14 }}>No tickets found.</p>
                )}
                {tickets.map((t, i) => <TicketCard key={i} ticket={t} />)}
              </div>
            )}

            {/* REQUESTS */}
            {tab === "requests" && (
              <div>
                {requests.length === 0 && (
                  <p style={{ color: "var(--muted)", fontSize: 14 }}>No service requests found.</p>
                )}
                {requests.map((r, i) => <RequestCard key={i} req={r} />)}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}