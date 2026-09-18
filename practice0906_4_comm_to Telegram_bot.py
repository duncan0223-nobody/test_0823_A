"""
項目名稱：Telegram + Gemini 智慧對話機器人
適用對象：Python 初學者
核心技術：python-telegram-bot (v20+) 與 Google GenAI SDK (最新正式版 v1)
"""

import os
import ssl
from dotenv import load_dotenv
from google import genai
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
from telegram.request import HTTPXRequest

# ==========================================
# 1. 環境準備與初始化設定
# ==========================================

# 讀取專案目錄下的 .env 檔案，並將裡面的設定值載入到 Python 的全域環境變數中
load_dotenv()

# 從環境變數中撈出我們需要的 API Key 和 Token
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# 【新手科普：全域 SSL 防禦設定】
# 當你使用 Kiro、防毒軟體或特定公司網路時，網路流量會被攔截並換成「本地憑證」。
# 這會導致 Python 底層在發送 HTTPS 安全連線時，因為找不到標準官方憑證而報錯。
# 以下幾行程式碼的作用是告訴 Python：「這台電腦現在的網路環境有特殊代理，請直接信任並發送請求，不用檢查憑證鏈。」
os.environ["PYTHONHTTPSVERIFY"] = "0"
os.environ["SSL_CERT_FILE"] = ""
try:
    # 針對 Python 內建的 ssl 模組，建立一個「不檢查憑證」的預設連線環境
    ssl._create_default_https_context = ssl._create_unverified_context
except AttributeError:
    pass

# 初始化 Google Gemini 的官方客戶端
# http_options 指定 api_version 為 'v1'，代表我們使用目前官方最穩定、最安全的主流正式版本
client = genai.Client(
    api_key=GEMINI_API_KEY,
    http_options={'api_version': 'v1'}
)


# ==========================================
# 2. 機器人事件處理函式 (Event Handlers)
# ==========================================

# 【新手科普：非同步程式設計 async / await】
# 網路機器人需要同時處理很多人的訊息。如果用傳統的寫法（同步），當 AI 還在想答案時，整支程式就會卡住，其他人傳訊息就會沒反應。
# 定義成 `async def` 代表這是一個「非同步」函式；而遇到需要花時間連線的步驟，就用 `await` 讓程式先去處理別人的事，等結果回來再繼續。

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    當使用者在 Telegram 輸入 `/start` 命令時，會觸發這個函式。
    :param update: 代表 Telegram 傳過來的最新發生事件（包含是誰傳的、傳了什麼內容）。
    :param context: 機器人的上下文工具箱，可以用來查資料或執行特殊控制。
    """
    welcome_text = (
        "👋 你好！我是串接 Google 最新 Gemini 3.6 Flash 的 Telegram AI 助理。\n\n"
        "你可以直接向我提問任何問題、請我寫程式、翻譯或總結文章！"
    )
    
    # 安全性檢查：確認真的有收到使用者的對話視窗
    if update.message:
        # await 關鍵字：等待這封歡迎訊息發送成功給使用者後，再繼續往下執行
        await update.message.reply_text(welcome_text)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    當使用者發送一般文字訊息（非指令）時，會觸發這個函式。
    我們會把使用者的問題收集起來，丟給 Gemini API，再把答案回傳。
    """
    # 檢查機制：如果沒有收到訊息，或者訊息裡面不是文字（例如貼圖或圖片），就直接結束不處理
    if not update.message or not update.message.text:
        return

    user_query = update.message.text        # 撈出使用者在 Telegram 視窗輸入的文字
    chat_id = update.effective_chat.id      # 撈出當前對話視窗的唯一識別 ID

    # 【小巧思】調用 Telegram 內建功能：在視窗上方顯示「小助理正在輸入中... (typing...)」的動態提示
    # 這樣可以讓使用者知道機器人有收到，正在努力通訊中，提升使用者體驗。
    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

    # 在 VS Code 控制台（Terminal）印出日誌，方便開發者觀察進度
    print(f"📥 收到使用者訊息: {user_query}")

    # 使用 try...except 異常處理機制：萬一網路突然斷線或 API Key 壞掉，程式不會直接崩潰當機
    try:
        print("🔄 正在透過 Interactions API 呼叫 Gemini 3.6 Flash...")
        
        # 呼叫 Google 官方的 Interactions 介面來與 AI 對話
        interaction = client.interactions.create(
            model="gemini-3.6-flash", # 指定要使用的 AI 模型
            input=user_query,          # 傳入使用者的問題
            # system_instruction：系統指令，用來規範 AI 的「人設」、「口吻」或「回答規則」
            system_instruction="你是一個繁體中文的 Telegram 智慧助理，請用繁體中文給出清晰、條理分明的回答。"
        )

        # 從 Google 回傳的結果中，把 AI 的文字抽取出來
        # 如果裡面是空的，就給予一個預設的提示替代字
        reply_text = interaction.output_text or "抱歉，目前無法生成回應。"
        print(f"🤖 Gemini 回覆生成成功!")
        
        # 將 AI 的精采回覆，回傳發送給 Telegram 的使用者
        await update.message.reply_text(reply_text)

    except Exception as e:
        # 萬一發生錯誤（例如 503 伺服器超載或網路逾時），會跑到這裡
        error_msg = f"發生錯誤：{str(e)}"
        print(f"❌ 呼叫 Gemini 發生異常: {error_msg}")
        
        # 也把錯誤訊息回傳給 Telegram，方便直接在手機上確認錯誤狀況
        await update.message.reply_text(error_msg)


