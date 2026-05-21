"use client";

import { useMemo, useState, useEffect, useRef } from "react";

type Msg = { role: "user" | "bot"; text: string; sender?: string; isTyping?: boolean };
type Conversation = { id: string; title: string; updated_at: string };

import ChatSidebar from "./components/ChatSidebar";
import Dass21Modal from "./components/Dass21Modal";

export default function Page() {
  const [name, setName] = useState("");
  const [ready, setReady] = useState(false);
  const [input, setInput] = useState("");
  const [threadId, setThreadId] = useState("");
  const [model, setModel] = useState("gemini");
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [busy, setBusy] = useState(false);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const chatBottomRef = useRef<HTMLDivElement>(null);
  const [showDass21, setShowDass21] = useState(false);

  // Queue references
  const abortDelayRef = useRef<() => void>(() => {});
  const shouldFlushRef = useRef<boolean>(false);
  const isSendingRef = useRef<boolean>(false);

  const apiUrl = useMemo(
    () => (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, ""),
    []
  );
  const userId = useMemo(() => name.trim() || "default_user", [name]);
  const greeting = useMemo(
    () =>
      `Chào ${name || "Khách"}, mình là chuyên viên tâm lý AI. Hôm nay bạn cảm thấy thế nào?\nTrước khi bắt đầu trò chuyện sâu hơn, bạn có thể mở bài đánh giá DASS-21 ngắn để hệ thống hiểu rõ hơn chỉ số cảm xúc của bạn trong tuần qua.`,
    [name]
  );

  const fetchConversations = () => {
    fetch(`${apiUrl}/conversations?user_id=${encodeURIComponent(userId)}`)
      .then((r) => r.json())
      .then((d) => setConversations(d.conversations || []))
      .catch((err) => console.error("Lỗi tải ds hội thoại", err));
  };

  useEffect(() => {
    if (ready) {
      fetchConversations();
      if (msgs.length === 0) {
        setMsgs([{ 
          role: "bot", 
          text: greeting
        }]);
      }
    }
  }, [ready, name, apiUrl, userId, greeting]);

  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [msgs]);

  useEffect(() => {
    let timeout: ReturnType<typeof setTimeout>;
    if (ready && msgs.length > 0 && msgs[msgs.length - 1].role === "bot" && msgs[msgs.length - 1].text !== "Chưa có tin nhắn nào." && !busy && !showDass21 && threadId) {
       timeout = setTimeout(() => {
           if (!input.trim()) send("[USER_SILENT]");
       }, 45000); // Ngăn trigger auto ping
    }
    return () => clearTimeout(timeout);
  }, [msgs, busy, ready, showDass21, threadId, input]);

  function newChat() {
    setThreadId("");
    setMsgs([{ 
      role: "bot", 
      text: greeting
    }]);
  }

  async function processQueue(items: any[]) {
    shouldFlushRef.current = false;
    for (let i = 0; i < items.length; i++) {
        const item = items[i];
        
        // Start typing
        setMsgs(prev => {
            const arr = [...prev];
            if (arr[arr.length - 1]?.isTyping) {
                arr[arr.length - 1] = { role: "bot", text: "...", isTyping: true, sender: item.sender };
            } else {
                arr.push({ role: "bot", text: "...", isTyping: true, sender: item.sender });
            }
            return arr;
        });

        if (!shouldFlushRef.current) {
            await new Promise<void>(resolve => {
                let timer = setTimeout(resolve, item.typing_time_ms || 4000);
                abortDelayRef.current = () => {
                    clearTimeout(timer);
                    resolve();
                }
            });
        }
        
        // Finalize message
        setMsgs(prev => {
            const arr = [...prev];
            if (arr[arr.length - 1]?.isTyping) {
                arr[arr.length - 1] = { role: "bot", sender: item.sender, text: item.text };
            } else {
                arr.push({ role: "bot", sender: item.sender, text: item.text });
            }
            return arr;
        });
    }
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

        const flushBotQueue = () => {
             if (currentText.trim()) {
                 const textToParse = currentText.trim();
                 const re = /\[(.*?)\]: (.*)/g;
                 let match;
                 let hasMatches = false;
                 while ((match = re.exec(textToParse)) !== null) {
                     hasMatches = true;
                     const sender = match[1];
                     const nextMatchIdx = textToParse.indexOf("\n[", re.lastIndex);
                     const msgText = nextMatchIdx !== -1 
                            ? textToParse.substring(re.lastIndex, nextMatchIdx).trim() 
                            : textToParse.substring(re.lastIndex).trim();
                     loadedMsgs.push({ role: "bot", sender, text: textToParse.substring(match.index + match[0].length, nextMatchIdx !== -1 ? nextMatchIdx : textToParse.length).trim() });
                     re.lastIndex = nextMatchIdx !== -1 ? nextMatchIdx : textToParse.length;
                 }
                 if (!hasMatches) loadedMsgs.push({ role: "bot", text: textToParse });
             }
        }

        for (const line of lines) {
          if (line.startsWith("User: ")) {
            if (currentRole === "bot") flushBotQueue();
            else if (currentRole === "user") loadedMsgs.push({ role: "user", text: currentText.trim() });
            currentRole = "user";
            currentText = line.substring(6);
          } else if (line.startsWith("Bot: ")) {
            if (currentRole === "bot") flushBotQueue();
            else if (currentRole === "user") loadedMsgs.push({ role: "user", text: currentText.trim() });
            currentRole = "bot";
            currentText = line.substring(5);
          } else {
            currentText += "\n" + line;
          }
        }
        if (currentRole === "bot") flushBotQueue();
        else if (currentRole === "user") loadedMsgs.push({ role: "user", text: currentText.trim() });

        if (loadedMsgs.length > 0) setMsgs(loadedMsgs);
        else setMsgs([{ role: "bot", text: "Chưa có tin nhắn nào." }]);
      } else {
        setMsgs([{ role: "bot", text: "Chưa có tin nhắn nào." }]);
      }
    } catch {
      setMsgs([{ role: "bot", text: "Lỗi tải lịch sử." }]);
    }
  }

  async function send(silentText?: string | React.MouseEvent | React.KeyboardEvent) {
    if (isSendingRef.current) return;
    
    if (!shouldFlushRef.current) {
       shouldFlushRef.current = true;
       abortDelayRef.current(); 
    }

    const text = typeof silentText === "string" ? silentText : input.trim();
    if (!text || busy) return;
    
    isSendingRef.current = true;
    if (typeof silentText !== "string") setInput("");
    
    if (text !== "[USER_SILENT]") {
        setMsgs((m) => [...m, { role: "user", text }]);
    }
    setBusy(true);
    let finalOutputQueue: any[] = [];
    
    try {
      const payload = {
        user_message: text,
        thread_id: threadId,
        user_name: name || "Khách",
        user_id: userId,
        selected_model: model,
        system_variant: "ours_full",
      };

      const res = await fetch(`${apiUrl}/chat/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.body) throw new Error("No response body");
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      // Cleanup old typical messages first if any
      setMsgs((prev) => {
          const arr = [...prev];
          if (arr[arr.length - 1]?.isTyping) arr.pop();
          return arr;
      });
      console.log("Hệ thống đang phân tích...");

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n\n");
        buffer = lines.pop() || "";
        
        for (const line of lines) {
          if (line.startsWith("data: ")) {
             const dataStr = line.substring(6);
             const p = JSON.parse(dataStr);
             
	             if ((p.node === "Orchestrator" || p.node === "Therapist_Orchestrator") && p.next_speaker) {
                 let senderName = "Nhà trị liệu";
                 if (p.next_speaker === "peer_mirror_agent") senderName = "Nam";
                 else if (p.next_speaker === "veteran_peer_agent") senderName = "Chị Linh";
                 
                 if (p.next_speaker !== "FINISH" && p.next_speaker !== "Guardrails") {
                     setMsgs((prev) => {
                         const arr = [...prev];
                         if (arr[arr.length - 1]?.isTyping) arr.pop();
                         arr.push({ role: "bot", text: "đang nhập...", isTyping: true, sender: senderName });
                         return arr;
                     });
                 }
             }

	             if (p.ui_action === "SHOW_DASS21") setShowDass21(true);
	             if (p.thread_id && !threadId) setThreadId(p.thread_id);
	             if (p.final_output) finalOutputQueue = p.final_output;
	             else if (p.final_reply) {
	               finalOutputQueue = [{ sender: "Nhà trị liệu", text: p.final_reply, typing_time_ms: 800 }];
	             }
	          }
        }
      }
      
    } catch {
      setMsgs((m) => {
         const filtered = m.filter(msg => !msg.isTyping);
         return [...filtered, { role: "bot", text: "Lỗi kết nối backend." }];
      });
    } finally {
      // Clear trailing 'isTyping' bubble from system
      setMsgs((prev) => {
          const arr = [...prev];
          if (arr[arr.length - 1]?.isTyping) arr.pop();
          return arr;
      });
      setBusy(false);
      isSendingRef.current = false;
      fetchConversations();
      
      // FIRE THE ANIMATED QUEUE
      if (finalOutputQueue.length > 0) {
          processQueue(finalOutputQueue);
      }
    }
  }

  async function submitDass21(answers: number[]) {
    if (isSendingRef.current) return;
    isSendingRef.current = true;
    setShowDass21(false);
    
    if (!shouldFlushRef.current) {
       shouldFlushRef.current = true;
       abortDelayRef.current(); 
    }

    setMsgs((m) => [...m, { role: "user", text: "[Đã nộp bài kiểm tra DASS-21]" }]);
    setBusy(true);
    let finalOutputQueue: any[] = [];
    
    try {
      const payload = {
        user_message: JSON.stringify({ DASS21: answers }),
        thread_id: threadId,
        user_name: name || "Khách",
        user_id: userId,
        selected_model: model,
        system_variant: "ours_full",
      };

      const res = await fetch(`${apiUrl}/chat/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      
      if (!res.body) throw new Error("No response body");
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      setMsgs((prev) => {
          const arr = [...prev];
          if (arr[arr.length - 1]?.isTyping) arr.pop();
          return arr;
      });
      console.log("Đang phân bổ phòng trị liệu...");

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        
        const lines = buffer.split("\n\n");
        buffer = lines.pop() || "";
        
        for (const line of lines) {
          if (line.startsWith("data: ")) {
             const dataStr = line.substring(6);
             const p = JSON.parse(dataStr);
             
	             if ((p.node === "Orchestrator" || p.node === "Therapist_Orchestrator") && p.next_speaker) {
                 let senderName = "Nhà trị liệu";
                 if (p.next_speaker === "peer_mirror_agent") senderName = "Nam";
                 else if (p.next_speaker === "veteran_peer_agent") senderName = "Chị Linh";
                 
                 if (p.next_speaker !== "FINISH" && p.next_speaker !== "Guardrails") {
                     setMsgs((prev) => {
                         const arr = [...prev];
                         if (arr[arr.length - 1]?.isTyping) arr.pop();
                         arr.push({ role: "bot", text: "đang nhập...", isTyping: true, sender: senderName });
                         return arr;
                     });
                 }
             }

	             if (p.ui_action === "SHOW_DASS21") setShowDass21(true);
	             if (p.thread_id && !threadId) setThreadId(p.thread_id);
	             if (p.final_output) finalOutputQueue = p.final_output;
	             else if (p.final_reply) {
	               finalOutputQueue = [{ sender: "Nhà trị liệu", text: p.final_reply, typing_time_ms: 800 }];
	             }
	          }
        }
      }
    } catch {
      setMsgs((m) => {
         const filtered = m.filter(msg => !msg.isTyping);
         return [...filtered, { role: "bot", text: "Lỗi kết nối backend." }];
      });
    } finally {
      setMsgs((prev) => {
          const arr = [...prev];
          if (arr[arr.length - 1]?.isTyping) arr.pop();
          return arr;
      });
      setBusy(false);
      isSendingRef.current = false;
      fetchConversations();
      
      if (finalOutputQueue.length > 0) {
          processQueue(finalOutputQueue);
      }
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
              AI Therapist
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
      <ChatSidebar
        conversations={conversations}
        threadId={threadId}
        onNewChat={newChat}
        onLoadChat={loadChat}
        userName={name || "Khách"}
        onLogout={() => setReady(false)}
      />

      {/* TÀI KHOẢN & MAIN CHAT */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", padding: "20px 40px" }}>
        {/* HEADER */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
          <div>
            <div style={{ fontSize: 24, fontWeight: 700, letterSpacing: -0.5, color: "#fff" }}>Không Gian Lắng Nghe AI</div>
            <div style={{ fontSize: 13, color: "rgba(255,255,255,0.5)", marginTop: 2 }}>Luôn sẵn sàng đồng hành cùng bạn</div>
          </div>
          <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
            <button
              onClick={() => setShowDass21(true)}
              disabled={busy}
              style={{
                padding: "10px 14px",
                borderRadius: 8,
                background: "rgba(168, 85, 247, 0.14)",
                border: "1px solid rgba(168, 85, 247, 0.35)",
                color: "#EEF0FF",
                cursor: busy ? "not-allowed" : "pointer",
                fontWeight: 600,
              }}
            >
              DASS-21
            </button>
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
              <option value="groq" style={{ background: "#0B0D14" }}>🚀 Groq (LLaMA 3.3)</option>
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
                {m.role === "bot" && <strong style={{color: "#A855F7", display: "block", marginBottom: 6, fontSize: 13, letterSpacing: 0.5}}>{m.sender ? m.sender.toUpperCase() : "AI THERAPIST"}</strong>}
                {m.text}
                {m.isTyping && <span style={{ marginLeft: 6, animation: "blink 1s infinite" }}>|</span>}
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
            {busy ? "Đang gửi..." : "Gửi"}
          </button>
        </div>
      </div>

      {/* DASS-21 MODAL */}
      <Dass21Modal 
         show={showDass21} 
         onHide={() => setShowDass21(false)} 
         onSubmit={submitDass21} 
         busy={busy} 
      />
    </div>
  );
}
