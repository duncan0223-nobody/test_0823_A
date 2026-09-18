# ============================================================
# 🚨 終極全域修正：必須放在程式碼最頂端，強迫 Python 忽略 SSL 憑證
# ============================================================
import os
import ssl

try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

# 阻斷 httpx, requests, urllib3 去尋找本機損毀或遺失的 CA 憑證包
os.environ["CURL_CA_BUNDLE"] = ""
os.environ["PYTHONHTTPSVERIFY"] = "0"
# ============================================================

import logging
from datetime import datetime
from dotenv import load_dotenv  
from telegram import Update
from telegram.request import HTTPXRequest
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ==========================================
# 1. 記錄設定 (Logging)
# ==========================================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 您的本機記錄路徑設定
LOG_DIR = r"c:\github\test_0823_A\test_0823_A\0913\chat_logs"
os.makedirs(LOG_DIR, exist_ok=True)
TODAY_STR = datetime.now().strftime("%Y-%m-%d")
CSV_FILE_PATH = os.path.join(LOG_DIR, f"chat_log_{TODAY_STR}.csv")

# 使用官方支援的 httpx_kwargs 字典，將 verify=False 完美傳入底層
custom_request = HTTPXRequest(
    connection_pool_size=8,
    httpx_kwargs={"verify": False}
)

# ==========================================
# 2. Bot 功能邏輯處理
# ==========================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """處理 /start 指令"""
    await update.message.reply_text("您好！我是客服情緒分析 Bot，請輸入您想測試的對話。")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """處理使用者訊息並進行情緒分析與記錄"""
    user_text = update.message.text
    user_id = update.message.from_user.id
    username = update.message.from_user.username or "Unknown"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # -------------------------------------------------------------
    # 📝 這裡保留或替換您原本處理 Gemini / 情緒分析的邏輯
    # -------------------------------------------------------------
    sentiment_result = "中性"
    if any(word in user_text for word in ["生氣", "不爽", "爛", "差勁"]):
        sentiment_result = "負面/憤怒"
    elif any(word in user_text for word in ["謝謝", "棒", "讚", "滿意"]):
        sentiment_result = "正面/滿意"

    # 記錄至本機 CSV 檔案
    try:
        file_exists = os.path.exists(CSV_FILE_PATH)
        with open(CSV_FILE_PATH, mode="a", encoding="utf-8-sig") as f:
            if not file_exists:
                f.write("時間,使用者ID,帳號,訊息內容,情緒分析結果\n")
            f.write(f'"{timestamp}","{user_id}","{username}","{user_text}","{sentiment_result}"\n')
    except Exception as e:
        logger.error(f"寫入 CSV 失敗: {e}")
    # -------------------------------------------------------------

    # 回覆使用者
    reply_msg = f"已收到您的訊息！\n📊 偵測情緒：{sentiment_result}"
    await update.message.reply_text(reply_msg)

# ==========================================
# 3. 主程式進入點
# ==========================================
def main():
    logger.info("============================================================")
    logger.info("🚀 Telegram 客服情緒分析 Bot 運行中...")
    logger.info(f"📊 記錄資料夾: {LOG_DIR}")
    logger.info(f"📄 今日記錄檔: chat_log_{TODAY_STR}.csv")
    logger.info("============================================================")

    # ⭕ 絕對路徑修正：精準鎖定上一層根目錄的 .env 檔案路徑
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    env_path = os.path.join(project_root, ".env")
    
    # 強制指定絕對路徑載入環境變數
    load_dotenv(dotenv_path=env_path)

    # 讀取環境變數
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

    # 驗證必要環境變數是否存在
    if not TELEGRAM_TOKEN or not GEMINI_API_KEY:
        logger.error("錯誤: 系統找不到 TELEGRAM_TOKEN 或 GEMINI_API_KEY 環境變數！")
        logger.error(f"🔍 程式目前嘗試讀取的絕對路徑為: {env_path}")
        logger.error("請確認該路徑下是否確實存有 .env 檔案，且檔案內包含這兩個變數。")
        return

    # 建立 Application 並餵入雙重保險的 custom_request
    application = (
        Application.builder()
        .token(TELEGRAM_TOKEN)
        .request(custom_request)
        .build()
    )

    # 註冊處理指令與一般文字的監聽器
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # 開始輪詢 (Polling)
    application.run_polling()

if __name__ == '__main__':
    main()
