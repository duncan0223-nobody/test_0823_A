import os
import json
import logging
from dotenv import load_dotenv
from google import genai
from google.genai import types
from telegram import Update
from telegram.constants import ChatAction, ChatType
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

# 載入環境變數
load_dotenv()
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# 設定 Logging 以便追蹤與除錯
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# 初始化 Gemini 客戶端
client = genai.Client(api_key=GEMINI_API_KEY)

# 定義情緒分析函式
def analyze_customer_message(user_message: str) -> dict:
    """
    呼叫 Gemini 進行情緒分析並回傳 JSON 結構資料
    """
    system_instruction = """
    你是一位專業的 Telegram 線上客服情緒分析與應對助手。
    請分析客戶發送的訊息情緒，並特別注意台灣在地的口語語境與反諷語氣。
    
    情緒分類說明:
    - positive: 正向滿意
    - neutral: 一般詢問 / 中立
    - negative: 輕微不滿 / 抱怨
    - urgent_angry: 強烈憤怒 / 要求主管或退費
    
    如果客戶表達強烈不滿、投訴消保官、威脅退費或情緒極度憤怒，請將 requires_human_agent 設為 true。
    
    請務必以繁體中文撰寫 reasoning 與 suggested_reply，並輸出符合以下結構的 JSON 格式:
    {
        "sentiment": "positive | neutral | negative | urgent_angry",
        "confidence_score": 0.0到1.0的浮點數,
        "requires_human_agent": true 或 false,
        "reasoning": "判斷該情緒的簡短理由",
        "suggested_reply": "適合同理客戶的建議回覆內容"
    }
    """
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=user_message,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                temperature=0.1,
            ),
        )
        return json.loads(response.text)
    except Exception as e:
        logger.error(f"Gemini API 分析失敗: {e}")
        return {
            "sentiment": "neutral",
            "confidence_score": 0.0,
            "requires_human_agent": False,
            "reasoning": "分析過程發生例外狀況",
            "suggested_reply": "您好，已收到您的訊息，請稍候專人為您服務。"
        }

# 指令處理
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_info = await context.bot.get_me()
    if update.effective_chat.type == ChatType.PRIVATE:
        await update.message.reply_text("👋 你好！直接發送訊息，我會為您分析情緒並提供合適的客服回覆。")
    else:
        await update.message.reply_text(f"👋 大家好！在群組中請 @{bot_info.username} 或直接回覆我的訊息來啟用客服助手。")

# 訊息處理主邏輯
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    raw_text = update.message.text
    chat_type = update.effective_chat.type

    # 取得機器人資訊
    bot_info = await context.bot.get_me()
    bot_name = bot_info.username or ""

    is_private = chat_type == ChatType.PRIVATE
    is_mentioned = bool(bot_name and f"@{bot_name.lower()}" in raw_text.lower())
    is_reply_to_bot = bool(
        update.message.reply_to_message
        and update.message.reply_to_message.from_user
        and update.message.reply_to_message.from_user.id == bot_info.id
    )

    # 在群組中未 @機器人 且未回覆機器人訊息時忽略，避免干擾一般群聊
    if not is_private and not is_mentioned and not is_reply_to_bot:
        return

    # 清除 @BotUsername 字串
    clean_text = raw_text.lower().replace(f"@{bot_name.lower()}", "").strip()
    if not clean_text:
        return

    # 顯示「輸入中」狀態
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

    # 執行情緒分析
    analysis = analyze_customer_message(clean_text)

    # 標記需要真人介入的情境
    sentiment_tag = {
        "positive": "😊 正向滿意",
        "neutral": "💬 一般中立",
        "negative": "⚠️ 輕微不滿",
        "urgent_angry": "🚨 緊急客訴"
    }.get(analysis.get("sentiment"), "💬 一般中立")

    reply_content = analysis.get("suggested_reply", "收到您的訊息，處理中。")

    if analysis.get("requires_human_agent"):
        reply_message = (
            f"【{sentiment_tag}｜需要專人介入】\n"
            f"{reply_content}\n\n"
            f"（系統已通知管理員/真人客服進線處理）"
        )
    else:
        reply_message = reply_content

    # 回覆使用者
    await update.message.reply_text(
        reply_message,
        reply_to_message_id=update.message.message_id
    )

def main():
    if not TELEGRAM_TOKEN or not GEMINI_API_KEY:
        raise ValueError("請先確認 .env 內已設定 TELEGRAM_BOT_TOKEN 與 GEMINI_API_KEY。")

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🚀 Telegram 客服情緒分析 Bot 運行中...")
    app.run_polling()

if __name__ == "__main__":
    main()