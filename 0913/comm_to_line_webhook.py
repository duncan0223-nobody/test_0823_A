from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn

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

@app.post("/webhook")
async def line_webhook(request: Request):
    """
    LINE Webhook 專用節點
    接收 LINE 的 webhook 請求並回傳 status ok
    """
    # 可以在這裡取得 LINE 傳來的資料(如果需要的話)
    # body = await request.json()
    # print(f"收到 webhook 資料: {body}")
    
    # 回傳 status ok 給 LINE 伺服器
    return JSONResponse(content={"status": "ok"}, status_code=200)

if __name__ == "__main__":
    # 使用 port 8000 - 不需要 root 權限
    uvicorn.run(app, host="0.0.0.0", port=8000)
    #line webhook 的連結.....a
    #test file