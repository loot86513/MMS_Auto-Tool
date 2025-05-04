#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
from typing import Dict, Any
from dotenv import load_dotenv

class Config:
    def __init__(self, test_mode: bool = False, test_env: Dict[str, Any] = None):
        """初始化設定"""
        if not test_mode:
            # 載入環境變數
            load_dotenv()
        elif test_env:
            # 在測試模式下使用提供的測試環境變數
            os.environ.update(test_env)

        # MMS 系統設定
        self.mms_base_url = os.getenv('MMS_BASE_URL', 'https://api-new.oneclass.co/mms/proxy/link-plus')
        self.mms_api_version = os.getenv('MMS_API_VERSION', 'v1')
        self.mms_api_key = os.getenv('MMS_API_KEY')
        
        # Slack 設定
        self.slack_channel = os.getenv('SLACK_CHANNEL', '#mms-notifications')
        self.slack_webhook_url = os.getenv('SLACK_WEBHOOK_URL')
        self.slack_timeout = int(os.getenv('SLACK_TIMEOUT', '10'))  # 秒
        
        # 通知設定
        self.notification_days_threshold = int(os.getenv('NOTIFICATION_DAYS_THRESHOLD', '30'))
        self.notification_urgent_threshold = int(os.getenv('NOTIFICATION_URGENT_THRESHOLD', '7'))
        self.notification_warning_threshold = int(os.getenv('NOTIFICATION_WARNING_THRESHOLD', '30'))
        
        # API 請求設定
        self.api_timeout = int(os.getenv('API_TIMEOUT', '30'))  # 秒
        self.api_max_retries = int(os.getenv('API_MAX_RETRIES', '3'))
        self.api_retry_delay = int(os.getenv('API_RETRY_DELAY', '5'))  # 秒
        self.api_page_size = int(os.getenv('API_PAGE_SIZE', '50'))
        
        # 日誌設定
        self.log_level = os.getenv('LOG_LEVEL', 'INFO')
        self.log_file = os.getenv('LOG_FILE', 'mms_notify.log')
        self.log_max_size = int(os.getenv('LOG_MAX_SIZE', '10')) * 1024 * 1024  # MB to bytes
        self.log_backup_count = int(os.getenv('LOG_BACKUP_COUNT', '5'))
        
        # 機構到期時間閾值（天）
        self.expiry_threshold = int(os.getenv('EXPIRY_THRESHOLD', '60'))
        
        # 驗證必要的設定
        if not test_mode:
            self._validate_config()

    def _validate_config(self):
        """驗證必要的設定是否存在且有效"""
        # 驗證 URL 格式
        if not self._is_valid_url(self.mms_base_url):
            raise ValueError("MMS_BASE_URL 格式無效")
        
        # 驗證 API Key
        if not self.mms_api_key:
            raise ValueError("MMS_API_KEY 未設定")
        
        # 驗證 Slack Webhook URL
        if not self.slack_webhook_url:
            raise ValueError("SLACK_WEBHOOK_URL 未設定")
        if not self._is_valid_url(self.slack_webhook_url):
            raise ValueError("SLACK_WEBHOOK_URL 格式無效")
        
        # 驗證數值設定
        self._validate_positive_int('NOTIFICATION_DAYS_THRESHOLD', self.notification_days_threshold)
        self._validate_positive_int('NOTIFICATION_URGENT_THRESHOLD', self.notification_urgent_threshold)
        self._validate_positive_int('NOTIFICATION_WARNING_THRESHOLD', self.notification_warning_threshold)
        self._validate_positive_int('API_TIMEOUT', self.api_timeout)
        self._validate_positive_int('API_MAX_RETRIES', self.api_max_retries)
        self._validate_positive_int('API_RETRY_DELAY', self.api_retry_delay)
        self._validate_positive_int('API_PAGE_SIZE', self.api_page_size)
        self._validate_positive_int('LOG_MAX_SIZE', self.log_max_size)
        self._validate_positive_int('LOG_BACKUP_COUNT', self.log_backup_count)
        self._validate_positive_int('EXPIRY_THRESHOLD', self.expiry_threshold)
        
        # 驗證閾值邏輯
        if self.notification_urgent_threshold >= self.notification_warning_threshold:
            raise ValueError("緊急閾值必須小於警告閾值")
        if self.notification_warning_threshold >= self.expiry_threshold:
            raise ValueError("警告閾值必須小於到期閾值")

    def _is_valid_url(self, url: str) -> bool:
        """驗證 URL 格式"""
        if not url:
            return False
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        return bool(url_pattern.match(url))

    def _validate_positive_int(self, name: str, value: int):
        """驗證正整數值"""
        if not isinstance(value, int) or value <= 0:
            raise ValueError(f"{name} 必須是正整數")

    def validate(self) -> bool:
        """驗證所有必要的設定是否都存在且有效"""
        try:
            self._validate_config()
            return True
        except ValueError as e:
            raise ValueError(f"設定驗證失敗: {str(e)}")
        except Exception as e:
            raise Exception(f"設定驗證時發生未預期的錯誤: {str(e)}")

    def to_dict(self) -> Dict[str, Any]:
        """將設定轉換為字典格式"""
        return {
            'mms_base_url': self.mms_base_url,
            'mms_api_version': self.mms_api_version,
            'slack_channel': self.slack_channel,
            'notification_days_threshold': self.notification_days_threshold,
            'notification_urgent_threshold': self.notification_urgent_threshold,
            'notification_warning_threshold': self.notification_warning_threshold,
            'api_timeout': self.api_timeout,
            'api_max_retries': self.api_max_retries,
            'api_retry_delay': self.api_retry_delay,
            'api_page_size': self.api_page_size,
            'log_level': self.log_level,
            'log_file': self.log_file,
            'log_max_size': self.log_max_size,
            'log_backup_count': self.log_backup_count,
            'expiry_threshold': self.expiry_threshold
        } 