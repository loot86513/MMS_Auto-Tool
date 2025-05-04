#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
from src.config.config import Config
from src.mms.mms_client import MMSClient
from src.notifications.slack_notifier import SlackNotifier
from src.utils.logger import setup_logger

def main():
    """主程式入口"""
    try:
        # 設定日誌
        logger = setup_logger()
        logger.info("開始執行 MMS 到期通知程式")
        
        # 載入設定
        config = Config()
        
        # 初始化 MMS 客戶端
        mms_client = MMSClient(
            base_url=config.mms_base_url,
            api_key=config.mms_api_key,
            api_version=config.mms_api_version
        )
        
        # 初始化 Slack 通知器
        slack_notifier = SlackNotifier(config.slack_webhook_url)
        
        # 取得即將到期的機構
        expiring_institutions = mms_client.get_expiring_institutions(
            days_threshold=config.expiry_threshold
        )
        
        if expiring_institutions:
            logger.info(f"找到 {len(expiring_institutions)} 個即將到期的機構")
            
            # 發送 Slack 通知
            if slack_notifier.send_expiring_notification(expiring_institutions):
                logger.info("成功發送到期通知")
            else:
                logger.error("發送到期通知失敗")
        else:
            logger.info("沒有即將到期的機構")
        
        logger.info("程式執行完成")
        
    except Exception as e:
        logger.error(f"程式執行過程中發生錯誤: {str(e)}")
        raise

if __name__ == "__main__":
    main() 