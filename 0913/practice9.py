import os
import json
import time
import csv  # 💡 改用內建 csv 套件
import logging
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai.errors import ServerError
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

# 建立記錄資料夾
LOGS_DIR = Path(__file__).parent / "chat_logs"
LOGS_DIR.mkdir(exist_ok=True)

def get_today_csv_path() -> Path:
    """取得今天的 csv 檔案路徑"""
    today = datetime.now().strftime("%Y-%m-%d")
    return LOGS_DIR / f"chat_log_{today}.csv"

def init_csv_file(filepath: Path):
    """初始化 csv 檔案，建立 UTF-8-BOM 表頭（確保 Excel 開啟不亂碼）"""
    headers = [
        "時間", "使用者名稱", "使用者ID", "聊天類型", 
        "原始訊息", "情緒", "信心指數", "需要真人", 
        "判斷依據", "建議回覆", "實際回覆"
    ]
    
    # 使用 utf-8-sig 編碼可以自動加入 BOM 頭，防止 Excel 直接打開時中文變亂碼
    with open(filepath, mode="w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        
    logger.info(f"✅ 已建立新的 CSV 記錄檔: {filepath.name}")

def save_to_csv(
    user_name: str,
    user_id: int,
    chat_type: str,
    original_message: str,
    analysis: dict,
    actual_reply: str
):
    """儲存對話記錄到 csv"""
    try:
        filepath = get_today_csv_path()
        
        # 如果檔案不存在，先建立表頭
        if not filepath.exists():
            init_csv_file(filepath)
        
        # 整理資料列
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        data_row = [
            now,
            user_name,
            user_id,
            chat_type,
            # 移除換行符號以防干擾 CSV 解析（更換為空格）
            original_message.replace("\n", " ").replace("\r", ""),
            analysis.get("sentiment", ""),
            analysis.get("confidence_score", 0.0),
            "是" if analysis.get("requires_human_agent") else "否",
            analysis.get("reasoning", "").replace("\n", " ").replace("\r", ""),
            analysis.get("suggested_reply", "").replace("\n", " ").replace("\r", ""),
            actual_reply.replace("\n", " ").replace("\r", "")
        ]
        
        # 以附加模式 (a) 寫入新資料
        with open(filepath, mode="a", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(data_row)
            
        logger.info(f"✅ 已記錄到 CSV: {filepath.name}")
        
    except Exception as e:
        logger.error(f"❌ 儲存 CSV 失敗: {e}")

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
    
    chat = client.chats.create(
        model="gemini-2.5-flash",
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json",
            temperature=0.1,
        ),
    )

    max_retries = 3
    delay = 2
    
    for attempt in range(max_retries):
        try:
            response = chat.send_message(user_message)
            return json.loads(response.text)
        except ServerError as e:
            if e.code == 503 and attempt < max_retries - 1:
                logger.warning(f"⚠️ Gemini 503 伺服器忙碌，將於 {delay} 秒後進行第 {attempt + 1} 次重試...")
                time.sleep(delay)
                delay *= 2
            else:
                logger.error(f"Gemini API 503 錯誤且已達重試上限: {e}")
                break
        except Exception as e:
            logger.error(f"Gemini API 遭遇非預期錯誤: {e}")
            break

    return {
        "sentiment": "neutral",
        "confidence_score": 0.0,
        "requires_human_agent": False,
        "reasoning": "分析過程發生例外狀況或伺服器持續超載",
        "suggested_reply": "您好，已收到您的訊息，請稍候專人為您服務。"
    }

# 指令處理
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == ChatType.PRIVATE:
        await update.message.reply_text(
            "👋 你好！我是客服情緒分析助手。\n\n"
            "發送訊息給我，我會:\n"
            "1️⃣ 分析您的訊息情緒\n"
            "2️⃣ 提供建議的回覆內容\n"
            "3️⃣ 所有對話記錄會儲存在每日 .csv 檔案中"
        )
    else:
        await update.message.reply_text(
            f"👋 大家好！我是客服情緒分析助手。\n"
            f"我會分析所有訊息並記錄在每日 CSV 報表中。"
        )

# 訊息處理主邏輯
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    raw_text = update.message.text
    chat_type = update.effective_chat.type
    user = update.message.from_user

    bot_info = await context.bot.get_me()
    bot_name = bot_info.username or ""

    is_private = chat_type == ChatType.PRIVATE

    clean_text = raw_text.replace(f"@{bot_name}", "", 1).strip()
    if not clean_text:
        clean_text = raw_text.strip()
    
    if not clean_text:
        return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

    logger.info(f"分析訊息來自 {user.username or user.first_name}: {clean_text}")
    analysis = analyze_customer_message(clean_text)

    sentiment_tag = {
        "positive": "😊 正向滿意",
        "neutral": "💬 一般中立",
        "negative": "⚠️ 輕微不滿",
        "urgent_angry": "🚨 緊急客訴"
    }.get(analysis.get("sentiment"), "💬 一般中立")

    reply_content = analysis.get("suggested_reply", "收到您的訊息，處理中。")

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

    user_name = f"@{user.username}" if user.username else user.first_name or "未知使用者"
    chat_type_str = "私訊" if is_private else f"群組: {update.effective_chat.title or '未命名群組'}"
    
    # 💡 改用 save_to_csv 儲存
    save_to_csv(
        user_name=user_name,
        user_id=user.id,
        chat_type=chat_type_str,
        original_message=raw_text,
        analysis=analysis,
        actual_reply=user_reply
    )

def main():
    if not TELEGRAM_TOKEN or not GEMINI_API_KEY:
        raise ValueError("請先確認 .env 內已設定 TELEGRAM_BOT_TOKEN 與 GEMINI_API_KEY。")

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("=" * 60)
    logger.info("🚀 Telegram 客服情緒分析 Bot 運行中...")
    logger.info(f"📊 記錄資料夾: {LOGS_DIR.absolute()}")
    logger.info(f"📄 今日記錄檔: {get_today_csv_path().name}")
    logger.info("=" * 60)
    
    app.run_polling()

if __name__ == "__main__":
    main()
