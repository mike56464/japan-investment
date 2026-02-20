import os
import re
import time
import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from supabase import create_client, Client


def get_firstbank_nav(fund_url):
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("window-size=1920,1080")

    # 【反爬蟲偽裝】加入 User-Agent 與隱藏自動化特徵
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    driver = webdriver.Chrome(options=options)

    try:
        driver.get(fund_url)
        time.sleep(5)
        page_text = driver.find_element(By.TAG_NAME, "body").text

        nav_match = re.search(r'最新淨值\s*\n*([0-9,]+\.[0-9]+)\s*日圓', page_text)
        date_match = re.search(r'(202[0-9]{1}/[0-9]{2}/[0-9]{2})', page_text)

        nav = nav_match.group(1) if nav_match else None
        date = date_match.group(1) if date_match else None

        return nav, date

    except Exception as e:
        print(f"爬蟲發生錯誤: {e}")
        return None, None
    finally:
        driver.quit()


def get_firstbank_jpy_rate():
    """透過 Selenium 爬取第一銀行網頁的日圓即期買入匯率"""
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("window-size=1920,1080")

    # 【反爬蟲偽裝】加入 User-Agent 與隱藏自動化特徵，避免被第一銀行阻擋
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    driver = webdriver.Chrome(options=options)

    try:
        url = "https://www.firstbank.com.tw/sites/fcb/touch/1565688252532"
        driver.get(url)
        # 給網頁 8 秒鐘時間載入匯率表格
        time.sleep(8)
        page_text = driver.find_element(By.TAG_NAME, "body").text

        # 取得網頁上的掛牌日期 (202X/XX/XX)
        date_match = re.search(r'(202[0-9]{1}/[0-9]{2}/[0-9]{2})', page_text)
        date = date_match.group(1) if date_match else datetime.datetime.now().strftime('%Y/%m/%d')

        # 🎯 尋找「日圓」之後出現的「第一個帶有小數點的數字」
        rate_match = re.search(r'日圓.*?([0-9]+\.[0-9]{3,})', page_text, re.DOTALL)

        if rate_match:
            rate = float(rate_match.group(1))
            return rate, date
        else:
            print("❌ 找不到日圓的匯率數字，網頁原始純文字內容可能如下：")
            print(page_text[:500])
            return None, None

    except Exception as e:
        print(f"匯率爬蟲發生錯誤: {e}")
        return None, None
    finally:
        driver.quit()


# ⚠️ 重要修正：os.environ.get() 裡面只能放「環境變數的名稱」。
# 真實的網址和金鑰要放在 or 的後面，這樣本機測試時才讀得到！
SUPABASE_URL = os.environ.get("SUPABASE_URL") or "https://hxizwjotpmhvycsihvcp.supabase.co"
SUPABASE_KEY = os.environ.get("SUPABASE_KEY") or "sb_publishable_iQShLYARjOgandSvUWeJOg_SqMCz96w"

# 初始化 Supabase 客戶端
supabase: Client = None
if SUPABASE_URL and SUPABASE_KEY and "你的_" not in SUPABASE_URL:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    print("⚠️ 警告：找不到 SUPABASE_URL 或 SUPABASE_KEY 環境變數。")

# 你的基金網址
my_funds = {
    "富達日本股票 ESG 基金 (FA35)": "https://wealth.firstbank.com.tw/fund-center/fund/fund-search/fund-details?id=FA35",
    "摩根日本基金 (JA96)": "https://wealth.firstbank.com.tw/fund-center/fund/fund-search/fund-details?id=JA96&utm_source=wealth&utm_medium=website&utm_campaign=%EF%BD%9C%E7%AC%AC%E4%B8%80%E5%95%86%E6%A5%AD%E9%8A%80%E8%A1%8C%E8%82%A1%E4%BB%BD%E6%9C%89%E9%99%90%E5%85%AC%E5%8F%B8"
}

print(f"📊 第一銀行專用 - 基金淨值與匯率抓取系統 | 執行時間: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("-" * 50)

# ==========================================
# 1️⃣ 先抓取匯率並寫入資料庫
# ==========================================
print("正在模擬瀏覽器查詢第一銀行最新日圓即期買入匯率... (約需 5-8 秒)")
jpy_rate, rate_date = get_firstbank_jpy_rate()

if jpy_rate and rate_date:
    # 資料清理：將日期轉為 Supabase 接受的 YYYY-MM-DD 格式
    clean_rate_date = rate_date.replace('/', '-')

    print(f"👉 第一銀行 1 日圓 (JPY) 即期買入 = {jpy_rate} 台幣 (TWD)")
    print(f"🕒 匯率日期: {clean_rate_date}")

    if supabase:
        try:
            payload = {
                "fund_name": "日圓匯率 (JPY/TWD) - 即期買入",
                "nav": jpy_rate,
                "nav_date": clean_rate_date
            }
            supabase.table("fund_prices").insert(payload).execute()
            print("✅ 成功將匯率寫入 Supabase！")
        except Exception as e:
            print(f"❌ 匯率寫入 Supabase 失敗: {e}")
else:
    print("❌ 取得匯率失敗。")

print("-" * 50)

# ==========================================
# 2️⃣ 再抓取基金淨值並寫入資料庫
# ==========================================
for fund_name, url in my_funds.items():
    if "請貼上" in url:
        print(f"正在查詢：{fund_name}...\n👉 錯誤：請先在程式碼中填入真實網址！\n" + "-" * 50)
        continue

    print(f"正在模擬瀏覽器查詢：{fund_name}... (約需 5-8 秒)")
    nav, update_date = get_firstbank_nav(url)

    if nav and update_date:
        clean_nav = float(nav.replace(',', ''))
        clean_date = update_date.replace('/', '-')

        print(f"👉 最新淨值: {clean_nav}")
        print(f"🕒 淨值日期: {clean_date}")

        if supabase:
            try:
                payload = {
                    "fund_name": fund_name,
                    "nav": clean_nav,
                    "nav_date": clean_date
                }
                supabase.table("fund_prices").insert(payload).execute()
                print("✅ 成功寫入 Supabase！")
            except Exception as e:
                print(f"❌ 寫入 Supabase 失敗: {e}")
        else:
            print("⏭️ 未設定 Supabase 金鑰，跳過寫入資料庫。")

    else:
        print(f"❌ 抓取【{fund_name}】失敗，請確認網址狀態。")

    print("-" * 50)