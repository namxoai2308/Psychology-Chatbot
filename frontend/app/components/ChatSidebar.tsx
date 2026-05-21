export default function ChatSidebar({
  conversations,
  threadId,
  onNewChat,
  onLoadChat,
  userName,
  onLogout,
}: {
  conversations: { id: string; title: string; updated_at: string }[];
  threadId: string;
  onNewChat: () => void;
  onLoadChat: (id: string) => void;
  userName: string;
  onLogout: () => void;
}) {
  return (
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
          onClick={onNewChat}
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
              onClick={() => onLoadChat(c.id)}
              style={{
                margin: "0 12px 6px",
                padding: "12px 14px",
                borderRadius: 10,
                cursor: "pointer",
                background: threadId === c.id ? "rgba(168, 85, 247, 0.15)" : "transparent",
                border: threadId === c.id ? "1px solid rgba(168, 85, 247, 0.4)" : "1px solid transparent",
                color: threadId === c.id ? "#fff" : "rgba(255,255,255,0.6)",
                transition: "all 0.2s",
                fontSize: 14,
              }}
            >
              <div style={{ fontWeight: 500, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                {c.title || "Cuộc trò chuyện mới"}
              </div>
              <div style={{ fontSize: 11, color: "rgba(255,255,255,0.3)", marginTop: 4 }}>
                {new Date(c.updated_at).toLocaleString("vi-VN", {
                  hour: "2-digit",
                  minute: "2-digit",
                  day: "2-digit",
                  month: "2-digit",
                })}
              </div>
            </div>
          ))
        )}
      </div>
      <div style={{ padding: 20, borderTop: "1px solid rgba(255,255,255,0.08)", display: "flex", justifyContent: "space-between", alignItems: "center", gap: 10 }}>
        <div style={{ fontSize: 14, fontWeight: 500, color: "rgba(255,255,255,0.7)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
          {userName}
        </div>
        <button onClick={onLogout} style={{ background: "transparent", color: "rgba(255,255,255,0.5)", border: "none", cursor: "pointer", fontSize: 12 }}>
          Đăng xuất
        </button>
      </div>
    </div>
  );
}
