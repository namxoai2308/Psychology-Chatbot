import { useState } from "react";

const DASS21_QUESTIONS = [
  "Tôi thấy khó mà thoải mái được",
  "Tôi bị khô miệng",
  "Tôi không thấy có chút cảm xúc tích cực nào",
  "Tôi bị rối loạn nhịp thở (thở gấp, khó thở dù chẳng làm việc gì nặng)",
  "Tôi thấy khó bắt tay vào công việc",
  "Tôi đã phản ứng thái quá khi có những sự việc xảy ra",
  "Tôi cảm thấy run rẩy (ví dụ: run tay)",
  "Tôi thấy khó thư giãn được",
  "Tôi thấy mình đang ở tình trạng căng thẳng",
  "Tôi cảm thấy không có gì để mong đợi",
  "Tôi thấy dễ cáu gắt với mọi thứ",
  "Tôi thấy khó chịu khi có ai đó làm gián đoạn công việc của tôi",
  "Tôi cảm thấy buồn bã và chán nản",
  "Tôi thấy không thể chịu đựng được bất cứ việc gì nữa",
  "Tôi thấy mình gần như hoảng loạn",
  "Tôi không thể cảm thấy nhiệt tình với bất cứ việc gì",
  "Tôi thấy mình không đáng giá",
  "Tôi thấy mình khá nhạy cảm với mọi việc",
  "Tôi thấy tim đập nhanh mà không có lý do rõ ràng",
  "Tôi thấy mình vô dụng",
  "Tôi thấy mình dễ bị kích động"
];

export default function Dass21Modal({
  show,
  onHide,
  onSubmit,
  busy,
}: {
  show: boolean;
  onHide: () => void;
  onSubmit: (answers: number[]) => void;
  busy: boolean;
}) {
  const [dass21Answers, setDass21Answers] = useState<number[]>(Array(21).fill(-1));

  if (!show) return null;

  async function submit() {
    if (dass21Answers.includes(-1) || busy) {
      alert("Vui lòng trả lời đầy đủ 21 câu hỏi trước khi nộp nhé.");
      return;
    }
    onSubmit(dass21Answers);
    setDass21Answers(Array(21).fill(-1));
  }

  return (
    <div style={{ position: "fixed", top: 0, left: 0, width: "100%", height: "100%", background: "rgba(0,0,0,0.8)", backdropFilter: "blur(5px)", display: "grid", placeItems: "center", zIndex: 999 }}>
      <div style={{ width: "min(600px, 90%)", maxHeight: "85vh", background: "rgba(15, 17, 26, 0.95)", border: "1px solid rgba(168, 85, 247, 0.4)", borderRadius: 16, display: "flex", flexDirection: "column", overflow: "hidden", boxShadow: "0 20px 60px rgba(0,0,0,0.8), 0 0 0 1px rgba(255,255,255,0.05) inset, 0 0 40px rgba(168, 85, 247, 0.2)"}}>
         <div style={{ padding: 20, borderBottom: "1px solid rgba(255,255,255,0.1)", background: "rgba(168, 85, 247, 0.08)" }}>
           <h2 style={{ margin: 0, fontSize: 18, color: "#fff" }}>Bài Kiểm Tra Cảm Xúc DASS-21</h2>
           <div style={{ margin: "8px 0 0", fontSize: 13, color: "rgba(255,255,255,0.7)", lineHeight: 1.5, background: "rgba(255,255,255,0.05)", padding: 12, borderRadius: 8, border: "1px solid rgba(255,255,255,0.05)" }}>
              <strong style={{ color: "#EEF0FF" }}>LUẬT ĐÁNH GIÁ:</strong> Hãy đọc mỗi câu và chọn 1 mức độ tương ứng với việc tình trạng đó áp dụng với bạn <strong style={{ color: "#A855F7" }}>TRONG MỘT TUẦN VỪA QUA</strong> tới mức nào.
              <br/><span style={{ color: "rgba(255,255,255,0.5)", fontSize: 12, marginTop: 4, display: "block" }}>* Không có câu trả lời đúng hay sai. Vui lòng đừng dành quá nhiều thời gian suy nghĩ cho mỗi câu.</span>
           </div>
         </div>
         <div style={{ flex: 1, overflowY: "auto", padding: 20, display: "grid", gap: 16 }}>
            {DASS21_QUESTIONS.map((q, i) => (
               <div key={i} style={{ borderBottom: "1px solid rgba(255,255,255,0.05)", paddingBottom: 16 }}>
                  <div style={{ marginBottom: 10, fontSize: 15, color: "#EEF0FF" }}>{i+1}. {q}</div>
                  <div style={{ display: "flex", gap: 8, flexWrap: "wrap", userSelect: "none" }}>
                     {[0,1,2,3].map(score => (
                        <label key={score} onClick={() => { const newA = [...dass21Answers]; newA[i] = score; setDass21Answers(newA); }} style={{ display: "flex", alignItems: "center", gap: 6, cursor: "pointer", background: dass21Answers[i] === score ? "rgba(168, 85, 247, 0.2)" : "rgba(255,255,255,0.03)", padding: "10px 14px", borderRadius: 10, border: dass21Answers[i] === score ? "1px solid #A855F7" : "1px solid rgba(255,255,255,0.1)", transition: "all 0.2s" }}>
                           <div style={{ width: 14, height: 14, borderRadius: "50%", border: "2px solid", borderColor: dass21Answers[i] === score ? "#A855F7" : "rgba(255,255,255,0.3)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                               {dass21Answers[i] === score && <div style={{ width: 8, height: 8, background: "#A855F7", borderRadius: "50%" }} />}
                           </div>
                           <span style={{ fontSize: 13, color: dass21Answers[i] === score ? "#fff" : "rgba(255,255,255,0.6)" }}>{score === 0 ? "Không" : score === 1 ? "Thỉnh thoảng" : score === 2 ? "Khá nhiều" : "Hầu hết"}</span>
                        </label>
                     ))}
                  </div>
               </div>
            ))}
         </div>
         <div style={{ padding: 20, borderTop: "1px solid rgba(255,255,255,0.1)", display: "flex", gap: 12, justifyContent: "flex-end", background: "rgba(11, 13, 20, 0.5)" }}>
            <button onClick={onHide} style={{ padding: "10px 16px", borderRadius: 8, background: "transparent", border: "1px solid rgba(255,255,255,0.2)", color: "#fff", cursor: "pointer", fontWeight: 500 }}>Hủy</button>
            <button onClick={submit} disabled={busy} style={{ padding: "10px 20px", borderRadius: 8, background: "linear-gradient(135deg, #A855F7 0%, #6D28D9 100%)", border: "none", color: "#fff", fontWeight: "bold", cursor: busy ? "not-allowed" : "pointer", opacity: busy ? 0.7 : 1, boxShadow: "0 4px 15px rgba(168, 85, 247, 0.3)" }}>Nộp form DASS-21</button>
         </div>
      </div>
    </div>
  );
}
