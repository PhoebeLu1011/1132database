import os
import gradio as gr
import pandas as pd
from fpdf import FPDF
from datetime import datetime
import time
from dotenv import load_dotenv
from google import genai
from playwright.sync_api import sync_playwright

#載入 API
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

# 環境變數設定
email = os.getenv("GOOGLE_EMAIL")
ntnumail = os.getenv("NTNU_MAIL")
password = os.getenv("GOOGLE_PASSWORD")
gemini_api_key = os.getenv("GEMINI_API_KEY")

# 中文字型處理
def get_chinese_font_file():
    fonts_path = r"C:\Windows\Fonts"
    for name in ["kaiu.ttf"]:
        path = os.path.join(fonts_path, name)
        if os.path.exists(path):
            return os.path.abspath(path)
    return None

# 生成 PDF 
def generate_pdf(text):
    pdf = FPDF(format="A4")
    pdf.add_page()
    font_path = get_chinese_font_file()
    if not font_path:
        return "錯誤：未找到中文字型"
    pdf.add_font("ChineseFont", "", font_path, uni=True)
    pdf.set_font("ChineseFont", "", 12)
    pdf.multi_cell(0, 10, text)
    filename = f"health_plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    pdf.output(filename)
    return filename

#AI
def agent_analyze_and_suggest(csv_file, user_prompt):
    if csv_file:
        df = pd.read_csv(csv_file.name)
        block_csv = df.to_csv(index=False)
        prompt = (
            "你是一位專業健康管理師兼健身教練。\n"
            "以下是使用者提供的資料：\n"
            f"{block_csv}\n\n"
            "請根據資料分析飲食與運動問題，並給出一天三餐的飲食建議與一週的運動計劃。\n\n"
            "請整理為清楚的條列式。"
            "\n\n附加指令：\n" + user_prompt
        )
    else:
        prompt = (
            "你是一位專業健康管理師兼健身教練。\n"
            "使用者提供了以下描述：\n"
            f"{user_prompt}\n\n"
            "請給出一天三餐的飲食建議與一週的運動計劃，條列式呈現。"
        )

    response = client.models.generate_content(
        model="gemini-2.5-pro-exp-03-25",
        contents=[prompt]
    )
    return response.text.strip()

# 轉成 PDF
def export_pdf_from_text(ai_output_text):
    return generate_pdf(ai_output_text)

# Playwright 自動輸入到 Google Keep 
def open_keep_and_fill(note_text):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # 有畫面
        page = browser.new_page()

        # 1. 開啟 Google Keep
        page.goto("https://accounts.google.com/")

        # 輸入 Email
        page.fill('input[type="email"]', email)
        page.get_by_text("下一步").click()
        page.wait_for_timeout(2000)  # 等2秒

        # 輸入 Email
        page.fill('input[type="username"]', ntnumail)
        page.wait_for_timeout(2000)  # 等2秒

        # 輸入 Password
        page.fill('input[type="password"]', password)
        page.click('button[type="submit"]')
        page.wait_for_timeout(5000)  # 等5秒看是否完成登入
        

        # 新增到Google Keep
        page.goto("https://keep.google.com/")
        page.wait_for_timeout(3000)
        
        print("請手動點開新增記事輸入框...")
        time.sleep(15)  # 給30秒時間登入和打開輸入框
        browser.close()

#  預設提示 
default_prompt = """使用者希望改善身體健康，請根據提供的今日運動訓練資料，進行分析，並根據今日的運動菜單，給出明日運動訓練菜單的建議與飲食菜單建議"""

# Gradio 介面
with gr.Blocks() as demo:
    gr.Markdown("# AI 健康顧問：飲食與訓練建議生成器")

    with gr.Row():
        csv_input = gr.File(label="上傳健康資料 CSV（可選）")
        user_input = gr.Textbox(label="輸入使用者描述或目標", lines=8, value=default_prompt)

    ai_output = gr.Textbox(label=" AI 生成建議結果", lines=20, interactive=False)
    pdf_output = gr.File(label=" 下載生成的 PDF")

    with gr.Row():
        analyze_btn = gr.Button(" 請 AI 分析並建議")
        export_btn = gr.Button(" 生成 PDF")
        send_keep_btn = gr.Button(" 自動填入 Google Keep")

    # 按鈕
    analyze_btn.click(fn=agent_analyze_and_suggest,
                      inputs=[csv_input, user_input],
                      outputs=[ai_output])

    export_btn.click(fn=export_pdf_from_text,
                     inputs=[ai_output],
                     outputs=[pdf_output])

    send_keep_btn.click(fn=open_keep_and_fill,
                        inputs=[ai_output],
                        outputs=[])

demo.launch()
