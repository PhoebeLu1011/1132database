from playwright.sync_api import sync_playwright
import os
from dotenv import load_dotenv
import time
import csv
from datetime import datetime

# HW3讀取 .env 檔案
load_dotenv()
TIMETREE_EMAIL = os.getenv("TIMETREE_EMAIL")
TIMETREE_PASSWORD = os.getenv("TIMETREE_PASSWORD")

def scrape_timetree(keyword):
    events = []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)  # 顯示瀏覽器
    page = browser.new_page()

    print("啟動瀏覽器，開始登入")

    print(f"Email: {TIMETREE_EMAIL}")
    print(f"Password: {'*' * len(TIMETREE_PASSWORD)}")  # 隱藏密碼

    # 進入 Facebook 登入頁面
    page.goto("https://timetreeapp.com/signin")
    page.wait_for_timeout(3000)


    if page.locator("input[name='email']").is_visible():
        page.fill("input[name='email']", TIMETREE_EMAIL)
    else:
        print("找不到 email 輸入框！")


    # HW3使用 .env 讀取帳號密碼
    page.fill("input[name='email']",TIMETREE_EMAIL)
    page.fill("input[name='password']", TIMETREE_PASSWORD)
    page.screenshot(path="debug_1_after_login.png")

    # 按下登入按鈕
    page.click("[data-test-id='signin-form-submit']")
   

    # 等待登入完成
    page.wait_for_timeout(5000)
    print("登入成功！")
    
    #HW3
    # 直接前往個人頁面
    page.goto("https://timetreeapp.com/calendars")
    page.wait_for_timeout(3000)
    print("進入個人首頁")
    page.screenshot(path="debug_2_after_profile.png")


    calendar_name_target = "[Midterm]"  # 目標行事曆名稱
    search_button = page.locator("span.ttfont-search")  # 這是你的搜尋按鈕 class
    search_button.click()
    page.wait_for_timeout(3000)

    page.fill("input.css-d4yh9d", calendar_name_target) 
    page.keyboard.press("Enter")  # 按下 Enter 鍵
    page.wait_for_timeout(5000)

    print(f"已搜尋到所有{calendar_name_target}")
    page.screenshot(path="search_result.png")

    browser.close()



   
