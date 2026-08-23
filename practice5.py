import gradio as gr
from google import genai
from dotenv import load_dotenv

load_dotenv()
client = genai.Client()

DEFAULT_PROMPT = "請逐步教學含視窗化操作指令, 如何使用raspberry樹莓派架設出家用的NAS伺服器?"


def generate_answer(question: str):
    if not question or not question.strip():
        return "請輸入問題！"
    interaction = client.interactions.create(
        model="gemini-3.7-flash",
        input=question,
    )
    return interaction.output_text


with gr.Blocks(title="樹莓派 NAS 架設小幫手") as demo:
    gr.Markdown("# 樹莓派 NAS 架設小幫手 (Gemini)")
    gr.Markdown("輸入任何問題，AI 將逐步教學（含視窗化操作指令）。")

    input_text = gr.Textbox(
        label="Prompt",
        value=DEFAULT_PROMPT,
        placeholder="請輸入問題...",
        submit_btn=True,
    )
    with gr.Accordion("**懶得輸入可以點選以下範例問題**", open=False):
        gr.Examples(
            examples=[
                DEFAULT_PROMPT,
                "如何使用樹莓派架設家用網頁伺服器？",
                "請問 OpenMediaVault 與 Samba 各有什麼優缺點？",
            ],
            label="問題範例",
            inputs=input_text,
        )

    output_md = gr.Markdown(label="回答結果")
    clear_btn = gr.ClearButton([input_text, output_md])

    input_text.submit(
        fn=generate_answer,
        inputs=input_text,
        outputs=output_md,
    )

if __name__ == "__main__":
    demo.launch()
