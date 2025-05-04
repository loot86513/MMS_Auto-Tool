#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from urllib.parse import quote

class MMSClient:
    def __init__(self, base_url: str, api_key: str, api_version: str = 'v1'):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.api_version = api_version
        self.logger = logging.getLogger(__name__)

    def _get_headers(self) -> Dict[str, str]:
        """取得 API 請求標頭"""
        return {
            'Authorization': self.api_key,
            'Content-Type': 'application/json',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-TW,zh;q=0.8',
            'Origin': 'https://oneclub.backstage.oneclass.com.tw',
            'Referer': 'https://oneclub.backstage.oneclass.com.tw/',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36'
        }

    def _make_request(self, endpoint: str, method: str = 'POST', data: Optional[Dict] = None) -> Dict:
        """發送 API 請求"""
        # 將斜線替換為 URL 編碼
        encoded_endpoint = quote(endpoint, safe='')
        url = f"{self.base_url}/{encoded_endpoint}"
        
        try:
            self.logger.debug(f"發送請求到 {url}")
            self.logger.debug(f"請求參數: {data}")
            
            response = requests.request(
                method=method,
                url=url,
                headers=self._get_headers(),
                json=data
            )
            
            self.logger.debug(f"回應狀態碼: {response.status_code}")
            self.logger.debug(f"回應內容: {response.text}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"API 請求失敗: {str(e)}")
            if hasattr(e.response, 'text'):
                self.logger.error(f"錯誤詳情: {e.response.text}")
            raise

    def get_institutions(self, page: int = 1, per_page: int = 10) -> List[Dict]:
        """取得機構列表"""
        try:
            data = {
                "pageNumber": page,
                "pageSize": per_page,
                "organizationStatuses": [1],  # 1 表示啟用的機構
                "expirationStatuses": [2],    # 2 表示即將到期的機構
                "searchKeyword": ""
            }
            
            response = self._make_request(
                endpoint='admin/organization/get/info/byPage',
                method='POST',
                data=data
            )
            
            # 檢查回應格式
            if response.get('status') == 'success':
                institutions = response.get('data', {}).get('data', {}).get('pageData', [])
                
                # 轉換日期格式
                for institution in institutions:
                    if 'expirationTime' in institution:
                        expiry_date = datetime.fromisoformat(institution['expirationTime'].replace('Z', '+00:00'))
                        institution['expiry_date'] = expiry_date.strftime('%Y-%m-%d')
                        
                        # 添加其他必要的欄位
                        institution['contact_person'] = f"{institution.get('ownerLastName', '')} {institution.get('ownerFirstName', '')}".strip() or 'N/A'
                        institution['contact_number'] = next((contact['number'] for contact in institution.get('contactNumbers', []) if contact.get('type') in [1, 2]), 'N/A')
                        institution['address'] = institution.get('address', 'N/A')
                        institution['plan_name'] = institution.get('purchasePlan', {}).get('name', 'N/A')
                
                return institutions
            else:
                error_msg = response.get('error', {}).get('message', '未知錯誤')
                self.logger.error(f"API 回應錯誤: {error_msg}")
                return []
            
        except Exception as e:
            self.logger.error(f"取得機構列表失敗: {str(e)}")
            raise

    def get_expiring_institutions(self, days_threshold: int = 60) -> List[Dict]:
        """取得即將到期的機構"""
        try:
            all_institutions = []
            page = 1
            per_page = 50  # 每頁取得更多資料以減少請求次數
            
            # 分頁取得所有機構
            while True:
                institutions = self.get_institutions(page=page, per_page=per_page)
                if not institutions:
                    break
                    
                all_institutions.extend(institutions)
                page += 1

            # 計算到期日期並篩選
            today = datetime.now().date()
            expiring_institutions = []
            
            for institution in all_institutions:
                try:
                    # 解析到期日期
                    expiry_date = datetime.strptime(
                        institution['expiry_date'],
                        '%Y-%m-%d'
                    ).date()
                    
                    # 計算剩餘天數
                    days_until_expiry = (expiry_date - today).days
                    
                    # 如果在閾值內，加入列表
                    if 0 < days_until_expiry <= days_threshold:
                        institution['days_until_expiry'] = days_until_expiry
                        expiring_institutions.append(institution)
                        
                except (ValueError, TypeError) as e:
                    self.logger.warning(f"處理機構 {institution.get('name', 'Unknown')} 的到期日期時發生錯誤: {str(e)}")
                    continue

            # 依照剩餘天數排序
            expiring_institutions.sort(key=lambda x: x['days_until_expiry'])
            
            self.logger.info(f"找到 {len(expiring_institutions)} 個即將到期的機構")
            return expiring_institutions
            
        except Exception as e:
            self.logger.error(f"取得即將到期機構時發生錯誤: {str(e)}")
            raise 