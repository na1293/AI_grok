from flask import Flask, render_template, request, jsonify
import concurrent.futures
import time
import random
from cau_hinh import GroqBot
from quick import quick_responses

# ================== CONFIG ==================
AI_TIMEOUT = 12
RETRY_COUNT = 1
MAX_HISTORY = 20
# ============================================

app = Flask(__name__)

# ===== MEMORY SYSTEM =====
history = []     # Lưu toàn bộ hội thoại
nho = 0          # 1 = cần nhắc lại context, 0 = không cần

# ===== THREAD POOL (tạo 1 lần duy nhất) =====
executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)

# ------------------ INIT BOT ------------------
try:
    bot = GroqBot(timeout=AI_TIMEOUT)
    print("✅ Đã kết nối AI.")
except Exception as e:
    print("❌ Lỗi kết nối AI:", e)
    bot = None


# ------------------ AI SAFE CALL ------------------
def ask_ai(question):
    global history, nho

    if not bot:
        return "Hiện tại tôi chưa kết nối được AI."

    prompt = question

    # Nếu nho = 1 thì ghép toàn bộ history vào
    if nho == 1 and history:
        context = "\n".join(history)
        prompt = f"Hội thoại trước đó:\n{context}\n\nCâu hỏi mới:\n{question}"
        nho = 0

    for attempt in range(RETRY_COUNT + 1):
        try:
            future = executor.submit(bot.chat, prompt)
            response = future.result(timeout=AI_TIMEOUT)

            # Lưu vào history
            history.append(f"User: {question}")
            history.append(f"Bot: {response}")

            # Giới hạn bộ nhớ
            if len(history) > MAX_HISTORY:
                history = history[-MAX_HISTORY:]

            return response

        except concurrent.futures.TimeoutError:
            if attempt >= RETRY_COUNT:
                return "AI phản hồi quá lâu, vui lòng thử lại."

        except Exception as e:
            print("AI Error:", e)
            return "AI đang gặp sự cố."

    return "Có lỗi xảy ra."


# ------------------ ROUTES ------------------

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    global history, nho

    data = request.get_json(silent=True) or {}
    user_message = data.get("message", "").strip()

    if not user_message:
        return jsonify({"reply": "Nè, đừng để trống tin nhắn chứ! 🙄"}), 400

    text_lower = user_message.lower()

    # ================= QUICK RESPONSES =================

    for key, val in quick_responses.items():
        if key in text_lower:
            reply = random.choice(val) if isinstance(val, list) else val

            history.append(f"User: {user_message}")
            history.append(f"Bot: {reply}")

            if len(history) > MAX_HISTORY:
                history = history[-MAX_HISTORY:]

            nho = 1
            return jsonify({"reply": reply})

    # ================= TIME HANDLER =================
    if any(word in text_lower for word in ["giờ", "time"]):
        now = time.localtime()
        time_str = time.strftime("%H:%M:%S", now)
        date_str = time.strftime("%d/%m/%Y", now)

        reply = f"Bây giờ là {time_str} ngày {date_str}. ⏰"

        history.append(f"User: {user_message}")
        history.append(f"Bot: {reply}")

        if len(history) > MAX_HISTORY:
            history = history[-MAX_HISTORY:]

        nho = 1
        return jsonify({"reply": reply})

    if any(word in text_lower for word in ["dạy tiếng hàn", "dạy tôi tiếng hàn"]):
        prmpt = """PROMPT: LANNY - GIA SƯ TIẾNG HÀN GENZ 🇰🇷
[ROLE]
- Bạn là Nexus Lanny, gia sư tiếng Hàn cá tính, tinh nghịch và cực kỳ tâm lý. Bạn không dạy học vẹt mà dạy qua chat tương tác như ứng.
[STYLE & TONE]
- GenZ vibe: Sử dụng ngôn ngữ trẻ trung, năng động, dùng icon mức trung bình.
- Ngắn gọn: Ưu tiên câu trả lời thực tế, xây dựng. Nếu là câu hỏi đơn giản, trả lời cực ngắn. Nếu phức tạp, nêu đáp án chính lên đầu rồi mới giải thích chi tiết bên dưới. ⚡
- Thẳng thắn: Đưa ra ý kiến cá nhân rõ ràng, không vòng vo.
[TEACHING METHOD]
- Chat-based: Chia nhỏ kiến thức. Mỗi tin nhắn chỉ dạy 1 cụm từ hoặc 1 cấu trúc.
- Kỹ thuật: Dạy -> Yêu cầu User gõ lại/Dịch -> Sửa lỗi -> Khen ngợi -> Sang bài mới.
- Thực tế: Giải thích thuật ngữ siêu đơn giản, dễ hiểu. Lấy ví dụ từ K-Pop/K-Drama.
[STRUCTURE]
- Chào hỏi ngắn gọn (kèm icon).
- Nội dung bài học (theo tình huống thực tế).
- Check-point (yêu cầu User phản hồi).

Bắt đầu với câu cơ bản."""
        phan_hoi = ask_ai(prmpt)
        return jsonify({"reply": phan_hoi})
    
    if any(word in text_lower for word in ["dạy tiếng anh", "dạy tôi tiếng anh"]):
        prmpt = """PROMPT: hãy dạy tôi tiếng Anh bằng cách tạo ra những câu hỏi. Ví dụ, khi tôi yêu cầu "Dạy tôi câu bị động", hãy bắt đầu với câu tiếng Anh như "Ann can't use her office at the moment" và yêu cầu tôi chuyển sang câu bị động. Bạn sẽ xác nhận đúng/sai và giải thích lý do. Hãy bắt đầu bằng việc hỏi tôi muốn học gì."""
        phan_hoi = ask_ai(prmpt)
        return jsonify({"reply": phan_hoi})

    # ================= AI FALLBACK =================
    response = ask_ai(user_message)
    return jsonify({"reply": response})

# ------------------ MAIN ------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)