"""
字符串处理工具函数
"""
import random
import string
import re
from typing import Optional


def generate_random_str(length: int = 8, use_digits: bool = True, use_letters: bool = True) -> str:
    """
    生成随机字符串
    """
    chars = ""
    if use_letters:
        chars += string.ascii_letters
    if use_digits:
        chars += string.digits

    if not chars:
        chars = string.ascii_letters + string.digits

    return ''.join(random.choice(chars) for _ in range(length))


def mask_sensitive_info(text: Optional[str], visible_chars: int = 4, mask_char: str = '*') -> Optional[str]:
    """
    脱敏处理
    例如：138****5678
    """
    if not text or len(text) <= visible_chars:
        return text

    if len(text) <= visible_chars * 2:
        # 短字符串，只显示前visible_chars个字符
        return text[:visible_chars] + mask_char * (len(text) - visible_chars)
    else:
        # 显示前visible_chars和后visible_chars个字符
        return text[:visible_chars] + mask_char * (len(text) - visible_chars * 2) + text[-visible_chars:]


def truncate(text: Optional[str], max_length: int = 100, suffix: str = '...') -> Optional[str]:
    """
    截断字符串
    """
    if not text:
        return text

    if len(text) <= max_length:
        return text

    return text[:max_length - len(suffix)] + suffix


def camel_to_snake(name: str) -> str:
    """
    驼峰命名转蛇形命名
    userName -> user_name
    """
    pattern = re.compile(r'(?<!^)(?=[A-Z])')
    return pattern.sub('_', name).lower()


def snake_to_camel(name: str, upper_first: bool = False) -> str:
    """
    蛇形命名转驼峰命名
    user_name -> userName 或 UserName
    """
    components = name.split('_')
    if upper_first:
        return ''.join(x.title() for x in components)
    else:
        return components[0] + ''.join(x.title() for x in components[1:])


def remove_extra_spaces(text: Optional[str]) -> Optional[str]:
    """
    去除多余空格
    """
    if not text:
        return text

    return ' '.join(text.split())


def is_chinese_only(text: str) -> bool:
    """
    是否只包含中文
    """
    return bool(re.match(r'^[\u4e00-\u9fff]+$', text))


def is_alphanumeric(text: str) -> bool:
    """
    是否只包含字母和数字
    """
    return text.isalnum()


def extract_chinese(text: str) -> str:
    """
    提取文本中的中文字符
    """
    return ''.join(re.findall(r'[\u4e00-\u9fff]', text))


def extract_phone_numbers(text: str) -> list:
    """
    提取文本中的手机号
    """
    return re.findall(r'1[3-9]\d{9}', text)


def to_unicode_escape(text: str) -> str:
    """
    转换为Unicode转义形式
    """
    return text.encode('unicode_escape').decode('ascii')


def from_unicode_escape(text: str) -> str:
    """
    从Unicode转义形式转换回来
    """
    return text.encode('ascii').decode('unicode_escape')


def slugify(text: str) -> str:
    """
    生成URL友好的slug
    """
    # 转换为小写
    text = text.lower()
    # 将非字母数字字符替换为连字符
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    # 去除首尾连字符
    text = text.strip('-')
    return text


def format_currency(amount: float, currency: str = '¥') -> str:
    """
    格式化金额
    """
    return f"{currency}{amount:,.2f}"


def format_percentage(value: float, decimals: int = 2) -> str:
    """
    格式化百分比
    """
    return f"{value * 100:.{decimals}f}%"