# ==========================================
# 3. 程式主入口與機器人啟動
# ==========================================

def main():
    """ 程式的主入口，負責檢查設定、綁定處理器並維持機器人長駐執行 """
    
    # 安全檢查：確保開發者有確實填寫隱密金鑰
    if not TELEGRAM_TOKEN:
        print("❌ 錯誤：請先在 .env 中設定 TELEGRAM_BOT_TOKEN")
        return
    if not GEMINI_API_KEY:
        print("❌ 錯誤：請先在 .env 中設定 GEMINI_API_KEY")
        return

    # 【核心修正點：客製化 Telegram 連線要求】
    # 因為使用了 Kiro 工具或特定代理，Telegram 的基礎連線也需要特製。
    # 建立一個連線逾時時間設為 20 秒的 Request 管理物件。
    custom_request = HTTPXRequest(connect_timeout=20.0, read_timeout=20.0)
    
    # 暴力但完美潛入套件底層的關鍵：
    # 直接在字典檔設定中，塞入 "verify": False，強制叫 httpx 不要去校驗 Kiro 換掉的本地憑證。
    custom_request._client_kwargs["verify"] = False

    # 建立並配置 Telegram 機器人應用程式
    app = (
        ApplicationBuilder()
        .token(TELEGRAM_TOKEN)     # 告訴程式要控制哪一隻 Telegram 機器人
        .request(custom_request)   # 強制使用我們上面做好的「免憑證檢查」連線物件
        .build()
    )

    # 【註冊處理器 (Handlers)】：告訴機器人，收到什麼指令時該找誰處理
    # 當收到使用者發送 `/start` 命令時 ➡️ 交給 start 函式處理
    app.add_handler(CommandHandler("start", start))
    
    # 當收到一般文字訊息，且「不是指令」時 ➡️ 交給 handle_message 函式處理
    # filters.TEXT 代表只抓文字，~filters.COMMAND 代表排除了斜線開頭的指令
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🚀 Gemini Telegram Bot 運行中 (Polling 模式)... 按 Ctrl+C 結束")
    
    # 啟動 Polling（輪詢）模式：機器人會開始每秒不間斷地向 Telegram 官方伺服器詢問是否有新訊息。
    # 除非我們手動按下 Ctrl+C 關閉，否則這行會讓程式像伺服器一樣一直維持長駐執行。
    app.run_polling()


# 標準的 Python 開頭防護：確保這支檔案是被直接執行的，而不是被當成套件匯入的
if __name__ == "__main__":
    main()
