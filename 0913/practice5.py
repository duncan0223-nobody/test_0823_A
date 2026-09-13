import os
import json
import time
from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai.errors import ServerError

# 載入環境變數
load_dotenv()

# 1. 初始化 Gemini Client
client = genai.Client()

def analyze_customer_message(user_message: str) -> dict:
    """
    分析客戶訊息的情緒
    
    回傳的字典包含:
    - sentiment: 情緒類型 (positive, neutral, negative, urgent_angry)
    - confidence_score: 信心指數 (0.0 到 1.0)
    - requires_human_agent: 是否需要轉接真人 (True/False)
    - reasoning: 判斷理由
    - suggested_reply: 建議回覆內容
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
    
    請以 JSON 格式回覆，包含以下欄位:
    {
        "sentiment": "情緒類型(positive/neutral/negative/urgent_angry)",
        "confidence_score": 0.0到1.0的信心指數,
        "requires_human_agent": true或false,
        "reasoning": "判斷該情緒的簡短理由或關鍵字說明",
        "suggested_reply": "適合給該使用者的同理心回覆建議"
    }
    """

    # 2. 改用符合最新 SDK 建議的 Chat 模式來初始化對話 (消除 AFC 警告)
    chat = client.chats.create(
        model="gemini-3.8-flash",
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json",
            temperature=0.1,  # 降低隨機性以提升分類穩定度
        ),
    )

    # 3. 呼叫模型並處理 503 UNAVAILABLE 伺服器超載重試機制
    max_retries = 3
    delay = 2
    
    for attempt in range(max_retries):
        try:
            response = chat.send_message(user_message)
            # 解析 JSON 結果並回傳
            return json.loads(response.text)
        except ServerError as e:
            # 如果遇到先前碰到的 503 錯誤，且還沒超過重試次數，就自動等待重試
            if e.code == 503 and attempt < max_retries - 1:
                print(f"⚠️ Google API 伺服器忙碌中 (503)，將在 {delay} 秒後重試第 {attempt + 1} 次...")
                time.sleep(delay)
                delay *= 2  # 遞增等待時間（2s -> 4s）
            else:
                raise e  # 超過重試次數或非 503 錯誤，直接拋出例外

# 4. 測試執行
if __name__ == "__main__":
    test_messages = [
        "請問我的訂單 #883921 什麼時候會出貨呢?謝謝!",
    ]

    for msg in test_messages:
        print(f"\n--- 測試訊息: {msg} ---")
        analysis = analyze_customer_message(msg)
        
        # 使用字典的方式取值
        print(f"情緒標籤: {analysis['sentiment']}")
        print(f"信心指數: {analysis['confidence_score']}")
        print(f"轉接真人: {'是' if analysis['requires_human_agent'] else '否'}")
        print(f"判斷依據: {analysis['reasoning']}")
        print(f"建議回覆: {analysis['suggested_reply']}")
