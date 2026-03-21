"use client";

import { useMemo, useState } from "react";

type Msg = { role: "user" | "bot"; text: string };

export default function Page() {
  const [name, setName] = useState("");
  const [ready, setReady] = useState(false);
  const [input, setInput] = useState("");
  const [threadId, setThreadId] = useState("");
  const [msgs, setMsgs] = useState<Msg[]>([
    { role: "bot", text: "Chào bạn. Bạn đang thấy thế nào hôm nay?" },
  ]);
  const [busy, setBusy] = useState(false);

  const apiUrl = useMemo(
    () => (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, ""),
    []
  );


  async function send() {
    const text = input.trim();
    if (!text || busy) return;
    setInput("");
    setMsgs((m) => [...m, { role: "user", text }]);
    setBusy(true);
    try {
      const res = await fetch(`${apiUrl}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_message: text, thread_id: threadId, user_name: name }),
      });
      const data = (await res.json()) as { reply?: string, thread_id?: string };
      if (data.thread_id && !threadId) {
        setThreadId(data.thread_id);
      }
      setMsgs((m) => [...m, { role: "bot", text: data.reply || "Mình chưa trả lời được." }]);
    } catch {
      setMsgs((m) => [...m, { role: "bot", text: "Lỗi kết nối backend." }]);
    } finally {
      setBusy(false);
    }
  }

  if (!ready) {
    return (
      <div
        style={{
          minHeight: "100dvh",
          display: "grid",
          placeItems: "center",
          padding: 16,
          background:
            "radial-gradient(800px circle at 20% 15%, rgba(168, 85, 247, 0.35), transparent 55%), radial-gradient(600px circle at 80% 85%, rgba(109, 40, 217, 0.25), transparent 60%)",
        }}
      >
        <div
          style={{
            width: "min(480px, 100%)",
            borderRadius: 18,
            background: "rgba(15, 17, 26, 0.92)",
            border: "1px solid rgba(168, 85, 247, 0.35)",
            boxShadow:
              "0 28px 90px rgba(0,0,0,0.65), 0 0 0 1px rgba(255,255,255,0.04) inset, 0 0 60px rgba(168, 85, 247, 0.18)",
            padding: 22,
            backdropFilter: "blur(8px)",
          }}
        >
          <div style={{ marginBottom: 14 }}>
            <div style={{ fontSize: 26, fontWeight: 650, letterSpacing: -0.3 }}>
              Đăng nhập
            </div>
            <div style={{ marginTop: 6, color: "rgba(238, 240, 255, 0.70)", fontSize: 14 }}>
              Giao diện mẫu. Nhập tên để bắt đầu trò chuyện.
            </div>
          </div>

          <div style={{ display: "grid", gap: 10 }}>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Tên (tuỳ chọn)"
              style={{
                padding: "12px 12px",
                borderRadius: 12,
                background: "rgba(11, 13, 20, 0.9)",
                border: "1px solid rgba(255,255,255,0.10)",
                outline: "none",
                color: "#EEF0FF",
              }}
            />
            <button
              onClick={() => setReady(true)}
              style={{
                padding: "12px 14px",
                borderRadius: 12,
                border: "1px solid rgba(255,255,255,0.10)",
                cursor: "pointer",
                color: "#F7F7FF",
                fontWeight: 650,
                background: "linear-gradient(135deg, #A855F7 0%, #6D28D9 100%)",
                boxShadow: "0 10px 30px rgba(168, 85, 247, 0.25)",
              }}
            >
              Vào chat
            </button>
          </div>

          <div
            style={{
              marginTop: 14,
              fontSize: 12,
              color: "rgba(238, 240, 255, 0.55)",
              display: "flex",
              justifyContent: "space-between",
              gap: 10,
              flexWrap: "wrap",
            }}
          >
            <span>API: {apiUrl}</span>
            <span style={{ opacity: 0.8 }}>CBT Chatbot</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 980, margin: "0 auto", padding: 16 }}>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 10,
          margin: "10px 0 12px",
        }}
      >
        <div style={{ display: "flex", gap: 10, alignItems: "baseline", flexWrap: "wrap" }}>
          <div style={{ fontSize: 18, fontWeight: 650 }}>CBT Chatbot</div>
          <div style={{ color: "rgba(238, 240, 255, 0.60)", fontSize: 13 }}>
            {name ? `Xin chào, ${name}` : "Chế độ demo"}
          </div>
        </div>
        <button
          onClick={() => setReady(false)}
          style={{
            padding: "10px 12px",
            borderRadius: 12,
            background: "rgba(11, 13, 20, 0.65)",
            border: "1px solid rgba(255,255,255,0.10)",
            color: "rgba(238, 240, 255, 0.85)",
            cursor: "pointer",
          }}
        >
          Đổi tên
        </button>
      </div>

      <div
        style={{
          border: "1px solid rgba(255,255,255,0.10)",
          borderRadius: 16,
          padding: 12,
          height: "62vh",
          overflow: "auto",
          background: "rgba(15, 17, 26, 0.78)",
          boxShadow: "0 18px 55px rgba(0,0,0,0.45)",
        }}
      >
        {msgs.map((m, i) => (
          <div
            key={i}
            style={{
              display: "flex",
              justifyContent: m.role === "user" ? "flex-end" : "flex-start",
              margin: "10px 0",
            }}
          >
            <div
              style={{
                maxWidth: "80%",
                padding: "10px 12px",
                borderRadius: 12,
                background:
                  m.role === "user"
                    ? "linear-gradient(135deg, rgba(168, 85, 247, 0.95), rgba(109, 40, 217, 0.95))"
                    : "rgba(255,255,255,0.06)",
                border:
                  m.role === "user"
                    ? "1px solid rgba(255,255,255,0.10)"
                    : "1px solid rgba(255,255,255,0.08)",
                color: "#EEF0FF",
                whiteSpace: "pre-wrap",
              }}
            >
              {m.text}
            </div>
          </div>
        ))}
      </div>

      <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => (e.key === "Enter" ? send() : null)}
          placeholder="Nhập tin nhắn…"
          style={{
            padding: 12,
            flex: 1,
            borderRadius: 12,
            background: "rgba(11, 13, 20, 0.65)",
            border: "1px solid rgba(255,255,255,0.10)",
            outline: "none",
            color: "#EEF0FF",
          }}
          disabled={busy}
        />
        <button
          onClick={send}
          disabled={busy}
          style={{
            padding: "12px 16px",
            borderRadius: 12,
            border: "1px solid rgba(255,255,255,0.10)",
            cursor: busy ? "not-allowed" : "pointer",
            color: "#F7F7FF",
            fontWeight: 650,
            background: busy
              ? "rgba(168, 85, 247, 0.35)"
              : "linear-gradient(135deg, #A855F7 0%, #6D28D9 100%)",
            boxShadow: busy ? "none" : "0 10px 30px rgba(168, 85, 247, 0.22)",
            opacity: busy ? 0.75 : 1,
          }}
        >
          {busy ? "..." : "Gửi"}
        </button>
      </div>
    </div>
  );
}

