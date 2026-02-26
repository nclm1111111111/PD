"""
业务常量配置
包含品类、联单状态等业务常量的定义
"""

# ========== 品类配置 ==========
CATEGORY_CONFIG = {
    "电动": {
        "display_name": "电动车",
        "aliases": ["电动", "电动车"],
        "description": "电动车品类",
        "sort_order": 1
    },
    "黑皮": {
        "display_name": "黑皮",
        "aliases": ["黑皮", "到水黑皮"],
        "description": "黑皮品类",
        "sort_order": 2
    },
    "新能源": {
        "display_name": "新能源",
        "aliases": ["新能源"],
        "description": "新能源品类",
        "sort_order": 3
    },
    "通信": {
        "display_name": "通信",
        "aliases": ["通信"],
        "description": "通信品类",
        "sort_order": 4
    },
    "摩托车": {
        "display_name": "摩托车",
        "aliases": ["摩托", "摩托车"],
        "description": "摩托车品类",
        "sort_order": 5
    },
    "大白": {
        "display_name": "大白",
        "aliases": ["大白"],
        "description": "大白品类",
        "sort_order": 6
    },
    "电子秤": {
        "display_name": "电子秤",
        "aliases": ["电子秤"],
        "description": "电子秤品类",
        "sort_order": 7
    },
    "黑木胶": {
        "display_name": "黑木胶",
        "aliases": ["黑木胶"],
        "description": "黑木胶品类",
        "sort_order": 8
    }
}

# ========== 联单状态配置 ==========
WEIGHBILL_STATUS_CONFIG = {
    "有联单已发": {
        "display_name": "有联单已发",
        "aliases": ["有联单", "有联单已发", "自带联单且已发"],
        "status": "已发",
        "needs_driver_send": False,
        "needs_company_upload": False,
        "sort_order": 1
    },
    "有联单未发": {
        "display_name": "有联单未发",
        "aliases": ["有联单未发"],
        "status": "待发",
        "needs_driver_send": True,
        "needs_company_upload": False,
        "sort_order": 2
    },
    "无联单": {
        "display_name": "无联单",
        "aliases": ["无联单"],
        "status": "无联单",
        "needs_driver_send": False,
        "needs_company_upload": True,
        "sort_order": 3
    }
}

# ========== 辅助函数 ==========

def get_category_display_name(category_key: str) -> str:
    """获取品类的显示名称"""
    config = CATEGORY_CONFIG.get(category_key)
    return config["display_name"] if config else category_key


def get_category_by_alias(alias: str) -> str:
    """通过别名获取品类标准名称"""
    for key, config in CATEGORY_CONFIG.items():
        if alias in config["aliases"]:
            return key
    return alias


def get_weighbill_status_by_alias(alias: str) -> str:
    """通过别名获取联单状态标准名称"""
    for key, config in WEIGHBILL_STATUS_CONFIG.items():
        if alias in config["aliases"]:
            return key
    return alias


def get_all_categories() -> list:
    """获取所有品类列表（按排序）"""
    categories = []
    for key, config in sorted(CATEGORY_CONFIG.items(), key=lambda x: x[1]["sort_order"]):
        categories.append({
            "code": key,
            "name": config["display_name"],
            "description": config["description"]
        })
    return categories


def get_all_weighbill_statuses() -> list:
    """获取所有联单状态列表（按排序）"""
    statuses = []
    for key, config in sorted(WEIGHBILL_STATUS_CONFIG.items(), key=lambda x: x[1]["sort_order"]):
        statuses.append({
            "code": key,
            "name": config["display_name"],
            "status": config["status"],
            "needs_driver_send": config["needs_driver_send"],
            "needs_company_upload": config["needs_company_upload"]
        })
    return statuses