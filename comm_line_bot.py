import os
import json
import logging
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage
)
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent
)
from google import genai
from google.genai import types
import uvicorn

# 載入環境變數
load_dotenv()
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.environ.get("LINE_CHANNEL_SECRET")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# 設定 Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 初始化 LINE Bot
configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# 初始化 Gemini 客戶端
client = genai.Client(api_key=GEMINI_API_KEY)

app = FastAPI()

@app.get("/", response_class=HTMLResponse)
async def read_root():
    html_content = """
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>FastAPI 簡單網頁</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            }
            .container {
                text-align: center;
                background: white;
                padding: 50px;
                border-radius: 10px;
                box-shadow: 0 10px 25px rgba(0,0,0,0.2);
            }
            h1 {
                color: #333;
                margin-bottom: 20px;
            }
            p {
                color: #666;
                font-size: 18px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 歡迎使用 FastAPI!</h1>
            <p>這是一個簡單的 FastAPI 網頁應用程式</p>
            <p>運行於 Port 8000</p>
        </div>
    </body>
    </html>
    """
    return html_content

def chat_with_gemini(user_message: str) -> str:
    """
    使用 Gemini API 進行對話
    """
    try:
        response = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=user_message,
            config=types.GenerateContentConfig(
                temperature=0.7,
            ),
        )
        return response.text
    except Exception as e:
        logger.error(f"Gemini API 呼叫失敗: {e}")
        return "抱歉,我現在無法回應。請稍後再試。"

@handler.add(MessageEvent, message=TextMessageContent)
def handle_text_message(event):
    """
    處理 LINE 文字訊息事件
    """
    user_message = event.message.text
    logger.info(f"收到使用者訊息: {user_message}")
    
    # 使用 Gemini 產生回覆
    reply_text = chat_with_gemini(user_message)
    logger.info(f"Gemini 回覆: {reply_text}")
    
    # 回覆訊息給使用者
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply_text)]
            )
        )

@app.post("/webhook")
async def line_webhook(request: Request):
    """
    LINE Webhook 專用節點
    接收 LINE 的 webhook 請求並處理訊息
    """
    # 取得 X-Line-Signature 表頭
    signature = request.headers.get("X-Line-Signature", "")
    
    # 取得請求的 body
    body = await request.body()
    body_str = body.decode('utf-8')
    
    logger.info(f"收到 webhook 請求")
    
    try:
        # 處理 webhook body
        handler.handle(body_str, signature)
    except InvalidSignatureError:
        logger.error("無效的簽章")
        raise HTTPException(status_code=400, detail="Invalid signature")
    except Exception as e:
        logger.error(f"處理 webhook 時發生錯誤: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
    return JSONResponse(content={"status": "ok"}, status_code=200)

if __name__ == "__main__":
    # 使用 port 8000 - 不需要 root 權限
    uvicorn.run(app, host="0.0.0.0", port=8000)