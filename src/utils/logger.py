#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import logging
import traceback
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Optional

class CustomFormatter(logging.Formatter):
    """自定義日誌格式化器"""
    
    def __init__(self):
        super().__init__()
        self.default_fmt = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        self.debug_fmt = '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
        self.error_fmt = '''%(asctime)s - %(name)s - %(levelname)s - %(message)s
錯誤位置: %(filename)s:%(lineno)d
錯誤詳情: %(error_details)s'''
        
        self.formatters = {
            logging.DEBUG: logging.Formatter(self.debug_fmt, datefmt='%Y-%m-%d %H:%M:%S'),
            logging.INFO: logging.Formatter(self.default_fmt, datefmt='%Y-%m-%d %H:%M:%S'),
            logging.WARNING: logging.Formatter(self.default_fmt, datefmt='%Y-%m-%d %H:%M:%S'),
            logging.ERROR: logging.Formatter(self.error_fmt, datefmt='%Y-%m-%d %H:%M:%S'),
            logging.CRITICAL: logging.Formatter(self.error_fmt, datefmt='%Y-%m-%d %H:%M:%S')
        }

    def format(self, record):
        # 為錯誤和關鍵錯誤添加詳細資訊
        if record.levelno in (logging.ERROR, logging.CRITICAL):
            if hasattr(record, 'exc_info') and record.exc_info:
                record.error_details = ''.join(traceback.format_exception(*record.exc_info))
            else:
                record.error_details = '無詳細錯誤資訊'
        
        formatter = self.formatters.get(record.levelno)
        return formatter.format(record)

def setup_logger(
    log_level: str = None,
    log_file: str = None,
    max_bytes: int = 10*1024*1024,  # 10MB
    backup_count: int = 5,
    module_name: str = None
) -> logging.Logger:
    """設定日誌記錄器
    
    Args:
        log_level: 日誌級別
        log_file: 日誌檔案路徑
        max_bytes: 單個日誌檔案最大大小
        backup_count: 保留的備份檔案數量
        module_name: 模組名稱
    
    Returns:
        logging.Logger: 設定好的日誌記錄器
    """
    try:
        # 獲取日誌級別
        log_level = log_level or os.getenv('LOG_LEVEL', 'DEBUG')
        log_file = log_file or os.getenv('LOG_FILE', 'mms_notify.log')
        
        # 創建日誌目錄
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        # 設定根日誌記錄器
        logger = logging.getLogger(module_name) if module_name else logging.getLogger()
        logger.setLevel(getattr(logging, log_level))
        
        # 清除現有的處理器
        logger.handlers = []
        
        # 添加控制台處理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(CustomFormatter())
        console_handler.setLevel(getattr(logging, log_level))
        logger.addHandler(console_handler)
        
        # 添加檔案處理器
        try:
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding='utf-8'
            )
            file_handler.setFormatter(CustomFormatter())
            file_handler.setLevel(getattr(logging, log_level))
            logger.addHandler(file_handler)
        except (IOError, PermissionError) as e:
            logger.error(f"無法創建日誌檔案 {log_file}: {str(e)}")
            logger.warning("將只使用控制台輸出")
        
        # 設定 asyncio 日誌
        logging.getLogger('asyncio').setLevel(logging.WARNING)
        
        # 記錄啟動資訊
        logger.info("=== 日誌系統啟動 ===")
        logger.info(f"日誌級別: {log_level}")
        logger.info(f"日誌檔案: {log_file}")
        logger.info(f"時間戳記: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return logger
        
    except Exception as e:
        # 如果設定過程中發生錯誤，確保至少有基本的日誌輸出
        basic_logger = logging.getLogger()
        basic_logger.setLevel(logging.DEBUG)
        
        # 添加基本的控制台處理器
        if not basic_logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            basic_logger.addHandler(handler)
        
        basic_logger.error(f"設定日誌系統時發生錯誤: {str(e)}")
        basic_logger.debug(traceback.format_exc())
        return basic_logger

def get_logger(module_name: str) -> logging.Logger:
    """獲取模組專用的日誌記錄器
    
    Args:
        module_name: 模組名稱
    
    Returns:
        logging.Logger: 模組專用的日誌記錄器
    """
    return logging.getLogger(module_name) 