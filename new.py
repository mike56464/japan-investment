from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import re
import time
import datetime


def get_firstbank_nav(fund_url):
    # 設置 Chrome 為無頭模式 (背景默默執行，不會跳出視窗干擾你)
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("window-size=1920,1080")

    try:
        # 啟動自動化瀏覽器 (Python 3.12 的 Selenium 4 會自動處理驅動程式)
        driver = webdriver.Chrome(options=options)
        driver.get(fund_url)

        # 給第一銀行的動態網頁 5 秒鐘的時間，確保數字完全載入
        time.sleep(5)

        # 抓取整個網頁渲染後的純文字
        page_text = driver.find_element(By.TAG_NAME, "body").text

        # 針對你截圖的排版特徵進行正則表達式暴力搜尋
        # 尋找「最新淨值」與「日圓」之間的數字
        nav_match = re.search(r'最新淨值\s*\n*([0-9,]+\.[0-9]+)\s*日圓', page_text)
        # 尋找 202X/XX/XX 格式的日期
        date_match = re.search(r'(202[0-9]{1}/[0-9]{2}/[0-9]{2})', page_text)

        nav = nav_match.group(1) if nav_match else "解析失敗，請確認網址或網頁載入狀態"
        date = date_match.group(1) if date_match else "解析日期失敗"

        driver.quit()
        return nav, date

    except Exception as e:
        return f"發生錯誤: {e}", ""


# ⚠️ 重要：請把下面這兩個網址，換成你在第一銀行網站上看到的真實網址
my_funds = {
    "富達日本股票 ESG 基金 (FA35)": "https://wealth.firstbank.com.tw/fund-center/fund/fund-search/fund-details?id=FA35",
    "摩根日本基金 (JA96)": "https://wealth.firstbank.com.tw/fund-center/fund/fund-search/fund-details?id=JA96&utm_source=wealth&utm_medium=website&utm_campaign=%EF%BD%9C%E7%AC%AC%E4%B8%80%E5%95%86%E6%A5%AD%E9%8A%80%E8%A1%8C%E8%82%A1%E4%BB%BD%E6%9C%89%E9%99%90%E5%85%AC%E5%8F%B8"  # 也就是你截圖那個畫面的網址
}

print(f"📊 第一銀行專用 - 基金淨值抓取系統 | 執行時間: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("-" * 50)

for fund_name, url in my_funds.items():
    if "請貼上" in url:
        print(f"正在查詢：{fund_name}...\n👉 錯誤：請先在程式碼中填入真實網址！\n" + "-" * 50)
        continue

    print(f"正在模擬瀏覽器查詢：{fund_name}... (約需 5-8 秒)")
    nav, update_date = get_firstbank_nav(url)
    print(f"👉 最新淨值: {nav}")
    print(f"🕒 淨值日期: {update_date}")
    print("-" * 50)