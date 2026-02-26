"""
冶炼厂数据管理
提供常见的冶炼厂列表和查询功能
"""
from typing import Optional, Dict, List, Any

# ========== 冶炼厂数据 ==========

SMELTERS = [
    {"name": "豫光", "code": "YG", "address": "河南济源", "full_name": "河南豫光金铅股份有限公司"},
    {"name": "金利", "code": "JL", "address": "河南济源", "full_name": "河南金利金铅集团有限公司"},
    {"name": "万洋", "code": "WY", "address": "河南济源", "full_name": "济源市万洋冶炼（集团）有限公司"},
    {"name": "岷山", "code": "MS", "address": "河南安阳", "full_name": "安阳市岷山有色金属有限责任公司"},
    {"name": "宏达", "code": "HD", "address": "河南焦作", "full_name": "焦作市宏达力车业有限公司"},
    {"name": "永兴", "code": "YX", "address": "湖南郴州", "full_name": "湖南永兴县富康金属有限公司"},
    {"name": "灵宝", "code": "LB", "address": "河南三门峡", "full_name": "灵宝黄金股份有限公司"},
    {"name": "中金", "code": "ZJ", "address": "河南三门峡", "full_name": "中国黄金集团中原冶炼厂"},
]


# ========== 查询函数 ==========

def get_smelter_by_name(name: str) -> Optional[Dict[str, Any]]:
    """
    根据名称或代码查询冶炼厂

    Args:
        name: 冶炼厂名称或代码

    Returns:
        冶炼厂信息字典，未找到返回None
    """
    if not name:
        return None

    name = name.strip()

    # 精确匹配
    for smelter in SMELTERS:
        if name == smelter["name"] or name == smelter["code"]:
            return smelter.copy()

    # 模糊匹配（包含关系）
    for smelter in SMELTERS:
        if name in smelter["name"] or name in smelter["full_name"]:
            return smelter.copy()
        if smelter["name"] in name or smelter["code"] in name:
            return smelter.copy()

    return None


def get_all_smelters() -> List[Dict[str, Any]]:
    """
    获取所有冶炼厂列表
    """
    return [smelter.copy() for smelter in SMELTERS]


def get_smelters_by_province(province: str) -> List[Dict[str, Any]]:
    """
    按省份获取冶炼厂
    """
    result = []
    for smelter in SMELTERS:
        if province in smelter["address"]:
            result.append(smelter.copy())
    return result


def search_smelters(keyword: str) -> List[Dict[str, Any]]:
    """
    搜索冶炼厂
    """
    if not keyword:
        return []

    keyword = keyword.lower()
    result = []

    for smelter in SMELTERS:
        if (keyword in smelter["name"].lower() or
                keyword in smelter["code"].lower() or
                keyword in smelter["full_name"].lower() or
                keyword in smelter["address"].lower()):
            result.append(smelter.copy())

    return result


def get_smelter_options() -> List[Dict[str, Any]]:
    """
    获取下拉选项格式的冶炼厂列表
    """
    return [
        {
            "label": f"{s['name']} ({s['code']})",
            "value": s["name"],
            "code": s["code"],
            "address": s["address"]
        }
        for s in SMELTERS
    ]


def get_smelter_names() -> List[str]:
    """
    获取所有冶炼厂名称列表
    """
    return [s["name"] for s in SMELTERS]


def get_smelter_codes() -> List[str]:
    """
    获取所有冶炼厂代码列表
    """
    return [s["code"] for s in SMELTERS]


# ========== 缓存版本（可选） ==========

class SmelterCache:
    """冶炼厂缓存（单例模式）"""

    _instance = None
    _cache = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._cache = SMELTERS.copy()
        return cls._instance

    def get_all(self):
        return self._cache.copy()

    def get_by_name(self, name):
        return get_smelter_by_name(name)

    def search(self, keyword):
        return search_smelters(keyword)


# 创建缓存实例（可选）
smelter_cache = SmelterCache()