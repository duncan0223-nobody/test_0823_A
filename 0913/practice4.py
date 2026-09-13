"""
practice4.py
整合 Gemini 聯網搜尋 + Telegram 推播功能
使用 Gemini API 搜尋最新資訊,並將結果透過 Telegram Bot 發送至指定頻道/群組
"""

import asyncio
import os
from dotenv import load_dotenv
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from google import genai
from google.genai import types

load_dotenv()

# Telegram 設定
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TARGET_USER_ID = 8719067870
TARGET_GROUP_ID = -5339618596
TARGET_CHANNEL_ID = -1004322810613

# Gemini 設定
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")


async def send_text_broadcast(
    chat_id: str | int,
    text: str,
    keyboard: InlineKeyboardMarkup | None = None
):
    """
    發送純文字訊息推播
    :param chat_id: 目標聊天室 ID (個人/群組/頻道)
    :param text: 訊息內容 (支援 HTML 格式)
    :param keyboard: 訊息底部的按鈕 (選填)
    """
    bot = Bot(token=TELEGRAM_TOKEN)
    try:
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard,
            disable_web_page_preview=False  # 允許顯示網址預覽
        )
        print(f"✅ 成功發送訊息至：{chat_id}")
    except Exception as e:
        print(f"❌ 發送至 {chat_id} 失敗：{e}")


def gemini_search(prompt: str) -> str:
    """
    使用 Gemini API 進行聯網搜尋
    :param prompt: 搜尋提示詞
    :return: Gemini 回應的文字內容
    """
    try:
        print(f"💬 搜尋提示：{prompt}\n")
        print("🌐 Gemini 正在自主聯網搜尋最新資料中...")
        
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
            ),
        )
        
        print("✅ 搜尋完成！\n")
        return response.text
    except Exception as e:
        print(f"❌ Gemini 搜尋失敗：{e}")
        return f"搜尋時發生錯誤：{e}"


async def main():
    # 1. 定義搜尋查詢
    search_prompt = "請查詢並告訴我今天最新的重要國際精品新聞三則（包含發生時間與簡要說明），使用繁體中文,並用美觀的排版呈現。"
    
    # 2. 執行 Gemini 聯網搜尋
    search_result = gemini_search(search_prompt)
    
    # 3. 格式化 Telegram 訊息內容
    message_text = (
        "🔍 <b>國際精品新聞快報</b>\n"
        "━━━━━━━━━━━━━━━━━\n\n"
        f"{search_result}\n\n"
        "━━━━━━━━━━━━━━━━━\n"
        "📡 <i>資料來源：Gemini 即時搜尋</i>"
    )
    
    # 4. 可選：添加互動按鈕
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🛍️ 立即下單", url="https://t.me/Guotang_LV"),
            InlineKeyboardButton("💬 聯絡店長", url="https://t.me/Guotang_LV")
        ]
    ])
    
    # 5. 發送至所有目標頻道
    targets = [
        TARGET_USER_ID,
        TARGET_GROUP_ID,
        TARGET_CHANNEL_ID
    ]
    
    for chat_id in targets:
        await send_text_broadcast(chat_id, message_text, keyboard)
        await asyncio.sleep(1)  # 避免發送過快被限制


if __name__ == "__main__":
    asyncio.run(main())