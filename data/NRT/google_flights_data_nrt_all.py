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
    data = {"content": message}
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
log_dir = '/home/runner/work/flight_data/flight_data/logs'
create_directory_if_not_exists(log_dir)
log_file_path = os.path.join(log_dir, 'flight_scrape_nrt_all.log')
logging.basicConfig(filename=log_file_path, level=logging.INFO)
logging.info(f'Starting the flight data scrape at {datetime.now()}')

# 設置 Selenium 驅動
options = Options()
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")
options.add_argument("--disable-software-rasterizer")
options.add_argument("--headless")
service = Service("/opt/homebrew/bin/chromedriver")
driver = webdriver.Chrome(service=service, options=options)

def scrape_flights(target_date_str):
    target_date = datetime.strptime(target_date_str, "%Y-%m-%d")
    success_count = 0  # 總共抓取的航班數量
    
    url = "https://www.google.com/travel/flights/search?tfs=CBwQAhoqEgoyMDI0LTEyLTE5KABqDAgCEggvbS8wZnRreHIMCAISCC9tLzA3ZGZrQAFIAXABggELCP___________wGYAQI&authuser=0"
    driver.get(url)

    # 點擊日期選擇器
    try:
        departure_date_picker = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CLASS_NAME, 'TP4Lpb'))
        )
        departure_date_picker.click()
        print("成功點擊出發日期選擇器")
    except Exception as e:
        print("無法找到出發日期選擇器", e)

    time.sleep(3)

    # 選擇具體日期
    try:
        specific_date = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, f"//div[@class='WhDFk Io4vne' and @data-iso='{current_date.strftime('%Y-%m-%d')}']//div[@role='button']"))
        )
        specific_date.click()
        print(f"成功選擇出發日期 {current_date.strftime('%Y 年 %m 月 %d 日')}")
    except Exception as e:
        print(f"無法選擇出發日期 {current_date.strftime('%Y-%m-%d')}", e)
        
    # 點擊 "Done" 按鈕
    try:
        done_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//div[@class="WXaAwc"]//div//button'))
        )
        done_button.click()
        print("成功點擊 'Done' 按鈕")
    except Exception as e:
        print("無法找到 'Done' 按鈕", e)
        
    time.sleep(5)

    flight_links = WebDriverWait(driver, 20).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "li.pIav2d"))
    )
    print(f"找到 {len(flight_links)} 個航班")
        
    # CSV 文件目錄處理
    output_dir = './data/data'
    create_directory_if_not_exists(output_dir)
    csv_file_path = os.path.join(output_dir, f'google_flights_data_nrt.csv')
    # 準備寫入 CSV 檔案
    with open(csv_file_path, 'a', newline='', encoding='utf-8-sig') as csv_file:           
        csv_writer = csv.writer(csv_file)

        # 寫入標題
        csv_writer.writerow([
            "出發日期", "出發時間", "出發機場代號", 
            "抵達時間", "抵達機場代號", "航空公司", 
            "停靠站數量", "停留時間", "飛行時間", 
            "是否過夜", "機型", "航班代碼", "艙等", "價格歷史"
        ])
        
        # 遍歷並點擊每個航班
        for index in range(len(flight_links)):
            try:
                # 重新獲取航班連結，防止 StaleElementReferenceException
                flight_links = driver.find_elements(By.CSS_SELECTOR, "li.pIav2d")
                flight_links[index].click()
                time.sleep(10)

                # 初始化各個欄位
                departure_date, departure_time, arrival_time, departure_airport, arrival_airport = "null", "null", "null", "null", "null"
                airline, layover, layover_time, flight_duration, overnight, aircraft, flight_number, cabin_class = "null", "null", "null", "null", "null", "null", "null", "null"

                # 抓取資料
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
                    
                    if len(airport_elements) > 0:
                        departure_airport = airport_elements[0].get_attribute("innerHTML").strip("()")  # 第一個是出發機場
                    else:
                        departure_airport = "未找到出發機場代碼"
                    
                    if len(airport_elements) > 1:
                        arrival_airport = airport_elements[1].get_attribute("innerHTML").strip("()")  # 第二個是抵達機場
                    else:
                        arrival_airport = "未找到抵達機場代碼"
                    
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

            except Exception as e:
                print(f"抓取航班 {index} 失敗: {e}")
                continue  # 繼續執行，忽略失敗

    driver.quit()
    return success_count

# 獲取今天的日期並加上 60 天
today = datetime.today()
target_date = today + timedelta(days=60)
target_date_str = target_date.strftime("%Y-%m-%d")

# 執行抓取函數
success_count = scrape_flights(target_date_str)

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