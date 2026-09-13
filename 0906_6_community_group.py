import os
import re  # 引入正規表達式，方便不區分大小寫取代
from dotenv import load_dotenv
from google import genai
from telegram import Update
from telegram.constants import ChatAction, ChatType
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

load_dotenv()
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# 初始化 Gemini 客戶端
client = genai.Client(api_key=GEMINI_API_KEY)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == ChatType.PRIVATE:
        await update.message.reply_text("👋 你好！直接發送訊息即可與我對話。")
    else:
        await update.message.reply_text(f"👋 大家好！在群組中請 @{context.bot.username} 或回覆我的訊息來提問。")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    raw_text = update.message.text
    chat_type = update.effective_chat.type
    bot_name = context.bot.username

    is_private = chat_type == ChatType.PRIVATE
    is_mentioned = bot_name and f"@{bot_name.lower()}" in raw_text.lower()
    is_reply_to_bot = (
        update.message.reply_to_message
        and update.message.reply_to_message.from_user
        and update.message.reply_to_message.from_user.id == context.bot.id
    )

    # 非私聊且沒有 @機器人 也沒有回覆機器人時，直接略過
    if not is_private and not is_mentioned and not is_reply_to_bot:
        return

    # 使用不區分大小寫的方式去除 @BotUsername，留下純問題文字
    clean_text = re.sub(f"@{bot_name}", "", raw_text, flags=re.IGNORECASE).strip()
    if not clean_text:
        return

    # 發送正在輸入中的動態
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

    try:
        # 修正：使用正確的 google-genai SDK 語法
        response = client.models.generate_content(
            model="gemini-3.7-flash",
            contents=clean_text,
            config={
                "system_instruction": "你是一個 Telegram 群組 AI 助理，請用繁體中文給出簡潔有條理的回答。"
            }
        )
        # 修正：讀取結果使用 .text
        reply_html = response.text or "抱歉，無法生成回應。"
    except Exception as e:
        print(f"❌ Gemini API 發生錯誤: {e}")
        reply_html = "🤖 抱歉，我現在大腦有點混亂，請稍後再試。"

    # 指定 reply_to_message_id 回覆該則訊息
    await update.message.reply_text(
        reply_html,
        reply_to_message_id=update.message.message_id
    )

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🚀 Gemini 群組 Telegram Bot 運行中...")
    app.run_polling()

if __name__ == "__main__":
    main()
