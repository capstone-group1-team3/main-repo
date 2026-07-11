"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

export default function DashboardPage() {
  const router = useRouter();
  const [tickets, setTickets] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");

  useEffect(() => {
    if (!localStorage.getItem("token")) { router.push("/login"); return; }
    api.allTickets()
      .then(setTickets)
      .catch(() => router.push("/chat"))
      .finally(() => setLoading(false));
  }, [router]);

  const statuses = ["all", "open", "pending_proof", "approved", "resolved", "rejected"];
  const filtered = filter === "all" ? tickets : tickets.filter(t => t.status === filter);

  return (
    <div style={{ minHeight: "100vh", background: "var(--bg)" }}>
      <header style={{ padding: "12px 24px", background: "var(--panel)", borderBottom: "1px solid var(--border)",
        display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <span style={{ fontWeight: 700, color: "var(--accent)", fontSize: 17 }}>Staff Dashboard</span>
        <div style={{ display: "flex", gap: 16 }}>
          <a href="/chat" style={{ fontSize: 13, color: "var(--ink-soft)" }}>Chat</a>
          <button className="btn-outline" onClick={() => { localStorage.removeItem("token"); router.push("/login"); }}
            style={{ fontSize: 12, padding: "5px 14px" }}>Sign out</button>
        </div>
      </header>

      <div style={{ maxWidth: 900, margin: "0 auto", padding: "28px 20px" }}>
        <div style={{ display: "flex", gap: 8, marginBottom: 20, flexWrap: "wrap" }}>
          {statuses.map(s => (
            <button key={s} onClick={() => setFilter(s)}
              style={{ padding: "6px 16px", borderRadius: 20, border: "1px solid",
                borderColor: filter === s ? "var(--accent)" : "var(--border)",
                background: filter === s ? "var(--accent)" : "transparent",
                color: filter === s ? "#fff" : "var(--ink-soft)", fontSize: 13 }}>
              {s}
            </button>
          ))}
          <span style={{ marginLeft: "auto", fontSize: 13, color: "var(--muted)", alignSelf: "center" }}>
            {filtered.length} ticket{filtered.length !== 1 ? "s" : ""}
          </span>
        </div>

        {loading && <p style={{ color: "var(--muted)" }}>Loading…</p>}
        {!loading && filtered.length === 0 && <p style={{ color: "var(--muted)" }}>No tickets match this filter.</p>}
        {!loading && filtered.map((t, i) => (
          <div key={i} className="card" style={{ marginBottom: 10 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <span style={{ fontWeight: 600, fontSize: 14 }}>{t.ticket_id}</span>
                <span style={{ marginLeft: 12, fontSize: 12, color: "var(--muted)" }}>{t.customer_unique_id?.slice(0, 12)}…</span>
              </div>
              <span className={`badge badge-${t.status}`}>{t.status}</span>
            </div>
            <p style={{ fontSize: 13, color: "var(--ink-soft)", marginTop: 6 }}>{t.subject || t.category}</p>
            <p style={{ fontSize: 12, color: "var(--muted)", marginTop: 4 }}>
              {t.category} · {t.created_at}
              {t.order_id && ` · ${t.order_id}`}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
