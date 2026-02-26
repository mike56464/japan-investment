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
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    driver = webdriver.Chrome(options=options)
    
    try:
        driver.get(fund_url)
        # 【重要修改】：雲端自動化環境(如 GitHub Actions)跑得比較慢，將等待時間延長至 10 秒
        time.sleep(10)
        page_text = driver.find_element(By.TAG_NAME, "body").text

        # 稍微放寬正則表達式，不強制要求後面一定要加上 "日圓"，增加容錯率
        nav_match = re.search(r'最新淨值\s*\n*([0-9,]+\.[0-9]+)', page_text)
        date_match = re.search(r'(202[0-9]{1}/[0-9]{2}/[0-9]{2})', page_text)

        nav = nav_match.group(1) if nav_match else None
        date = date_match.group(1) if date_match else None

        # 【加入除錯機制】：如果沒抓到資料，就把爬蟲當下看到的畫面印出來
        if not nav or not date:
            print(f"⚠️ 找不到基金淨值或日期！網頁載入可能未完成，或者被彈出視窗阻擋。")
            print(f"👉 網頁前 500 字元內容如下：\n{page_text[:500]}")
            print("-" * 30)

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
    
    # 【反爬蟲偽裝】加入 User-Agent 與隱藏自動化特徵
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    driver = webdriver.Chrome(options=options)
    
    try:
        url = "https://www.firstbank.com.tw/sites/fcb/touch/1565688252532"
        driver.get(url)
        time.sleep(8)
        page_text = driver.find_element(By.TAG_NAME, "body").text

        date_match = re.search(r'(202[0-9]{1}/[0-9]{2}/[0-9]{2})', page_text)
        date = date_match.group(1) if date_match else datetime.datetime.now().strftime('%Y/%m/%d')

        rate_match = re.search(r'日圓.*?([0-9]+\.[0-9]{3,})', page_text, re.DOTALL)
        
        if rate_match:
            rate = float(rate_match.group(1))
            return rate, date
        else:
            print("❌ 找不到日圓的匯率數字。")
            return None, None

    except Exception as e:
        print(f"匯率爬蟲發生錯誤: {e}")
        return None, None
    finally:
        driver.quit()


SUPABASE_URL = os.environ.get("SUPABASE_URL") or "https://hxizwjotpmhvycsihvcp.supabase.co"
SUPABASE_KEY = os.environ.get("SUPABASE_KEY") or "sb_publishable_iQShLYARjOgandSvUWeJOg_SqMCz96w"

supabase: Client = None
if SUPABASE_URL and SUPABASE_KEY and "你的_" not in SUPABASE_URL:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    print("⚠️ 警告：找不到 SUPABASE_URL 或 SUPABASE_KEY。")

my_funds = {
    "富達日本股票 ESG 基金 (FA35)": "https://wealth.firstbank.com.tw/fund-center/fund/fund-search/fund-details?id=FA35",
    "摩根日本基金 (JA96)": "https://wealth.firstbank.com.tw/fund-center/fund/fund-search/fund-details?id=JA96&utm_source=wealth&utm_medium=website&utm_campaign=%EF%BD%9C%E7%AC%AC%E4%B8%80%E5%95%86%E6%A5%AD%E9%8A%80%E8%A1%8C%E8%82%A1%E4%BB%BD%E6%9C%89%E9%99%90%E5%85%AC%E5%8F%B8"
}

print(f"📊 第一銀行專用 - 系統測試版 (v5.2 雲端環境除錯版) | {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("-" * 50)

# ==========================================
# 🎯 獨立任務 1：處理「匯率」資料 (只寫入 exchange_rates 表格)
# ==========================================
print("正在抓取第一銀行最新日圓即期買入匯率...")
jpy_rate, rate_date = get_firstbank_jpy_rate()

if jpy_rate and rate_date:
    clean_rate_date = rate_date.replace('/', '-')
    print(f"👉 匯率: 1 JPY = {jpy_rate} TWD (日期: {clean_rate_date})")
    
    if supabase:
        try:
            rate_payload = {
                "currency_code": "JPY",
                "rate": jpy_rate,
                "rate_date": clean_rate_date  
            }
            
            try:
                # 先嘗試最基本的 insert
                res = supabase.table("exchange_rates").insert(rate_payload).execute()
                print(f"✅ 成功將匯率寫入專屬的【exchange_rates】資料表！")
            except Exception as inner_e:
                # 如果是重複資料導致的錯誤，改用 upsert
                if "duplicate key" in str(inner_e).lower() or "23505" in str(inner_e):
                    res = supabase.table("exchange_rates").upsert(rate_payload, on_conflict="currency_code,rate_date").execute()
                    print(f"✅ 成功【更新】匯率到專屬的【exchange_rates】資料表！")
                else:
                    raise inner_e

        except Exception as e:
            print("\n" + "="*50)
            print("🚨 匯率寫入 Supabase 失敗！請檢查以下幾點：")
            print("1. 您是否已經在 Supabase 執行了 CREATE TABLE exchange_rates 的 SQL 語法？")
            print("2. 您的 exchange_rates 表格是否開啟了 RLS (Row Level Security) 阻擋了寫入？")
            print(f"👉 【系統給出的真實錯誤原因】：{e}")
            print("="*50 + "\n")
else:
    print("❌ 取得匯率失敗。")

print("-" * 50)


# ==========================================
# 🎯 獨立任務 2：處理「基金淨值」資料 (只寫入 fund_prices 表格)
# ==========================================
for fund_name, url in my_funds.items():
    if "請貼上" in url:
        continue

    print(f"正在抓取基金淨值：{fund_name}...")
    nav, update_date = get_firstbank_nav(url)
    
    if nav and update_date:
        clean_nav = float(nav.replace(',', ''))
        clean_date = update_date.replace('/', '-')

        print(f"👉 淨值: {clean_nav} (日期: {clean_date})")

        if supabase:
            try:
                fund_payload = {
                    "fund_name": fund_name,
                    "nav": clean_nav,
                    "nav_date": clean_date
                }
                supabase.table("fund_prices").insert(fund_payload).execute()
                print(f"✅ 成功將基金淨值寫入專屬的【fund_prices】資料表！")
            except Exception as e:
                print(f"❌ 基金淨值寫入失敗: {e}")
    print("-" * 50)
