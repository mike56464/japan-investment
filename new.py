import os
import sys

# 確保輸出支援 UTF-8 (解決 Windows cmd 下顯示 Emoji 會掛掉的問題)
try:
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

import re
import time
import json
import sys
import datetime
import requests
from google import genai
from google.genai import types
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

# ==========================================
# ⚙️ 設定區 (Linux VM 專用)
# ==========================================
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1474664376186179706/MtIa8U1EJS6tBydicPkLEiPgJa53PzBJ-PVeUvEkWDKheAuS0fKyFp_blzSR6dM524Ls"

# ⚠️ Linux VM 的絕對路徑 (已修正為 Linux 格式)
JSON_KEY_PATH = "/home/lingeiai48/project-c7e1d808-1b27-4629-b29-682ac8b02c24.json"

# 【防呆機制】檢查金鑰檔案是否存在
if not os.path.exists(JSON_KEY_PATH):
    print(f"🚨 嚴重錯誤：找不到金鑰檔案！請確認檔案是否上傳至 {JSON_KEY_PATH}")
    sys.exit(1)

# 自動讀取 Project ID
try:
    with open(JSON_KEY_PATH, 'r', encoding='utf-8') as f:
        key_data = json.load(f)
        PROJECT_ID = key_data.get("project_id")
except Exception as e:
    print(f"🚨 讀取金鑰發生錯誤: {e}")
    sys.exit(1)

# 設定環境變數供 SDK 自動讀取驗證
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = JSON_KEY_PATH

# 初始化 Google Gen AI 用戶端 (指定使用 Vertex AI 模式)
client = genai.Client(
    vertexai=True,
    project=PROJECT_ID,
    location="global",  # 依照 MIKE 設定改為 global 測試連線
    http_options={'timeout': 15.0}  # 加上超時機制，避免因為連線或模型當機導致程式無限掛起
)

# ==========================================
# 🤖 AI 分析模組 (MIKE 專屬情報分析邏輯)
# ==========================================
def ask_gemini_analysis(fund_data, jpy_rate):
    print("🧠 啟動 Gemini AI 頂級推理分析 (優先嘗試 3.1 Pro)...")

    prompt = f"""
    【系統設定】你現在是 MIKE 的私人首席財富顧問與市場情報分析師。請務必使用繁體中文，並強烈依賴「網路搜尋功能」，不僅要抓取今日最新的日本市場數據，更要深入挖掘**目前的市場傳言 (Rumors)、外資機構預測，以及大眾與投資圈的普遍共識 (Consensus)**。

    【今日市場與持倉數據】
    - 第一銀行日圓即期匯率買入：{jpy_rate}
    - 關注基金最新淨值：
    {fund_data}

    【分析任務】請依照以下架構，為 MIKE 產出一份包含「市場情緒與未公開預期」的專業投資日報：

    🗣️ 1. 市場共識與最新傳言 (Rumors & Consensus)
    - 簡述目前日本股市、日銀（BoJ）利率政策的最新官方動態。
    - **重點分析：** 目前華爾街或日本當地有什麼**最新傳言**？（例如：央行暗中干預匯市的可能、高市早苗內閣的潛在新法案）。大家「預期」接下來會發生什麼事？

    🔍 2. 核心持倉解析 (FA35 & JA96)
    - 針對「富達日本股票 ESG (FA35)」與「摩根日本 (JA96)」，結合上述的「市場情緒」與今日匯率 ({jpy_rate})，評估這兩檔基金的成分股是否能受惠於當前的市場共識。

    🎯 3. 投資情緒與信心指標 (0-100分)
    - 根據當前的「預期心理」與基本面，給出明確的綜合信心分數。
    - 條列：🟢 市場樂觀的加分項 (利多傳聞) 與 🔴 市場擔憂的減分項 (利空隱憂)。

    💡 4. MIKE 專屬操作指南
    - 給出明確決策：【 強力加碼 / 逢低布局 / 觀望 / 減碼 】（擇一）。
    - 說明觸發此決策的理由。在大家都在貪婪或恐懼的當下，MIKE 該如何反向思考或順勢而為？請給出具體的觀察點位。

    ⚠️ 5. 黑天鵝與預期落空風險
    - 點出當前市場「最害怕發生」，或者「萬一傳言落空」時，最具破壞性的 1-2 個潛在風險。

    【輸出格式要求】
    - 總字數嚴格限制在 2000 字內，資訊密度要高。
    - 善用 Markdown 標題 (`##`, `###`)、粗體 (`**`) 與 Emoji，確保 Discord 排版清晰易讀。
    - 語氣需具備情報頭子的敏銳度，既看重冰冷的數據，也洞悉市場瘋狂的心理。
    """

    models_to_try = [
        ("gemini-3.1-pro", "🌟 **[Gemini 3.1 Pro GA]**"),
        ("gemini-3.1-pro-preview", "🌠 **[Gemini 3.1 Pro Preview]**"),
        ("gemini-3.0-pro", "👑 **[Gemini 3 Pro Stable]**"),
        ("gemini-2.5-pro", "⚡ **[Gemini 2.5 Pro]**"),
        ("gemini-1.5-pro", "🛡️ **[Gemini 1.5 Pro Alias]**")
    ]

    for model_id, display_name in models_to_try:
        try:
            print(f"📡 嘗試啟動 {display_name} 核心引擎...")

            # 使用最新 SDK 的生成方式，並加入 Google 搜尋工具
            response = client.models.generate_content(
                model=model_id,
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[types.Tool(google_search=types.GoogleSearch())]
                )
            )

            if response.text:
                return f"{display_name}\n\n" + response.text
            else:
                continue

        except Exception as e:
            error_str = str(e)
            if "404" in error_str or "not found" in error_str.lower() or "403" in error_str:
                print(f"⚠️ 找不到模型或權限不足 {model_id}，嘗試下一個...")
            elif "timeout" in error_str.lower() or "deadline" in error_str.lower():
                print(f"⚠️ 呼叫 {model_id} 超時 (Timeout)，嘗試下一個...")
            else:
                print(f"❌ 呼叫 {model_id} 時發生非預期錯誤: {error_str[:120]}...")
            continue

    return "❌ 呼叫所有頂級模型皆失敗。請確認專案金鑰是否正確，或是否已在 GCP 啟用 Vertex AI。"

