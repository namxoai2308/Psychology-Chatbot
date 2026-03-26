"use client";

import { useMemo, useState, useEffect, useRef } from "react";

type Msg = { role: "user" | "bot"; text: string };
type Conversation = { id: string; title: string; updated_at: string };

export default function Page() {
  const [name, setName] = useState("");
  const [ready, setReady] = useState(false);
  const [input, setInput] = useState("");
  const [threadId, setThreadId] = useState("");
  const [model, setModel] = useState("slm");
  const [msgs, setMsgs] = useState<Msg[]>([
    { role: "bot", text: "Chào bạn. Bạn đang thấy thế nào hôm nay?" },
  ]);
  const [busy, setBusy] = useState(false);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const chatBottomRef = useRef<HTMLDivElement>(null);

  const apiUrl = useMemo(
    () => (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, ""),
    []
  );

  const fetchConversations = () => {
    fetch(`${apiUrl}/conversations?user_id=${name || "default_user"}`)
      .then((r) => r.json())
      .then((d) => setConversations(d.conversations || []))
      .catch((err) => console.error("Lỗi tải ds hội thoại", err));
  };

  useEffect(() => {
    if (ready) {
      fetchConversations();
    }
  }, [ready, name, apiUrl]);

  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [msgs]);

  function newChat() {
    setThreadId("");
    setMsgs([{ role: "bot", text: "Chào bạn. Bạn đang thấy thế nào hôm nay?" }]);
  }

  async function loadChat(id: string) {
    if (busy) return;
    setThreadId(id);
    setMsgs([{ role: "bot", text: "Đang tải tin nhắn..." }]);
    try {
      const res = await fetch(`${apiUrl}/conversations/${id}/history`);
      const data = await res.json();
      if (data.chat_history) {
        const lines = data.chat_history.trim().split("\n");
        const loadedMsgs: Msg[] = [];
        let currentRole: "user" | "bot" | null = null;
        let currentText = "";

        for (const line of lines) {
          if (line.startsWith("User: ")) {
            if (currentRole) loadedMsgs.push({ role: currentRole, text: currentText.trim() });
            currentRole = "user";
            currentText = line.substring(6);
          } else if (line.startsWith("Bot: ")) {
            if (currentRole) loadedMsgs.push({ role: currentRole, text: currentText.trim() });
            currentRole = "bot";
            currentText = line.substring(5);
          } else {
            currentText += "\n" + line;
          }
        }
        if (currentRole) loadedMsgs.push({ role: currentRole, text: currentText.trim() });

        if (loadedMsgs.length > 0) {
          setMsgs(loadedMsgs);
        } else {
          setMsgs([{ role: "bot", text: "Chưa có tin nhắn nào." }]);
        }
      } else {
        setMsgs([{ role: "bot", text: "Chưa có tin nhắn nào." }]);
      }
    } catch {
      setMsgs([{ role: "bot", text: "Lỗi tải lịch sử." }]);
    }
  }

  async function send() {
    const text = input.trim();
    if (!text || busy) return;
    setInput("");
    setMsgs((m) => [...m, { role: "user", text }]);
    setBusy(true);
    try {
      const payload = {
        user_message: text,
        thread_id: threadId,
        user_name: name || "Khách",
        selected_model: model,
      };

      const res = await fetch(`${apiUrl}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = (await res.json()) as { reply?: string; thread_id?: string };
      if (data.thread_id && !threadId) {
        setThreadId(data.thread_id);
      }
      setMsgs((m) => [...m, { role: "bot", text: data.reply || "Mình chưa trả lời được." }]);
      
      // Refresh sidebar
      fetchConversations();
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
            "radial-gradient(800px circle at 20% 15%, rgba(168, 85, 247, 0.35), transparent 55%), radial-gradient(600px circle at 80% 85%, rgba(109, 40, 217, 0.25), transparent 60%), #0B0D14",
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
            <div style={{ fontSize: 26, fontWeight: 650, letterSpacing: -0.3, color: "#fff" }}>
              CBT AI Therapist
            </div>
            <div style={{ marginTop: 6, color: "rgba(238, 240, 255, 0.70)", fontSize: 14 }}>
              Nhập tên để hệ thống lưu trữ lịch sử cá nhân của bạn.
            </div>
          </div>

          <div style={{ display: "grid", gap: 10 }}>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Nhập tên đăng nhập..."
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
              Vào hệ thống
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div style={{ display: "flex", height: "100vh", background: "#0B0D14", color: "#EEF0FF" }}>
      {/* SIDEBAR */}
      <div
        style={{
          width: 300,
          borderRight: "1px solid rgba(255,255,255,0.08)",
          display: "flex",
          flexDirection: "column",
          background: "rgba(15, 17, 26, 0.95)",
        }}
      >
        <div style={{ padding: 20 }}>
          <button
            onClick={newChat}
            style={{
              width: "100%",
              padding: "12px",
              borderRadius: 12,
              background: "linear-gradient(135deg, #A855F7 0%, #6D28D9 100%)",
              color: "#fff",
              cursor: "pointer",
              border: "1px solid rgba(255,255,255,0.1)",
              fontWeight: 600,
              boxShadow: "0 4px 15px rgba(168, 85, 247, 0.2)",
              transition: "opacity 0.2s",
            }}
          >
            + Cuộc trò chuyện mới
          </button>
        </div>
        
        <div style={{ padding: "0 20px 10px", fontSize: 13, color: "rgba(255,255,255,0.4)", fontWeight: 600, letterSpacing: 0.5 }}>
          LỊCH SỬ HỘI THOẠI
        </div>

        <div style={{ flex: 1, overflowY: "auto" }}>
          {conversations.length === 0 ? (
            <div style={{ padding: 20, color: "rgba(255,255,255,0.3)", fontSize: 13, textAlign: "center" }}>
              Chưa có lịch sử.
            </div>
          ) : (
            conversations.map((c) => (
              <div
                key={c.id}
                onClick={() => loadChat(c.id)}
                style={{
                  padding: "14px 20px",
                  cursor: "pointer",
                  background: threadId === c.id ? "rgba(168, 85, 247, 0.15)" : "transparent",
                  borderLeft: threadId === c.id ? "3px solid #A855F7" : "3px solid transparent",
                  transition: "background 0.2s",
                }}
              >
                <div style={{ color: threadId === c.id ? "#fff" : "rgba(255,255,255,0.8)", fontSize: 14, fontWeight: 500, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                  {c.title}
                </div>
                <div style={{ color: "rgba(238, 240, 255, 0.4)", fontSize: 12, marginTop: 4 }}>
                  {new Date(c.updated_at).toLocaleString('vi-VN')}
                </div>
              </div>
            ))
          )}
        </div>
        
        <div style={{ padding: 20, borderTop: "1px solid rgba(255,255,255,0.08)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
           <div style={{ fontSize: 14, fontWeight: 500, color: "rgba(255,255,255,0.7)" }}>👤 {name || "Khách"}</div>
           <button onClick={() => setReady(false)} style={{ background: "transparent", color: "rgba(255,255,255,0.5)", border: "none", cursor: "pointer", fontSize: 12 }}>Đăng xuất</button>
        </div>
      </div>

      {/* TÀI KHOẢN & MAIN CHAT */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", padding: "20px 40px" }}>
        {/* HEADER */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
          <div>
            <div style={{ fontSize: 24, fontWeight: 700, letterSpacing: -0.5, color: "#fff" }}>Phòng Khám Tâm Lý AI</div>
            <div style={{ fontSize: 13, color: "rgba(255,255,255,0.5)", marginTop: 2 }}>Luôn sẵn sàng lắng nghe bạn</div>
          </div>
          <div>
            <select
              value={model}
              onChange={(e) => setModel(e.target.value)}
              style={{
                padding: "10px 16px",
                borderRadius: 8,
                background: "rgba(255,255,255,0.05)",
                border: "1px solid rgba(255,255,255,0.1)",
                color: "#EEF0FF",
                outline: "none",
                fontWeight: 500
              }}
            >
              <option value="gemini" style={{ background: "#0B0D14" }}>🤖 Google Gemini Pro</option>
              <option value="slm" style={{ background: "#0B0D14" }}>⚡ Qwen3 SLM (Kaggle)</option>
            </select>
          </div>
        </div>

        {/* CHAT AREA */}
        <div
          style={{
            flex: 1,
            border: "1px solid rgba(255,255,255,0.10)",
            borderRadius: 16,
            padding: 20,
            overflowY: "auto",
            background: "rgba(15, 17, 26, 0.5)",
            boxShadow: "inset 0 0 20px rgba(0,0,0,0.5)",
            display: "flex",
            flexDirection: "column",
            gap: 16
          }}
        >
          {msgs.map((m, i) => (
            <div
              key={i}
              style={{
                display: "flex",
                justifyContent: m.role === "user" ? "flex-end" : "flex-start",
              }}
            >
              <div
                style={{
                  maxWidth: "75%",
                  padding: "14px 18px",
                  borderRadius: 16,
                  borderBottomRightRadius: m.role === "user" ? 4 : 16,
                  borderBottomLeftRadius: m.role === "bot" ? 4 : 16,
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
                  lineHeight: 1.5,
                  fontSize: 15,
                  boxShadow: m.role === "user" ? "0 4px 15px rgba(168, 85, 247, 0.15)" : "none"
                }}
              >
                {m.role === "bot" && i > 0 && <strong style={{color: "#A855F7", display: "block", marginBottom: 6, fontSize: 12, letterSpacing: 0.5}}>AI THERAPIST</strong>}
                {m.text}
              </div>
            </div>
          ))}
          <div ref={chatBottomRef} />
        </div>

        {/* INPUT BUBBLE */}
        <div style={{ display: "flex", gap: 12, marginTop: 20 }}>
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => (e.key === "Enter" ? send() : null)}
            placeholder="Kể cho tôi nghe về cảm xúc của bạn lúc này..."
            style={{
              padding: "16px 20px",
              flex: 1,
              borderRadius: 16,
              background: "rgba(255,255,255,0.05)",
              border: "1px solid rgba(255,255,255,0.15)",
              outline: "none",
              color: "#EEF0FF",
              fontSize: 15,
              transition: "border 0.2s"
            }}
            disabled={busy}
            autoFocus
          />
          <button
            onClick={send}
            disabled={busy}
            style={{
              padding: "0 28px",
              borderRadius: 16,
              border: "1px solid rgba(255,255,255,0.10)",
              cursor: busy ? "not-allowed" : "pointer",
              color: "#F7F7FF",
              fontWeight: 650,
              fontSize: 15,
              background: busy
                ? "rgba(168, 85, 247, 0.35)"
                : "linear-gradient(135deg, #A855F7 0%, #6D28D9 100%)",
              boxShadow: busy ? "none" : "0 10px 30px rgba(168, 85, 247, 0.22)",
              transition: "opacity 0.2s",
              opacity: busy ? 0.75 : 1,
            }}
          >
            {busy ? "Đang gõ..." : "Gửi"}
          </button>
        </div>
      </div>
    </div>
  );
}
