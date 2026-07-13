"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

export default function RegisterPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [customerId, setCustomerId] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleRegister() {
    setError(""); setLoading(true);
    try {
      await api.register(email, password, customerId);
      router.push("/login");
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: "var(--bg)" }}>
      <div className="card" style={{ width: 380 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 6, color: "var(--accent)" }}>Create account</h1>
        <p style={{ color: "var(--muted)", fontSize: 13, marginBottom: 24 }}>Link to your Olist customer ID</p>
        {error && <p style={{ color: "var(--error)", fontSize: 13, marginBottom: 12 }}>{error}</p>}
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <input placeholder="customer_unique_id (from Olist)" value={customerId} onChange={e => setCustomerId(e.target.value)} />
          <input type="email" placeholder="Email" value={email} onChange={e => setEmail(e.target.value)} />
          <input type="password" placeholder="Password (min 6 chars)" value={password} onChange={e => setPassword(e.target.value)} />
          <button className="btn-primary" onClick={handleRegister} disabled={loading} style={{ marginTop: 4 }}>
            {loading ? "Creating…" : "Create account"}
          </button>
          <p style={{ textAlign: "center", fontSize: 13, color: "var(--ink-soft)" }}>
            Already have one? <a href="/login">Sign in</a>
          </p>
        </div>
      </div>
    </div>
  );
}
