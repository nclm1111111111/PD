"""
模型定义包 - 提供数据库表结构和查询方法
"""
from .user import UserModel
from .order import OrderModel
from .weighbill import WeighbillModel

__all__ = ["UserModel", "OrderModel", "WeighbillModel"]