# MMS Order Exporter

這是一個自動化工具，用於從 MMS 系統匯出訂單資料並上傳到 Google Drive。

## 功能特點

- 自動登入 MMS 系統
- 獲取訂單資料
- 將訂單資料匯出為 Excel 檔案
- 自動上傳到指定的 Google Drive 資料夾

## 安裝需求

- Python 3.9 或更高版本
- Chrome 瀏覽器
- Google Drive API 存取權限

## 安裝步驟

1. 克隆專案：
```bash
git clone [repository-url]
cd mms-order-exporter
```

2. 安裝依賴套件：
```bash
pip install -r requirements.txt
```

3. 設定環境變數：
創建 `.env` 文件並設定以下變數：
```
MMS_USERNAME=your_username
MMS_PASSWORD=your_password
GOOGLE_DRIVE_FOLDER_ID=your_folder_id
```

4. 設定 Google Drive API：
- 在 Google Cloud Console 創建專案
- 啟用 Google Drive API
- 創建服務帳戶並下載金鑰檔案
- 將金鑰檔案重命名為 `service-account.json` 並放在專案根目錄

## 使用方法

執行以下命令：
```bash
python mms_order_exporter.py
```

## 注意事項

- 請確保您的網路連接穩定
- 請妥善保管您的認證資訊
- 建議定期備份重要資料

## 授權

本專案採用 MIT 授權條款。 