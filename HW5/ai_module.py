import os
import pandas as pd
from dotenv import load_dotenv
from datetime import datetime
from fpdf import FPDF
from google import genai
from playwright.sync_api import sync_playwright
import time


# 載入 .env 檔案中的環境變數
load_dotenv()


# 初始化 Gemini client
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

# Google Keep 登入資訊
email = os.getenv("GOOGLE_EMAIL")
ntnumail = os.getenv("NTNU_MAIL")
password = os.getenv("GOOGLE_PASSWORD")

# 中文字型尋找
def get_chinese_font_file():
    fonts_path = r"C:\\Windows\\Fonts"
    for name in ["kaiu.ttf"]:
        path = os.path.join(fonts_path, name)
        if os.path.exists(path):
            return os.path.abspath(path)
    return None

# 生成 PDF 報告
def generate_pdf(text):
    pdf = FPDF(format="A4")
    pdf.add_page()
    font_path = get_chinese_font_file()
    if not font_path:
        return "錯誤：未找到中文字型"
    pdf.add_font("ChineseFont", "", font_path, uni=True)
    pdf.set_font("ChineseFont", "", 12)
    pdf.multi_cell(0, 10, text)
    filename = f"static/health_plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    pdf.output(filename)
    return filename

# Gemini AI 健康分析與建議

def agent_analyze_and_suggest(csv_file, user_prompt):
    if csv_file:
        df = pd.read_csv(csv_file)
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




# 使用 Playwright 登入 Google Keep 並貼上記事

def open_keep_and_fill(note_text):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        page.goto("https://accounts.google.com/")
        page.fill('input[type="email"]', email)
        page.get_by_text("下一步").click()
        page.wait_for_timeout(2000)

        page.fill('input[type="username"]', ntnumail)
        page.wait_for_timeout(2000)

        page.fill('input[type="password"]', password)
        page.click('button[type="submit"]')
        page.wait_for_timeout(5000)

        page.goto("https://keep.google.com/")
        page.wait_for_timeout(3000)
        print("請手動點開新增記事輸入框...")
        time.sleep(15)
        browser.close()