# ==========================================
# 📢 Discord 發送模組 (支援長文分段推播)
# ==========================================
def send_to_discord(content):
    full_msg = f"🚀 **Gemini 旗艦分析日報** ({datetime.datetime.now().strftime('%Y-%m-%d')})\n\n" + content
    
    chunk_size = 1500
    chunks = [full_msg[i:i + chunk_size] for i in range(0, len(full_msg), chunk_size)]
    
    for i, chunk in enumerate(chunks):
        payload = {"content": chunk}
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload)
        
        if response.status_code in [200, 204]:
            print(f"✅ 成功推播第 {i+1}/{len(chunks)} 部份分析至 Discord！")
        else:
            print(f"❌ 第 {i+1} 部份 Discord 發送失敗！狀態碼: {response.status_code}")
            
        if i < len(chunks) - 1:
            time.sleep(1)  # 等待 1 秒避免 Discord API 限制

# ==========================================
# 🕷️ 第一銀行爬蟲函數 (Linux VM 專用參數)
# ==========================================
def get_linux_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("window-size=1920,1080")
    # 模擬正常的瀏覽器，避免被銀行擋下
    options.add_argument("user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    return webdriver.Chrome(options=options)

def get_firstbank_jpy_rate():
    print("-" * 50)
    print("正在抓取第一銀行最新日圓即期買入匯率...")
    driver = get_linux_driver()
    try:
        url = "https://www.firstbank.com.tw/sites/fcb/touch/1565688252532"
        driver.get(url)
        time.sleep(5)
        page_text = driver.find_element(By.TAG_NAME, "body").text
        rate_match = re.search(r'日圓.*?([0-9]+\.[0-9]{3,})', page_text, re.DOTALL)
        if rate_match:
            rate = float(rate_match.group(1))
            print(f"👉 匯率: 1 JPY = {rate} TWD")
            return rate
        
        print("⚠️ 網頁改版或找不到匯率，改用預設值 0.2033")
        return 0.2033
    finally:
        driver.quit()

def get_firstbank_nav(fund_url, fund_name):
    print("-" * 50)
    print(f"正在抓取基金淨值：{fund_name}...")
    driver = get_linux_driver()
    try:
        driver.get(fund_url)
        time.sleep(5)
        page_text = driver.find_element(By.TAG_NAME, "body").text
        nav_match = re.search(r'最新淨值\s*\n*([0-9,]+\.[0-9]+)', page_text)
        nav = nav_match.group(1) if nav_match else "N/A"
        print(f"👉 淨值: {nav}")
        return nav
    finally:
        driver.quit()

# ==========================================
# 🎯 主程式
# ==========================================
def main():
    print(f"📊 Linux VM 專用 - MIKE 旗艦分析版 | " + datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

    # 1. 抓取數據
    jpy_rate = get_firstbank_jpy_rate()

    my_funds = {
        "富達日本股票 ESG 基金 (FA35)": "https://wealth.firstbank.com.tw/fund-center/fund/fund-search/fund-details?id=FA35",
        "摩根日本基金 (JA96)": "https://wealth.firstbank.com.tw/fund-center/fund/fund-search/fund-details?id=JA96"
    }

    fund_summary = ""
    for name, url in my_funds.items():
        nav = get_firstbank_nav(url, name)
        fund_summary += f"- {name}: 淨值 {nav}\n"

    # 2. AI 分析
    analysis_result = ask_gemini_analysis(fund_summary, jpy_rate)

    # 3. 推送通知
    print("📤 發送 Discord...")
    discord_msg = f"💹 **今日行情摘要：**\n{fund_summary}\n💴 **日圓匯率：** {jpy_rate}\n\n💡 **AI 深度分析：**\n{analysis_result}"
    send_to_discord(discord_msg)

    print("-" * 50)
    print("✅ 任務執行完畢！")

if __name__ == "__main__":
    main()
