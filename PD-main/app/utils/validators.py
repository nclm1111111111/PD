"""
数据验证工具函数
用于各种字段的格式验证
"""
import re
from typing import Optional, Union, Tuple, List
from datetime import datetime


def validate_phone(phone: Optional[str]) -> Tuple[bool, Optional[str]]:
    """
    验证手机号格式
    返回: (是否通过, 错误信息)
    """
    if not phone:
        return True, None

    # 去除空格
    phone = phone.strip()

    # 中国大陆手机号：1开头的11位数字
    pattern = r'^1[3-9]\d{9}$'
    if re.match(pattern, phone):
        return True, None
    else:
        return False, "手机号格式错误，应为11位数字，以1开头"


def validate_email(email: Optional[str]) -> Tuple[bool, Optional[str]]:
    """
    验证邮箱格式
    返回: (是否通过, 错误信息)
    """
    if not email:
        return True, None

    email = email.strip()
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

    if re.match(pattern, email):
        return True, None
    else:
        return False, "邮箱格式错误"


def validate_account(account: Optional[str]) -> Tuple[bool, Optional[str]]:
    """
    验证账号格式（字母数字下划线，3-20位）
    返回: (是否通过, 错误信息)
    """
    if not account:
        return False, "账号不能为空"

    account = account.strip()
    pattern = r'^[a-zA-Z0-9_]{3,20}$'

    if re.match(pattern, account):
        return True, None
    else:
        return False, "账号必须是3-20位字母、数字或下划线"


def validate_id_card(id_card: Optional[str]) -> Tuple[bool, Optional[str]]:
    """
    验证身份证号（简单验证）
    返回: (是否通过, 错误信息)
    """
    if not id_card:
        return True, None

    id_card = id_card.strip().upper()

    # 18位身份证
    pattern_18 = r'^\d{17}[\dX]$'
    # 15位身份证（旧版）
    pattern_15 = r'^\d{15}$'

    if re.match(pattern_18, id_card) or re.match(pattern_15, id_card):
        return True, None
    else:
        return False, "身份证号格式错误"


def validate_license_plate(plate: Optional[str]) -> Tuple[bool, Optional[str]]:
    """
    验证车牌号格式
    返回: (是否通过, 错误信息)
    """
    if not plate:
        return True, None

    plate = plate.strip().upper()
    # 普通车牌：省份简称(1位) + 字母(1位) + 数字字母(5-6位)
    pattern = r'^[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼][A-Z][A-Z0-9]{5,6}$'

    if re.match(pattern, plate):
        return True, None
    else:
        return False, "车牌号格式错误"


def validate_password(password: str, min_length: int = 6) -> Tuple[bool, Optional[str]]:
    """
    验证密码强度
    返回: (是否通过, 错误信息)
    """
    if not password:
        return False, "密码不能为空"

    if len(password) < min_length:
        return False, f"密码长度不能少于{min_length}位"

    # 检查是否包含数字
    has_digit = any(c.isdigit() for c in password)
    # 检查是否包含字母
    has_letter = any(c.isalpha() for c in password)

    if not has_digit:
        return False, "密码必须包含至少一位数字"

    if not has_letter:
        return False, "密码必须包含至少一位字母"

    return True, None


def validate_weight(weight: Union[str, float, int]) -> Tuple[bool, Optional[float]]:
    """
    验证重量值
    返回: (是否有效, 转换后的浮点数)
    """
    try:
        if isinstance(weight, str):
            weight = weight.strip()
            if not weight:
                return False, None
            weight = float(weight)
        else:
            weight = float(weight)

        # 重量必须在0.001到1000吨之间
        if weight <= 0 or weight > 1000:
            return False, None

        return True, round(weight, 3)
    except (ValueError, TypeError):
        return False, None


def validate_date(date_str: Optional[str], formats: List[str] = None) -> Tuple[bool, Optional[str]]:
    """
    验证日期格式并标准化
    返回: (是否有效, 标准化后的日期字符串 YYYY-MM-DD)
    """
    if not date_str:
        return False, None

    if formats is None:
        formats = [
            "%Y-%m-%d",
            "%Y/%m/%d",
            "%Y年%m月%d日",
            "%Y%m%d"
        ]

    date_str = date_str.strip()

    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return True, dt.strftime("%Y-%m-%d")
        except ValueError:
            continue

    return False, None


def sanitize_input(text: Optional[str]) -> Optional[str]:
    """
    清理输入，防止XSS攻击
    """
    if not text:
        return text

    # 替换危险字符
    dangerous_chars = ['<', '>', '"', "'", '&', ';', '--', '/*', '*/']
    for char in dangerous_chars:
        text = text.replace(char, '')

    # 去除首尾空格
    text = text.strip()

    return text


def extract_numbers(text: str) -> List[str]:
    """
    提取文本中的所有数字
    """
    return re.findall(r'\d+\.?\d*', text)


def is_chinese(text: str) -> bool:
    """
    判断是否包含中文字符
    """
    return bool(re.search(r'[\u4e00-\u9fff]', text))


def validate_url(url: Optional[str]) -> Tuple[bool, Optional[str]]:
    """
    验证URL格式
    """
    if not url:
        return True, None

    url = url.strip()
    pattern = r'^https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[^\s]*$'

    if re.match(pattern, url):
        return True, None
    else:
        return False, "URL格式错误"


def validate_required(value: Optional[str], field_name: str) -> Tuple[bool, Optional[str]]:
    """
    验证必填字段
    """
    if value is None or (isinstance(value, str) and not value.strip()):
        return False, f"{field_name}不能为空"
    return True, None


def validate_length(value: str, min_len: int = 0, max_len: int = None, field_name: str = "字段") -> Tuple[
    bool, Optional[str]]:
    """
    验证字符串长度
    """
    if not value:
        return True, None

    length = len(value)

    if min_len > 0 and length < min_len:
        return False, f"{field_name}长度不能少于{min_len}位"

    if max_len and length > max_len:
        return False, f"{field_name}长度不能超过{max_len}位"

    return True, None