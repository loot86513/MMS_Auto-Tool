#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import logging
import requests
from datetime import datetime
from typing import List, Dict

class SlackNotifier:
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
        self.logger = logging.getLogger(__name__)

    def _get_urgency_color(self, days_until_expiry: int) -> str:
        """根據到期天數決定訊息顏色"""
        if days_until_expiry <= 7:
            return "#FF0000"  # 紅色 - 緊急
        elif days_until_expiry <= 30:
            return "#FFA500"  # 橘色 - 警告
        else:
            return "#FFFF00"  # 黃色 - 提醒

    def _format_institution_block(self, institution: Dict) -> Dict:
        """格式化單個機構的訊息區塊"""
        days = institution['days_until_expiry']
        urgency_color = self._get_urgency_color(days)
        
        # 準備聯絡資訊
        contact_info = []
        if institution.get('contact_person') and institution['contact_person'] != 'N/A':
            contact_info.append(f"聯絡人：{institution['contact_person']}")
        if institution.get('contact_number') and institution['contact_number'] != 'N/A':
            contact_info.append(f"電話：{institution['contact_number']}")
        if institution.get('address') and institution['address'] != 'N/A':
            contact_info.append(f"地址：{institution['address']}")
        
        # 如果沒有任何聯絡資訊，添加提示
        if not contact_info:
            contact_info.append("⚠️ 無聯絡資訊")
        
        # 構建訊息文字
        message_text = (
            f"*{institution['name']}*\n"
            f"• 方案：{institution.get('plan_name', 'N/A')}\n"
            f"• 到期日期：{institution.get('expiry_date', 'N/A')}\n"
            f"• 剩餘天數：{days} 天\n"
            f"• " + "\n• ".join(contact_info)
        )
        
        return {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": message_text
            },
            "accessory": {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "查看詳情",
                    "emoji": True
                },
                "url": f"https://oneclub.backstage.oneclass.com.tw/organization/{institution.get('uid', '')}",
                "style": "primary"
            }
        }

    def send_expiring_notification(self, institutions: List[Dict]) -> bool:
        """發送到期通知到 Slack"""
        try:
            if not institutions:
                self.logger.warning("沒有需要通知的機構")
                return True

            # 將機構按照剩餘天數分類
            urgent = []    # 7天內
            warning = []   # 8-30天
            notice = []    # 31-60天
            
            for inst in institutions:
                days = inst['days_until_expiry']
                if days <= 7:
                    urgent.append(inst)
                elif days <= 30:
                    warning.append(inst)
                else:
                    notice.append(inst)

            # 構建訊息標題
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "🔔 機構帳號到期通知",
                        "emoji": True
                    }
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"更新時間：{current_time}"
                        }
                    ]
                },
                {"type": "divider"}
            ]

            # 添加摘要資訊
            summary_text = (
                f"*本次通知摘要*\n"
                f"• 緊急（7天內）：{len(urgent)} 個機構\n"
                f"• 警告（8-30天）：{len(warning)} 個機構\n"
                f"• 提醒（31-60天）：{len(notice)} 個機構\n"
                f"• 總計：{len(institutions)} 個機構"
            )
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": summary_text
                }
            })
            blocks.append({"type": "divider"})

            # 添加各個等級的機構資訊
            if urgent:
                blocks.extend([
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "🚨 *緊急 - 7天內到期*"
                        }
                    }
                ])
                for inst in urgent:
                    blocks.append(self._format_institution_block(inst))
                blocks.append({"type": "divider"})

            if warning:
                blocks.extend([
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "⚠️ *警告 - 30天內到期*"
                        }
                    }
                ])
                for inst in warning:
                    blocks.append(self._format_institution_block(inst))
                blocks.append({"type": "divider"})

            if notice:
                blocks.extend([
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "📢 *提醒 - 60天內到期*"
                        }
                    }
                ])
                for inst in notice:
                    blocks.append(self._format_institution_block(inst))

            # 添加頁尾資訊
            blocks.append({
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "如有任何問題，請聯繫系統管理員"
                    }
                ]
            })

            # 發送訊息到 Slack
            response = requests.post(
                self.webhook_url,
                json={"blocks": blocks},
                headers={"Content-Type": "application/json"},
                timeout=10  # 添加超時設定
            )

            if response.status_code == 200:
                self.logger.info(f"成功發送 Slack 通知，包含 {len(institutions)} 個機構")
                return True
            else:
                self.logger.error(f"發送 Slack 通知失敗: HTTP {response.status_code} - {response.text}")
                return False

        except requests.exceptions.Timeout:
            self.logger.error("發送 Slack 通知超時")
            return False
        except requests.exceptions.RequestException as e:
            self.logger.error(f"發送 Slack 通知時發生網路錯誤: {str(e)}")
            return False
        except Exception as e:
            self.logger.error(f"發送 Slack 通知時發生未預期的錯誤: {str(e)}")
            return False 