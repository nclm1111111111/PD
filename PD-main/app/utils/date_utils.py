"""
日期时间工具函数
"""
from datetime import datetime, timedelta, date
from typing import Optional, Union, Tuple, List
import time


def get_current_datetime(format: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    获取当前日期时间字符串
    """
    return datetime.now().strftime(format)


def get_current_date(format: str = "%Y-%m-%d") -> str:
    """
    获取当前日期字符串
    """
    return datetime.now().strftime(format)


def parse_date(
        date_str: str,
        formats: List[str] = None
) -> Optional[datetime]:
    """
    解析日期字符串
    """
    if formats is None:
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
            "%Y/%m/%d %H:%M:%S",
            "%Y/%m/%d",
            "%Y年%m月%d日 %H:%M:%S",
            "%Y年%m月%d日",
            "%Y%m%d%H%M%S",
            "%Y%m%d"
        ]

    date_str = date_str.strip()

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue

    return None


def format_date(
        dt: Union[datetime, str, None],
        format: str = "%Y-%m-%d %H:%M:%S"
) -> Optional[str]:
    """
    格式化日期时间
    """
    if dt is None:
        return None

    if isinstance(dt, str):
        dt = parse_date(dt)
        if dt is None:
            return None

    if isinstance(dt, datetime):
        return dt.strftime(format)

    return None


def to_timestamp(dt: Optional[Union[datetime, str]]) -> Optional[int]:
    """
    转换为时间戳
    """
    if dt is None:
        return None

    if isinstance(dt, str):
        dt = parse_date(dt)
        if dt is None:
            return None

    if isinstance(dt, datetime):
        return int(dt.timestamp())

    return None


def from_timestamp(timestamp: Optional[int]) -> Optional[datetime]:
    """
    从时间戳转换
    """
    if timestamp is None:
        return None

    try:
        return datetime.fromtimestamp(timestamp)
    except (ValueError, TypeError, OSError):
        return None


def get_date_range(
        start_date: Union[str, datetime, date],
        end_date: Union[str, datetime, date]
) -> Tuple[datetime, datetime]:
    """
    获取日期范围（开始日期的00:00:00 到 结束日期的23:59:59）
    """
    if isinstance(start_date, str):
        start = parse_date(start_date)
        if start is None:
            raise ValueError(f"无效的开始日期: {start_date}")
    elif isinstance(start_date, date) and not isinstance(start_date, datetime):
        start = datetime.combine(start_date, datetime.min.time())
    else:
        start = start_date

    if isinstance(end_date, str):
        end = parse_date(end_date)
        if end is None:
            raise ValueError(f"无效的结束日期: {end_date}")
    elif isinstance(end_date, date) and not isinstance(end_date, datetime):
        end = datetime.combine(end_date, datetime.max.time())
    else:
        end = end_date

    # 确保开始时间是一天的开始
    start = start.replace(hour=0, minute=0, second=0, microsecond=0)

    # 确保结束时间是一天的结束
    end = end.replace(hour=23, minute=59, second=59, microsecond=999999)

    return start, end


def add_days(dt: Union[datetime, str], days: int) -> Optional[datetime]:
    """
    添加天数
    """
    if isinstance(dt, str):
        dt = parse_date(dt)
        if dt is None:
            return None

    if isinstance(dt, datetime):
        return dt + timedelta(days=days)

    return None


def add_months(dt: Union[datetime, str], months: int) -> Optional[datetime]:
    """
    添加月份
    """
    if isinstance(dt, str):
        dt = parse_date(dt)
        if dt is None:
            return None

    if isinstance(dt, datetime):
        year = dt.year + (dt.month + months - 1) // 12
        month = (dt.month + months - 1) % 12 + 1
        day = min(dt.day,
                  [31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30,
                   31, 30, 31][month - 1])
        return dt.replace(year=year, month=month, day=day)

    return None


def time_ago(dt: Union[datetime, str]) -> str:
    """
    返回相对时间描述（例如：3分钟前）
    """
    if isinstance(dt, str):
        dt = parse_date(dt)
        if dt is None:
            return "未知"

    now = datetime.now()
    diff = now - dt

    if diff.days > 365:
        years = diff.days // 365
        return f"{years}年前"
    elif diff.days > 30:
        months = diff.days // 30
        return f"{months}个月前"
    elif diff.days > 0:
        return f"{diff.days}天前"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours}小时前"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes}分钟前"
    else:
        return "刚刚"


def is_same_day(dt1: Union[datetime, str], dt2: Union[datetime, str]) -> bool:
    """
    判断是否为同一天
    """
    if isinstance(dt1, str):
        dt1 = parse_date(dt1)
    if isinstance(dt2, str):
        dt2 = parse_date(dt2)

    if dt1 and dt2:
        return dt1.date() == dt2.date()

    return False


def get_week_range(dt: Union[datetime, str] = None) -> Tuple[datetime, datetime]:
    """
    获取所在周的范围（周一到周日）
    """
    if dt is None:
        dt = datetime.now()
    elif isinstance(dt, str):
        dt = parse_date(dt)
        if dt is None:
            dt = datetime.now()

    # 计算本周一
    monday = dt - timedelta(days=dt.weekday())
    monday = monday.replace(hour=0, minute=0, second=0, microsecond=0)

    # 计算本周日
    sunday = monday + timedelta(days=6)
    sunday = sunday.replace(hour=23, minute=59, second=59, microsecond=999999)

    return monday, sunday


def get_month_range(dt: Union[datetime, str] = None) -> Tuple[datetime, datetime]:
    """
    获取所在月的范围
    """
    if dt is None:
        dt = datetime.now()
    elif isinstance(dt, str):
        dt = parse_date(dt)
        if dt is None:
            dt = datetime.now()

    # 本月第一天
    first_day = dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # 下个月第一天减去1秒得到本月最后一天
    if dt.month == 12:
        last_day = dt.replace(year=dt.year + 1, month=1, day=1) - timedelta(seconds=1)
    else:
        last_day = dt.replace(month=dt.month + 1, day=1) - timedelta(seconds=1)

    last_day = last_day.replace(hour=23, minute=59, second=59, microsecond=999999)

    return first_day, last_day