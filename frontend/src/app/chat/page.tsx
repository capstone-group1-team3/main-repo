"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import ChatBox from "@/components/ChatBox";

export default function ChatPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) { router.push("/login"); return; }
    api.me().then(u => setEmail(u.email)).catch(() => router.push("/login"));
  }, [router]);

  function logout() { localStorage.removeItem("token"); router.push("/login"); }

  return (
    <div style={{ height: "100vh", display: "flex", flexDirection: "column" }}>
      {/* header */}
      <header style={{ padding: "12px 24px", background: "var(--panel)", borderBottom: "1px solid var(--border)",
        display: "flex", alignItems: "center", justifyContent: "space-between", flexShrink: 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <span style={{ fontWeight: 700, color: "var(--accent)", fontSize: 17 }}>AI Support</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <Link href="/account" style={{ fontSize: 13, color: "var(--ink-soft)" }}>My Account</Link>
          <span style={{ fontSize: 13, color: "var(--muted)" }}>{email}</span>
          <button className="btn-outline" onClick={logout} style={{ fontSize: 12, padding: "5px 14px" }}>Sign out</button>
        </div>
      </header>
      {/* chat fills remaining height */}
      <div style={{ flex: 1, overflow: "hidden" }}>
        <ChatBox />
      </div>
    </div>
  );
}
