import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

load_dotenv() #導入本目錄的.env 及環境參數
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN") #取得Telegram API key,並指定

# 處理 /start 指令
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("你好！我是你的 Telegram 機器人。Hello Im your Telegram bot")

# 回應一般文字訊息（Echo）
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    await update.message.reply_text(f"你說了：{user_text}")

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    print("Bot 運行中 (Polling 模式, switch to Polling mode , swith to Telegram window)...")
    app.run_polling()

if __name__ == "__main__":
    main()