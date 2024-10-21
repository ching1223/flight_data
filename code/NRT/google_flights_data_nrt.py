import requests
import json
from datetime import datetime
import logging
import smtplib
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import timedelta
import time
import csv
import os
import logging
import re

# Discord Webhook URL
WEBHOOK_URL = "https://discord.com/api/webhooks/1295434884361228450/zwTbBwZK3hryiEqFiCa6HWGXzZtWHRldTizl4BUNyZcw_0IHb94kbmikoKwOeFObbGBk"

# 發送 Discord 通知的函數
def send_discord_notification(message):
    data = {
        "content": message  # 要發送的訊息
    }
    response = requests.post(WEBHOOK_URL, data=json.dumps(data), headers={"Content-Type": "application/json"})
    
    if response.status_code == 204:
        logging.info("Discord 通知發送成功")
    else:
        logging.error(f"Failed to send Discord notification: {response.status_code}, {response.text}")

# 動態創建目錄
def create_directory_if_not_exists(path):
    if not os.path.exists(path):
        os.makedirs(path)

# 設定日誌文件路徑
log_dir = './logs'
create_directory_if_not_exists(log_dir)  # 確保日誌目錄存在
log_file = os.path.join(log_dir, 'flight_scrape_nrt.log')
logging.basicConfig(filename=log_file, level=logging.INFO)
logging.info('This is an info message')

# 設置 Selenium 驅動
options = Options()
options.add_argument("--headless")  # 如果需要顯示瀏覽器，請去掉此行
service = Service("/opt/homebrew/bin/chromedriver")  # 指定 ChromeDriver 的路徑
driver = webdriver.Chrome(service=service, options=options)

# 打開 Google Travel 的航班頁面
url = "https://www.google.com/travel/flights/search?tfs=CBwQAhoqEgoyMDI0LTEyLTIwKABqDAgCEggvbS8wZnRreHIMCAISCC9tLzA3ZGZrQAFIAXABggELCP___________wGYAQI&authuser=0"
driver.get(url)

# 等待頁面完全加載
flight_links = WebDriverWait(driver, 20).until(
    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "li.pIav2d"))
)
print(f"找到 {len(flight_links)} 個航班")

# 設置一個計數器來記錄抓取成功的航班數量
success_count = 0

# CSV 文件目錄處理
output_dir = './data/data'
create_directory_if_not_exists(output_dir)
csv_file_path = os.path.join(output_dir, f'google_flights_data_nrt.csv')

