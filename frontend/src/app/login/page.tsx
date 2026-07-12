"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleLogin() {
    setError(""); setLoading(true);
    try {
      const { access_token } = await api.login(email, password);
      localStorage.setItem("token", access_token);
      router.push("/chat");
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: "var(--bg)" }}>
      <div className="card" style={{ width: 380 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 6, color: "var(--accent)" }}>AI Support</h1>
        <p style={{ color: "var(--muted)", fontSize: 13, marginBottom: 24 }}>Sign in to your account</p>
        {error && <p style={{ color: "var(--error)", fontSize: 13, marginBottom: 12 }}>{error}</p>}
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <input type="email" placeholder="Email" value={email} onChange={e => setEmail(e.target.value)} />
          <input type="password" placeholder="Password" value={password} onChange={e => setPassword(e.target.value)}
            onKeyDown={e => e.key === "Enter" && handleLogin()} />
          <button className="btn-primary" onClick={handleLogin} disabled={loading} style={{ marginTop: 4 }}>
            {loading ? "Signing in…" : "Sign in"}
          </button>
          <p style={{ textAlign: "center", fontSize: 13, color: "var(--ink-soft)" }}>
            No account? <a href="/register">Register</a>
          </p>
        </div>
      </div>
    </div>
  );
}
