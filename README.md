# MMS Account Notify

這是一個自動化工具，用於監控 MMS（Member Management System）系統中即將到期的機構帳號，並透過 Slack 通知相關業務人員進行續約處理。

## 功能特點

- 自動連接 MMS API 系統
- 智能篩選即將到期的機構（可設定閾值，預設 60 天）
- 完整的機構資訊獲取
  - 基本資料（名稱、UID）
  - 到期資訊（到期日期、剩餘天數）
  - 聯絡資訊（聯絡人、電話、地址）
  - 方案資訊（方案名稱、帳號限制）
- Slack 通知整合
  - 自動發送到期提醒
  - 格式化的訊息呈現
  - 分級警示（急迫性分類）
- 完整的日誌記錄
  - 詳細的執行過程記錄
  - 錯誤追蹤和診斷
  - 可配置的日誌級別

## 系統需求

- Python 3.9 或以上版本
- 必要的 Python 套件（requirements.txt）
- MMS API 存取權限和認證
- Slack Webhook 設定
- 網路連接（需要訪問 MMS API 和 Slack API）

## 安裝步驟

1. 克隆專案到本地：
```bash
git clone [專案 URL]
cd MMS_Auto
```

2. 安裝相依套件：
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# 或者在 Windows 上：
# .venv\Scripts\activate
pip install -r requirements.txt
```

3. 設定環境變數：
```bash
# 複製環境變數範本
cp .env.example .env

# 編輯 .env 檔案，填入您的實際設定值
# 可使用任何文字編輯器，例如：
nano .env  # 或 vim .env
```

### 環境變數設置說明

在 `.env` 檔案中，您需要設定以下重要參數：

#### 必要設定
- `MMS_API_KEY`: MMS 系統的 API 金鑰
- `SLACK_WEBHOOK_URL`: Slack 的 Webhook URL

#### 選擇性設定（已有預設值）
- `MMS_BASE_URL`: MMS API 的基礎 URL（預設：https://api-new.oneclass.co/mms/proxy/link-plus）
- `MMS_API_VERSION`: API 版本（預設：v1）
- `SLACK_CHANNEL`: Slack 通知頻道（預設：#mms-notifications）
- `NOTIFICATION_DAYS_THRESHOLD`: 通知天數閾值（預設：30天）
- `EXPIRY_THRESHOLD`: 到期警告閾值（預設：60天）

完整的設定選項請參考 `.env.example` 檔案。

## 使用方法

1. 執行測試確認系統正常：
```bash
python -m pytest tests/test_mms_client.py -v
```

2. 運行主程式：
```bash
python main.py
```

### 執行結果範例

成功執行後，您將看到類似以下的輸出：
```
2025-05-04 13:22:46 - root - INFO - === 日誌系統啟動 ===
2025-05-04 13:22:46 - root - INFO - 開始執行 MMS 到期通知程式
2025-05-04 13:22:49 - root - INFO - 找到 5 個即將到期的機構
2025-05-04 13:22:50 - root - INFO - 成功發送到期通知
2025-05-04 13:22:50 - root - INFO - 程式執行完成
```

同時，在您設定的 Slack 頻道中將收到格式化的通知訊息，包含：
- 機構名稱
- 到期日期
- 聯絡資訊
- 方案資訊
- 緊急程度標示

## 通知機制

系統會根據機構到期時間的緊急程度分類：
- 緊急（7天內到期）：🔴 紅色警示
- 警告（8-30天）：🟡 黃色警示
- 提醒（31-60天）：🟢 綠色提醒

## 開發者資訊

- 專案維護者：[維護者名稱]
- 版本：1.0.0
- 授權：MIT License

## 注意事項

- 請確保 API 認證資訊的安全性
  - `.env` 檔案包含敏感資訊，已被加入 `.gitignore`
  - 切勿將含有實際金鑰的 `.env` 檔案提交到版本控制系統
- 定期檢查 Slack Webhook 的有效性
- 建議設定自動化排程執行（如：每日檢查）
- 確保網路連接穩定，以便正常訪問 API

## 故障排除

如果遇到問題，請檢查：
1. 確認 `.env` 檔案存在且包含所有必要的設定
2. 確認 Python 虛擬環境已啟動
3. 確認所有相依套件都已正確安裝
4. 檢查日誌檔案中的錯誤訊息
5. 確認網路連接狀態
6. 驗證 API 金鑰和 Webhook URL 的有效性

## 常見問題

1. SSL 警告訊息
   - 如果看到 `NotOpenSSLWarning` 警告，這是因為 urllib3 v2 需要 OpenSSL 1.1.1+
   - 這個警告不影響程式功能，但建議更新 OpenSSL 版本

2. API 連接問題
   - 確認 API 金鑰正確性
   - 檢查網路連接
   - 確認 API 端點可訪問

3. Slack 通知問題
   - 驗證 Webhook URL 的有效性
   - 確認頻道名稱正確
   - 檢查 Slack 工作區的權限設定