# 準備寫入 CSV 檔案
with open(csv_file_path , 'a', newline='', encoding='utf-8-sig') as csv_file:    
    csv_writer = csv.writer(csv_file)
    # 寫入標題
    csv_writer.writerow([
        "出發日期", "出發時間", "出發機場代號", 
        "抵達時間", "抵達機場代號", "航空公司", 
        "停靠站數量", "停留時間", "飛行時間", 
        "是否過夜", "機型", "航班代碼", "艙等", "價格歷史"
    ])

    # 遍歷並點擊每個航班列表項，打開新頁面
    for index in range(len(flight_links)):
        # 重新獲取航班連結，防止 StaleElementReferenceException
        flight_links = driver.find_elements(By.CSS_SELECTOR, "li.pIav2d")
        
        # 檢查是否超出範圍
        if index >= len(flight_links):
            print(f"索引 {index} 超出範圍，停止操作")
            break
        
        # 點擊
        flight_links[index].click()

        # 等待新頁面加載
        time.sleep(10)

        # 初始化各個欄位
        departure_date, departure_time, arrival_time, departure_airport, arrival_airport = "null", "null", "null", "null", "null"
        airline, layover, layover_time, flight_duration, overnight, aircraft, flight_number = "null", "null", "null", "null", "null", "null", "null"
        
        # 點擊「查看更多」按鈕
        try:
            more_button = driver.find_element(By.XPATH, "//div[@class='i18Ypf']//div[@class='VfPpkd-dgl2Hf-ppHlrf-sM5MNb']//button")
            more_button.click()
        except NoSuchElementException:
            print("未找到「查看更多」按鈕")
        
        time.sleep(8) # 等待更多內容加載
        
        try:
            # 抓取出發日期
            departure_date_element = driver.find_element(By.XPATH, "//span[contains(@class, 'mv1WYe')]").get_attribute("innerHTML")[:9]
            departure_date = departure_date_element.strip()
        except NoSuchElementException:
            print("出發日期抓取失敗")

        try:
            # 抓取出發時間
            departure_time_element = driver.find_element(By.XPATH, "//div[@class='wtdjmc YMlIz ogfYpf tPgKwe']").get_attribute("aria-label")
            departure_time = departure_time_element.split("：")[-1].strip()  # 抓取時間部分
        except NoSuchElementException:
            print("出發時間抓取失敗")

        try:
            # 抓取抵達時間
            arrival_time_element = driver.find_element(By.XPATH, "//div[@class='XWcVob YMlIz ogfYpf tPgKwe']").get_attribute("aria-label")
            arrival_time = arrival_time_element.split("：")[-1].strip()  # 抓取時間部分
        except NoSuchElementException:
            print("抵達時間抓取失敗")

        try:
            # 抓取出發和抵達機場代碼
            airport_elements = driver.find_elements(By.XPATH, "//span[contains(@class, 'qeoz6e HKHSfd')]/following-sibling::span[@dir='ltr']")
            departure_airport = airport_elements[0].get_attribute("innerHTML").strip("()")  # 第一個是出發機場
            arrival_airport = airport_elements[1].get_attribute("innerHTML").strip("()")    # 第二個是抵達機場
        except NoSuchElementException:
            print("機場代碼抓取失敗")

        try:
            # 抓取航空公司
            airline = driver.find_element(By.XPATH, "//div[contains(@class, 'sSHqwe')]/span[1]").text
        except NoSuchElementException:
            print("航空公司抓取失敗")

        try:
            # 抓取行程時間
            travel_time_element = driver.find_element(By.XPATH, "//div[@class='gvkrdb AdWm1c tPgKwe ogfYpf']").get_attribute("innerHTML")
            # 使用正則表達式提取飛行時間，可以處理「X 小時」和「X 小時 Y 分鐘」
            match = re.search(r'(\d+ 小時(?: \d+ 分鐘)?)', travel_time_element)
            flight_duration = match.group(1) if match else "未找到飛行時間"
        except NoSuchElementException:
            print("飛行時間抓取失敗")

        try:
            # 抓取停靠站數量
            layover_element = driver.find_element(By.XPATH, "//div[@class='EfT7Ae AdWm1c tPgKwe']//span[@class='ogfYpf']").get_attribute("aria-label")
            layover = layover_element.split(" flight.")[0]  # 提取 "1 stop" 或 "Non-stop"
        except NoSuchElementException:
            layover = "Non-stop"

        if layover != "直達航班。":
            try:
                # 抓取停留時間
                layover_info_element = driver.find_element(By.XPATH, '//div[@class = "tvtJdb eoY5cb y52p7d"]').get_attribute("innerHTML")
                # 更新正則表達式，支持「小時和分鐘」或僅「分鐘」
                time_pattern = r'(\d+\s*小時\s*\d+\s*分鐘|\d+\s*分鐘)'
                match = re.search(time_pattern, layover_info_element)
                layover_time = match.group(1) if match else "未找到停留時間"
            except NoSuchElementException:
                layover_time = "未找到停留時間"
        else:
            layover_time = "Non-stop"

        try:
            # 檢查是否有 "Overnight" 元素
            overnight_element = driver.find_element(By.XPATH, '//div[@class="qj0iCb" and contains(text(), "Overnight")]')
            overnight = "Yes"
        except NoSuchElementException:
            overnight = "No"
        
        try:
            # 抓取機型
            aircraft = driver.find_element(By.XPATH, '//div[@class="MX5RWe sSHqwe y52p7d"]/span[@class = "Xsgmwe"][last()]').get_attribute("innerHTML")
        except NoSuchElementException:
            print("機型抓取失敗")

        try:
            # 抓取航班代碼
            flight_number_element = driver.find_element(By.XPATH, '//div[@class="MX5RWe sSHqwe y52p7d"]/span[contains(@class, "Xsgmwe")][2]').get_attribute("innerHTML")
            flight_number = flight_number_element.replace('&nbsp;', ' ').strip()  # 去除前後空白
        except NoSuchElementException:
            flight_number = "未找到航班代碼"
            
        try:
            # 抓取艙等
            cabin_class = driver.find_element(By.XPATH, '//span[contains(@class, "Xsgmwe")]/div').get_attribute("innerHTML")            
        except NoSuchElementException:
            cabin_class = "未找到艙等"

        # 獲取今天的日期
        today = datetime.today()

        def replace_days_ago_with_date(price_history_text):
            price_with_date = []
    
            # 匹配 "60 天前 - $xxx" 格式的數據
            pattern = r"(\d+)\s*天前\s*-\s*\$([\d,]+)"
            matches = re.findall(pattern, price_history_text)
    
            for match in matches:
                days_ago = int(match[0])
                price = match[1]
        
                # 計算具體日期
                specific_date = today - timedelta(days=days_ago)
                formatted_date = specific_date.strftime("%m/%d")  # 以 "月/日" 格式顯示
        
                # 將 "60 天前 - $xxx" 替換為 "月/日 - $xxx"
                price_with_date.append(f"{formatted_date} - ${price}")
    
            return ", ".join(price_with_date)

        # 修改價格歷史的部分
        try:
            elements = driver.find_elements(By.XPATH, "//*[name()='g' and @class='ke9kZe-LkdAo-RbRzK-JNdkSc pKrx3d']")
            price_history = [element.get_attribute("aria-label") for element in elements]
            price_history_with_dates = [replace_days_ago_with_date(ph) for ph in price_history]
        except NoSuchElementException:
            price_history_with_dates = "未找到價格歷史"


        # 將資料寫入 CSV
        csv_writer.writerow([
            departure_date, departure_time, departure_airport,
            arrival_time, arrival_airport, airline,
            layover, layover_time, flight_duration,
            overnight, aircraft, flight_number, cabin_class,
            ', '.join(price_history_with_dates)  # 將價格歷史串接為一個字符串
        ])

        # 每次成功抓取航班後，計數器加 1
        success_count += 1

        # 返回上一頁
        driver.back()

        # 等待返回加載完成
        time.sleep(2)

# 關閉瀏覽器
driver.quit()

# 顯示抓取的總航班數量
logging.info(f"總共抓取了 {success_count} 個航班")
print(f"總共抓取了 {success_count} 個航班")

# 更新執行狀態
status_file_dir = './data/NRT'
create_directory_if_not_exists(status_file_dir)
status_file_path = os.path.join(status_file_dir, 'execution_status_nrt.txt')

with open(status_file_path, 'a') as status_file:
    status_file.write(f'Executed on {datetime.now()} - Scraped {success_count} flights\n')

# 在程式結尾發送 Discord 通知
send_discord_notification(f"Flight scraping completed at {datetime.now()}. Scraped {success_count} flights.")