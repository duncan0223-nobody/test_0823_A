import os
import gradio as gr

with gr.Blocks(title="Zero-shot Text Generation") as demo:
    gr.Markdown("# Zero-shot Text Generation (Interactions API)")
    
    input_text = gr.Textbox(
        label="Prompt",
        placeholder="請輸入問題...",
        submit_btn=True
    )
    with gr.Accordion("**懶得輸入可以點選以下範例問題**", open=False):
        gr.Examples(
            examples=[
                "請問台灣的首都是哪裡？",
                "請用三句話簡介人工智慧的發展歷史。",
                "請給出五個適合初學者的 Python 學習建議。"
            ],
            label="問題範例",
            inputs=input_text
        )
    output_text = gr.Markdown()

    @input_text.submit(inputs=input_text, outputs=[input_text, output_text])
    def generate_text(input_str: str):
        
        return None, f"## {input_str}\n\n"

demo.launch()