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

# 你的群組 ID
TARGET_GROUP_ID = -5361899778       #自己測試使用-只有bot

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
    請分析客戶發送的訊息情緒,並特別注意台灣在地的口語語境與反諷語氣。
    
    情緒分類說明:
    - positive: 正向滿意
    - neutral: 一般詢問 / 中立
    - negative: 輕微不滿 / 抱怨
    - urgent_angry: 強烈憤怒 / 要求主管或退費
    
    如果客戶表達強烈不滿、投訴消保官、威脅退費或情緒極度憤怒,請將 requires_human_agent 設為 true。
    
    請務必以繁體中文撰寫 reasoning 與 suggested_reply,並輸出符合以下結構的 JSON 格式:
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
            model="gemini-3.8-flash",
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
            "suggested_reply": "您好,已收到您的訊息,請稍候專人為您服務。"
        }

# 指令處理
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_info = await context.bot.get_me()
    if update.effective_chat.type == ChatType.PRIVATE:
        await update.message.reply_text(
            "👋 你好！我是客服情緒分析助手。\n\n"
            "發送訊息給我,我會:\n"
            "1️⃣ 分析您的訊息情緒\n"
            "2️⃣ 自動轉發分析結果到客服群組\n"
            "3️⃣ 提供建議的回覆內容"
        )
    else:
        await update.message.reply_text(f"👋 大家好！在群組中請 @{bot_info.username} 或直接回覆我的訊息來啟用客服助手。")

# 訊息處理主邏輯
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    raw_text = update.message.text
    chat_type = update.effective_chat.type
    user = update.message.from_user

    # 取得機器人資訊
    bot_info = await context.bot.get_me()
    bot_name = bot_info.username or ""

    is_private = chat_type == ChatType.PRIVATE

    # 清除 @BotUsername 字串(如果有的話)
    clean_text = raw_text.replace(f"@{bot_name}", "", 1).strip()
    if not clean_text:
        clean_text = raw_text.strip()
    
    if not clean_text:
        return

    # 顯示「輸入中」狀態
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

    # 執行情緒分析
    logger.info(f"分析訊息來自 {user.username or user.first_name}: {clean_text}")
    analysis = analyze_customer_message(clean_text)

    # 標記需要真人介入的情境
    sentiment_tag = {
        "positive": "😊 正向滿意",
        "neutral": "💬 一般中立",
        "negative": "⚠️ 輕微不滿",
        "urgent_angry": "🚨 緊急客訴"
    }.get(analysis.get("sentiment"), "💬 一般中立")

    reply_content = analysis.get("suggested_reply", "收到您的訊息,處理中。")

    # 回覆給使用者
    if analysis.get("requires_human_agent"):
        user_reply = (
            f"【{sentiment_tag}｜需要專人介入】\n"
            f"{reply_content}\n\n"
            f"（系統已通知管理員/真人客服進線處理）"
        )
    else:
        user_reply = reply_content

    await update.message.reply_text(
        user_reply,
        reply_to_message_id=update.message.message_id
    )

    # 同時發送分析報告到指定群組
    try:
        # 取得使用者資訊
        user_info = f"@{user.username}" if user.username else user.first_name
        chat_info = f"私訊" if is_private else f"群組: {update.effective_chat.title}"
        
        # 組合群組通知訊息
        if analysis.get("requires_human_agent"):
            group_message = (
                f"<b>【客服通知｜{sentiment_tag}｜需要專人介入】</b>\n\n"
                f"<b>來源:</b> {chat_info}\n"
                f"<b>使用者:</b> {user_info}\n"
                f"<b>原始訊息:</b>\n{raw_text}\n\n"
                f"<b>情緒分析:</b>\n"
                f"• 情緒: {analysis.get('sentiment')}\n"
                f"• 信心指數: {analysis.get('confidence_score'):.2f}\n"
                f"• 判斷依據: {analysis.get('reasoning')}\n\n"
                f"<b>建議回覆:</b>\n{reply_content}\n\n"
                f"⚠️ <b>系統已通知管理員/真人客服進線處理</b>"
            )
        else:
            group_message = (
                f"<b>【客服通知｜{sentiment_tag}】</b>\n\n"
                f"<b>來源:</b> {chat_info}\n"
                f"<b>使用者:</b> {user_info}\n"
                f"<b>原始訊息:</b>\n{raw_text}\n\n"
                f"<b>情緒分析:</b>\n"
                f"• 情緒: {analysis.get('sentiment')}\n"
                f"• 信心指數: {analysis.get('confidence_score'):.2f}\n"
                f"• 判斷依據: {analysis.get('reasoning')}\n\n"
                f"<b>建議回覆:</b>\n{reply_content}"
            )
        
        # 發送到目標群組
        await context.bot.send_message(
            chat_id=TARGET_GROUP_ID,
            text=group_message,
            parse_mode="HTML"
        )
        logger.info(f"✅ 分析報告已發送到群組 {TARGET_GROUP_ID}")
        
    except Exception as e:
        logger.error(f"❌ 發送到群組失敗: {e}")

def main():
    if not TELEGRAM_TOKEN or not GEMINI_API_KEY:
        raise ValueError("請先確認 .env 內已設定 TELEGRAM_BOT_TOKEN 與 GEMINI_API_KEY。")

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("=" * 60)
    logger.info("🚀 Telegram 客服情緒分析 Bot 運行中...")
    logger.info(f"📱 目標群組 ID: {TARGET_GROUP_ID}")
    logger.info("=" * 60)
    
    app.run_polling()

if __name__ == "__main__":
    main()