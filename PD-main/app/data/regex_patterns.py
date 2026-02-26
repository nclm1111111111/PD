"""
正则表达式模式配置
用于从文本中提取各种字段信息
"""
import re

# ========== 基础正则表达式 ==========

EXTRACTION_PATTERNS = {
    # 车牌号
    "license_plate": r'[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼][A-Z][A-Z0-9]{5,6}',

    # 司机姓名
    "driver_name": [
        r'(?:司机|姓名)[:：]\s*([\u4e00-\u9fa5]{2,4})',
        r'([\u4e00-\u9fa5]{2,4})(?=\s*(?:司机|电话|身份证|证号))'
    ],

    # 身份证号
    "driver_id_card": r'\d{17}[\dXx]|\d{15}',

    # 手机号
    "driver_phone": r'1[3-9]\d{9}',

    # 送货冶炼厂
    "delivery_smelter": r'(?:送货|送|到)[:：]?\s*([\u4e00-\u9fa5]{2,10})',

    # 品类
    "category": r'(电动|黑皮|新能源|通信|摩托|摩托车|大白|电子秤|黑木胶|到水黑皮)',

    # 联单状态
    "has_weighbill": r'(有联单[^未发]*|有联单未发|无联单|自带联单且已发)'
}


# ========== 编译后的正则表达式（供直接使用） ==========

class CompiledPatterns:
    """编译后的正则表达式类"""

    LICENSE_PLATE = re.compile(EXTRACTION_PATTERNS["license_plate"])
    DRIVER_ID_CARD = re.compile(EXTRACTION_PATTERNS["driver_id_card"])
    DRIVER_PHONE = re.compile(EXTRACTION_PATTERNS["driver_phone"])
    DELIVERY_SMELTER = re.compile(EXTRACTION_PATTERNS["delivery_smelter"])
    CATEGORY = re.compile(EXTRACTION_PATTERNS["category"])
    HAS_WEIGHBILL = re.compile(EXTRACTION_PATTERNS["has_weighbill"])

    # 姓名模式需要逐个处理
    DRIVER_NAME_PATTERNS = [re.compile(p) for p in EXTRACTION_PATTERNS["driver_name"]]


# ========== 额外常用正则表达式 ==========

# 日期格式
DATE_PATTERNS = {
    "ymd_chinese": r'(\d{4})年(\d{1,2})月(\d{1,2})日',
    "ymd_dash": r'(\d{4})-(\d{1,2})-(\d{1,2})',
    "ymd_slash": r'(\d{4})/(\d{1,2})/(\d{1,2})',
    "ymd_compact": r'(\d{4})(\d{2})(\d{2})'
}

# 重量格式
WEIGHT_PATTERNS = {
    "gross_weight": r'毛重[：:]\s*(\d+\.?\d*)',
    "tare_weight": r'皮重[：:]\s*(\d+\.?\d*)',
    "net_weight": r'净重[：:]\s*(\d+\.?\d*)'
}

# 合同相关
CONTRACT_PATTERNS = {
    "contract_no": r'(?:合同编号|合同号)[：:]\s*([A-Za-z0-9\-]+)',
    "ticket_no": r'(?:单据号|磅单号|票号)[：:]\s*(\d+)'
}

# 单位相关
UNIT_PATTERNS = {
    "delivery_unit": r'送货单位[：:]\s*(.+?)(?:\n|$)',
    "receive_unit": r'收货单位[：:]\s*(.+?)(?:\n|$)'
}


# ========== 辅助函数 ==========

def compile_all_patterns():
    """编译所有正则表达式"""
    compiled = {}
    for name, pattern in EXTRACTION_PATTERNS.items():
        if isinstance(pattern, list):
            compiled[name] = [re.compile(p) for p in pattern]
        else:
            compiled[name] = re.compile(pattern)
    return compiled


def match_using_patterns(text: str, patterns: dict) -> dict:
    """
    使用多个模式匹配文本
    返回匹配结果字典
    """
    results = {}
    for field, pattern in patterns.items():
        if isinstance(pattern, list):
            # 多个模式，取第一个匹配成功的
            for p in pattern:
                match = p.search(text)
                if match:
                    results[field] = match.group(1) if match.groups() else match.group()
                    break
        else:
            match = pattern.search(text)
            if match:
                results[field] = match.group(1) if match.groups() else match.group()

    return results


# 导出编译后的正则表达式实例
patterns = CompiledPatterns()