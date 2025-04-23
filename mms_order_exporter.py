import os
import time
import logging
from datetime import datetime, timedelta
import json
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2 import service_account

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# 載入環境變數
load_dotenv()

class MMSOrderExporter:
    def __init__(self):
        self.base_url = "https://oneclub.backstage.oneclass.com.tw"
        self.login_url = f"{self.base_url}/login"
        self.username = os.getenv('MMS_USERNAME')
        self.password = os.getenv('MMS_PASSWORD')
        self.google_drive_folder_id = os.getenv('GOOGLE_DRIVE_FOLDER_ID')
        
        # 初始化 logger
        self.logger = logging.getLogger(__name__)
        
        if not all([self.username, self.password, self.google_drive_folder_id]):
            raise ValueError("請確保環境變數 MMS_USERNAME, MMS_PASSWORD 和 GOOGLE_DRIVE_FOLDER_ID 都已設定")

    def setup_driver(self):
        """設定 Chrome WebDriver"""
        options = Options()
        options.add_argument('--headless')  # 無頭模式
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        return driver

    def login_and_get_token(self, driver):
        """登入 MMS 系統並獲取授權 token"""
        try:
            # 訪問登入頁面
            driver.get(self.login_url)
            self.logger.info("開始登入 MMS 系統...")
            
            # 等待登入頁面載入（使用更短的等待時間）
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='text']"))
            )
            
            # 輸入帳號密碼
            username_input = driver.find_element(By.CSS_SELECTOR, "input[type='text']")
            password_input = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
            
            username_input.clear()
            username_input.send_keys(self.username)
            time.sleep(1)  # 縮短等待時間
            
            password_input.clear()
            password_input.send_keys(self.password)
            time.sleep(1)  # 縮短等待時間
            
            # 找到並點擊登入按鈕
            login_button = driver.find_element(By.CSS_SELECTOR, "button[type='button']")
            login_button.click()
            
            # 等待登入完成，使用更精確的條件
            try:
                WebDriverWait(driver, 10).until(
                    lambda driver: "login" not in driver.current_url
                )
            except Exception:
                self.logger.error("登入失敗：頁面未跳轉")
                driver.save_screenshot("login_failed.png")
                raise Exception("登入失敗：請檢查帳號密碼是否正確")
            
            current_url = driver.current_url
            self.logger.info(f"登入成功，當前頁面：{current_url}")
            
            # 等待頁面完全載入，使用更精確的條件
            WebDriverWait(driver, 10).until(
                lambda driver: driver.execute_script('return document.readyState') == 'complete'
            )
            
            # 嘗試從 localStorage 獲取 token
            token_data = driver.execute_script("return localStorage.getItem('token');")
            if token_data:
                try:
                    token_json = json.loads(token_data)
                    if 'jwt' in token_json:
                        self.logger.info("成功從 localStorage 獲取 JWT token")
                        return token_json['jwt']
                except json.JSONDecodeError:
                    pass
            
            # 嘗試從 sessionStorage 獲取 token
            token_data = driver.execute_script("return sessionStorage.getItem('token');")
            if token_data:
                try:
                    token_json = json.loads(token_data)
                    if 'jwt' in token_json:
                        self.logger.info("成功從 sessionStorage 獲取 JWT token")
                        return token_json['jwt']
                except json.JSONDecodeError:
                    pass
            
            # 嘗試從 cookie 獲取 token
            cookies = driver.get_cookies()
            for cookie in cookies:
                if 'token' in cookie['name'].lower():
                    token_data = cookie['value']
                    try:
                        token_json = json.loads(token_data)
                        if 'jwt' in token_json:
                            self.logger.info("成功從 cookie 獲取 JWT token")
                            return token_json['jwt']
                    except json.JSONDecodeError:
                        # 如果不是 JSON 格式，檢查是否為 JWT 格式
                        if token_data.count('.') == 2:  # JWT token 應該有三個部分，用兩個點分隔
                            self.logger.info("成功從 cookie 獲取有效的 JWT token")
                            return token_data
            
            # 如果還是無法獲取 token，嘗試從頁面元素中獲取
            self.logger.info("嘗試從頁面元素中獲取 token...")
            try:
                # 檢查頁面源碼中是否包含 token
                page_source = driver.page_source
                if 'token' in page_source:
                    # 使用正則表達式尋找 token
                    import re
                    token_match = re.search(r'token["\']:\s*["\']([^"\']+)["\']', page_source)
                    if token_match:
                        token_data = token_match.group(1)
                        try:
                            token_json = json.loads(token_data)
                            if 'jwt' in token_json:
                                self.logger.info("成功從頁面源碼中獲取 JWT token")
                                return token_json['jwt']
                        except json.JSONDecodeError:
                            # 如果不是 JSON 格式，檢查是否為 JWT 格式
                            if token_data.count('.') == 2:
                                self.logger.info("成功從頁面源碼中獲取有效的 JWT token")
                                return token_data
            except Exception as e:
                self.logger.warning(f"從頁面元素獲取 token 失敗: {str(e)}")
            
            # 如果所有方法都失敗，保存截圖並拋出異常
            driver.save_screenshot("token_error.png")
            raise Exception("無法獲取有效的授權 token，請檢查登入狀態")
            
        except Exception as e:
            self.logger.error(f"登入過程發生錯誤: {str(e)}")
            driver.save_screenshot("login_error.png")
            raise

    def get_orders(self, token):
        """使用 API 獲取訂單資料"""
        try:
            # 計算日期範圍（近七天）
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)
            
            # 轉換為毫秒時間戳
            start_timestamp = int(start_date.timestamp() * 1000)
            end_timestamp = int(end_date.timestamp() * 1000)
            
            # 設定請求參數
            params = {
                'skip': 0,
                'limit': 50,
                'startAt': start_timestamp,
                'endAt': end_timestamp,
                'dateType': 'pay'
            }
            
            headers = {
                'Authorization': f'Bearer {token}',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'zh-TW,zh;q=0.7',
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15',
                'Origin': 'https://oneclub.backstage.oneclass.com.tw',
                'Referer': 'https://oneclub.backstage.oneclass.com.tw/',
                'sec-fetch-dest': 'empty',
                'sec-fetch-mode': 'cors',
                'sec-fetch-site': 'cross-site',
                'sec-gpc': '1'
            }
            
            logging.info("開始獲取訂單資料...")
            response = requests.get(
                'https://api.oneclass.co/product/orders/exportExcel',
                params=params,
                headers=headers,
                verify=True
            )
            
            if response.status_code == 200:
                logging.info("成功獲取訂單資料")
                # 印出訂單資料的內容
                logging.info("訂單資料內容：")
                logging.info(response.text)
                return response.content
            else:
                logging.error(f"API 請求失敗: {response.status_code}")
                logging.error(f"錯誤訊息: {response.text}")
                raise Exception(f"API 請求失敗: {response.status_code}")
                
        except Exception as e:
            logging.error(f"獲取訂單資料時發生錯誤: {str(e)}")
            raise

    def upload_to_google_drive(self, file_path):
        """上傳檔案到 Google Drive"""
        try:
            # 使用服務帳戶認證
            SCOPES = ['https://www.googleapis.com/auth/drive.file']
            
            # 檢查服務帳戶金鑰檔案
            if not os.path.exists('service-account.json'):
                raise Exception("找不到服務帳戶金鑰檔案 (service-account.json)")
            
            try:
                # 使用服務帳戶建立憑證
                creds = service_account.Credentials.from_service_account_file(
                    'service-account.json',
                    scopes=SCOPES
                )
            except Exception as e:
                self.logger.error(f"建立服務帳戶憑證時發生錯誤: {str(e)}")
                raise
            
            # 建立 Drive API 服務
            try:
                service = build('drive', 'v3', credentials=creds)
            except Exception as e:
                self.logger.error(f"建立 Drive API 服務時發生錯誤: {str(e)}")
                raise
            
            # 準備檔案上傳
            file_metadata = {
                'name': os.path.basename(file_path),
                'parents': [self.google_drive_folder_id]
            }
            
            media = MediaFileUpload(
                file_path,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                resumable=True
            )
            
            # 上傳檔案
            self.logger.info("開始上傳檔案到 Google Drive...")
            try:
                file = service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id'
                ).execute()
                
                self.logger.info(f"檔案已成功上傳到 Google Drive，檔案 ID: {file.get('id')}")
                return file.get('id')
            except Exception as e:
                self.logger.error(f"上傳檔案時發生錯誤: {str(e)}")
                raise
            
        except Exception as e:
            self.logger.error(f"上傳到 Google Drive 時發生錯誤: {str(e)}")
            raise

    def run(self):
        """執行完整的匯出流程"""
        driver = None
        try:
            # 設定 WebDriver
            driver = self.setup_driver()
            
            # 登入並獲取 token
            token = self.login_and_get_token(driver)
            
            # 計算日期範圍（近七天）
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)
            
            # 使用新的 get_orders_from_api 函數獲取訂單資料
            order_data = self.get_orders_from_api(start_date, end_date)
            
            # 儲存訂單資料為 Excel 檔案
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'orders_{timestamp}.xlsx'
            
            with open(filename, 'wb') as f:
                f.write(order_data)
            
            # 上傳到 Google Drive
            self.upload_to_google_drive(filename)
            
            # 清理暫存檔案
            os.remove(filename)
            
            logging.info("訂單匯出流程完成")
            
        except Exception as e:
            logging.error(f"執行過程發生錯誤: {str(e)}")
            raise
        finally:
            if driver:
                driver.quit()

    def get_orders_from_api(self, start_date, end_date):
        """從 API 獲取訂單資料"""
        driver = None
        try:
            # 設定 WebDriver
            driver = self.setup_driver()
            
            # 登入並獲取 token
            token = self.login_and_get_token(driver)
            self.logger.info(f"獲取到的 token: {token[:20]}...")  # 只顯示 token 的前 20 個字元
            
            # 準備請求參數
            params = {
                'skip': 0,
                'limit': 50,
                'startAt': int(start_date.timestamp() * 1000),
                'endAt': int(end_date.timestamp() * 1000),
                'dateType': 'pay'  # 改為 'pay' 而不是 'createTime'
            }
            self.logger.info(f"請求參數: {params}")
            
            # 設定請求標頭
            headers = {
                'Authorization': f'Bearer {token}',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'zh-TW,zh;q=0.7',
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15',
                'Origin': 'https://oneclub.backstage.oneclass.com.tw',
                'Referer': 'https://oneclub.backstage.oneclass.com.tw/',
                'sec-fetch-dest': 'empty',
                'sec-fetch-mode': 'cors',
                'sec-fetch-site': 'cross-site',
                'sec-gpc': '1'
            }
            self.logger.info(f"請求標頭: {headers}")
            
            # 發送請求
            session = requests.Session()
            
            # 記錄完整的請求 URL
            request_url = 'https://api.oneclass.co/product/orders/exportExcel'
            self.logger.info(f"請求 URL: {request_url}")
            
            response = session.get(
                request_url,
                params=params,
                headers=headers,
                verify=True
            )
            
            # 記錄回應標頭
            self.logger.info(f"回應標頭: {dict(response.headers)}")
            
            # 檢查回應
            if response.status_code == 401 or (response.status_code == 200 and 'Token not valid' in response.text):
                self.logger.warning("Token 已過期或無效，嘗試重新登入...")
                # 重新登入並獲取新的 token
                driver.quit()
                driver = self.setup_driver()
                token = self.login_and_get_token(driver)
                self.logger.info(f"重新獲取到的 token: {token[:20]}...")  # 只顯示 token 的前 20 個字元
                headers['Authorization'] = f'Bearer {token}'
                
                response = session.get(
                    request_url,
                    params=params,
                    headers=headers,
                    verify=True
                )
            
            # 檢查回應狀態
            if response.status_code != 200:
                self.logger.error(f"API 請求失敗: {response.status_code}")
                self.logger.error(f"回應內容: {response.text}")
                raise Exception(f"API 請求失敗: {response.status_code}")
            
            # 檢查回應內容
            try:
                response_data = response.json()
                if response_data.get('status') == 'failure':
                    error_msg = response_data.get('error', {}).get('message', '未知錯誤')
                    self.logger.error(f"API 回應錯誤: {error_msg}")
                    raise Exception(f"API 回應錯誤: {error_msg}")
            except ValueError:
                # 如果不是 JSON 格式，可能是檔案下載
                if 'application/CSV' in response.headers.get('Content-Type', ''):
                    return response.content
                else:
                    self.logger.error(f"無法解析 API 回應: {response.text[:200]}")
                    raise Exception("無法解析 API 回應")
            
            return response.content
            
        except Exception as e:
            self.logger.error(f"獲取訂單資料時發生錯誤: {str(e)}")
            raise
        finally:
            if driver:
                driver.quit()

if __name__ == '__main__':
    exporter = MMSOrderExporter()
    exporter.run() 