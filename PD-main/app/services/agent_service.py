"""
智能体对话服务 - 报单信息提取和处理
"""
import re
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime

from core.logging import get_logger

logger = get_logger(__name__)


class OrderAgent:
    """报单智能体 - 从对话中提取报单信息"""

    REQUIRED_FIELDS = [
        "driver_name",      # 司机姓名
        "driver_id_card",   # 身份证号
        "driver_phone",     # 电话
        "category",         # 品类
        "has_weighbill",    # 是否自带联单
        "license_plate",    # 车号
        "delivery_smelter"  # 送货冶炼厂
    ]

    FIELD_NAMES = {
        "driver_name": "司机姓名",
        "driver_id_card": "身份证号",
        "driver_phone": "司机电话",
        "category": "品类",
        "has_weighbill": "是否自带联单",
        "license_plate": "车号",
        "delivery_smelter": "送货冶炼厂"
    }

    CATEGORY_MAPPING = {
        "电动": "电动车",
        "电动车": "电动车",
        "黑皮": "黑皮",
        "新能源": "新能源",
        "通信": "通信",
        "摩托": "摩托车",
        "摩托车": "摩托车",
        "大白": "大白",
        "到水黑皮": "黑皮",
        "黑木胶": "黑木胶",
        "电子秤": "电子秤"
    }

    WEIGHBILL_MAPPING = {
        "有联单": "有联单已发",
        "有联单已发": "有联单已发",
        "有联单未发": "有联单未发",
        "无联单": "无联单",
        "自带联单且已发": "有联单已发"
    }

    def __init__(self):
        self.current_order = {}
        self.missing_fields = []
        self.conversation_history = []

    def parse_message(self, message: str) -> Dict[str, Any]:
        """
        解析用户消息，提取报单信息
        """
        extracted = {}

        # 提取车号（车牌）
        plate_match = re.search(r'[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼][A-Z][A-Z0-9]{5,6}', message)
        if plate_match:
            extracted["license_plate"] = plate_match.group()

        # 提取司机姓名
        name_patterns = [
            r'(?:司机|姓名)[:：]\s*([\u4e00-\u9fa5]{2,4})',
            r'([\u4e00-\u9fa5]{2,4})(?=\s*(?:司机|电话|身份证|证号))'
        ]
        for pattern in name_patterns:
            name_match = re.search(pattern, message)
            if name_match:
                extracted["driver_name"] = name_match.group(1)
                break

        # 如果没找到，尝试找单独的中文名
        if "driver_name" not in extracted:
            names = re.findall(r'[\u4e00-\u9fa5]{2,4}', message)
            if names and len(names[0]) >= 2:
                extracted["driver_name"] = names[0]

        # 提取身份证号
        id_match = re.search(r'\d{17}[\dXx]|\d{15}', message)
        if id_match:
            extracted["driver_id_card"] = id_match.group()

        # 提取电话
        phone_match = re.search(r'1[3-9]\d{9}', message)
        if phone_match:
            extracted["driver_phone"] = phone_match.group()

        # 提取品类
        for key, value in self.CATEGORY_MAPPING.items():
            if key in message:
                extracted["category"] = value
                break

        # 提取联单信息
        for key, value in self.WEIGHBILL_MAPPING.items():
            if key in message:
                extracted["has_weighbill"] = value
                break

        # 提取送货冶炼厂
        smelter_match = re.search(r'(?:送货|送|到)[:：]?\s*([\u4e00-\u9fa5]{2,10})', message)
        if smelter_match:
            extracted["delivery_smelter"] = smelter_match.group(1)

        return extracted

    def check_completeness(self, order_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        检查报单信息是否完整
        """
        missing = []
        for field in self.REQUIRED_FIELDS:
            if field not in order_data or not order_data.get(field):
                missing.append(field)
        return len(missing) == 0, missing

    def generate_missing_message(self, missing_fields: List[str]) -> str:
        """
        生成缺失字段提示信息
        """
        if not missing_fields:
            return ""

        field_names = [self.FIELD_NAMES.get(f, f) for f in missing_fields]

        if len(field_names) == 1:
            return f"请补充{field_names[0]}信息。"
        elif len(field_names) == 2:
            return f"请补充{'和'.join(field_names)}信息。"
        else:
            last = field_names.pop()
            return f"请补充{', '.join(field_names)}和{last}信息。"

    def format_order_table(self, order_data: Dict[str, Any]) -> str:
        """
        格式化报单信息为表格
        """
        today = datetime.now().strftime("%Y年%m月%d日")

        table = f"""
【报单信息确认】
-----------------------------
报单日期：{today}
送货冶炼厂：{order_data.get('delivery_smelter', '')}
车号：{order_data.get('license_plate', '')}
司机姓名：{order_data.get('driver_name', '')}
身份证号：{order_data.get('driver_id_card', '')}
司机电话：{order_data.get('driver_phone', '')}
品类：{order_data.get('category', '')}
是否自带联单：{order_data.get('has_weighbill', '')}
-----------------------------
请确认以上信息是否正确？(回复"确认"完成报单)
"""
        return table

    def process_message(
        self,
        message: str,
        user_id: int,
        existing_order: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        处理用户消息主入口
        """
        # 修改命令
        if message.strip() in ["修改", "重新填写", "重填"]:
            return {
                "reply": "请重新发送报单信息：",
                "order_completed": False,
                "clear_order": True
            }

        # 确认消息
        if message.strip() in ["确认", "确认报单", "正确", "是的"]:
            if existing_order and self.check_completeness(existing_order)[0]:
                return {
                    "reply": "报单成功！您的报单信息已保存。",
                    "order_completed": True,
                    "extracted_info": existing_order
                }
            else:
                return {
                    "reply": "报单信息不完整，请继续补充信息。",
                    "order_completed": False
                }

        # 解析新消息
        extracted = self.parse_message(message)

        # 合并现有信息
        if existing_order:
            current_data = {**existing_order, **extracted}
        else:
            current_data = extracted

        # 检查完整性
        is_complete, missing = self.check_completeness(current_data)

        if is_complete:
            # 信息完整，生成确认表格
            table = self.format_order_table(current_data)
            return {
                "reply": table,
                "order_completed": False,
                "extracted_info": current_data,
                "needs_confirmation": True
            }
        else:
            # 信息不完整，提醒缺失字段
            missing_msg = self.generate_missing_message(missing)
            return {
                "reply": f"收到您的信息。{missing_msg}",
                "order_completed": False,
                "extracted_info": current_data,
                "missing_fields": missing
            }

    def handle_unrelated_message(self) -> str:
        """
        处理无关消息
        """
        return """您好，我是报单智能助手。请发送报单信息，包含以下字段：
- 车号
- 司机姓名
- 身份证号
- 司机电话
- 品类（电动/黑皮/新能源/通信/摩托车/大白）
- 是否自带联单（有联单/有联单未发/无联单）
- 送货冶炼厂

例如：
车号：冀A013TJ
司机：黄立军
身份证号：132325197104084410
电话：13803364825
品类：电动
自带联单
送货：豫光"""