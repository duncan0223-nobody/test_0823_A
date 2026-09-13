"""
01_basic_search.py
Gemini 聯網搜尋核心教學：Google Search Grounding 基礎接地搜尋
"""

import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

prompt = "請查詢並告訴我今天最新的重要國際精品新聞三則（包含發生時間與簡要說明），使用繁體中文。"
print(f"💬 提問：{prompt}\n")
print("🌐 Gemini 正在自主聯網搜尋最新資料中...")

# 使用官方標準模型名稱與 Tool 設定
response = client.models.generate_content(
    model="gemini-3.6-flash",
    contents=prompt,
    config=types.GenerateContentConfig(
        tools=[{"google_search": {}}],
    ),
)

print("\n🤖 Gemini 聯網搜尋回答：")
print(response.text)