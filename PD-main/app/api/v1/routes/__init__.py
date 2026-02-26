"""
API路由聚合模块
将所有业务模块的路由集中注册
"""
from fastapi import APIRouter

# 导入原有业务模块路由
from . import balances
from . import contracts
from . import customers
from . import deliveries
from . import payment
from . import weighbills

# 导入新增模块路由
from . import chat      # 智能对话模块
from . import orders    # 报单管理模块

# 创建路由聚合器
router = APIRouter()

# 注册原有业务模块
router.include_router(balances.router, prefix="/balances", tags=["磅单结余管理"])
router.include_router(contracts.router, prefix="/contracts", tags=["合同管理"])
router.include_router(customers.router, prefix="/customers", tags=["客户管理"])
router.include_router(deliveries.router, prefix="/deliveries", tags=["销售台账/报货订单"])
router.include_router(payment.router, prefix="/payment", tags=["付款管理"])
router.include_router(weighbills.router, prefix="/weighbills", tags=["磅单管理"])

# 注册新增模块
router.include_router(chat.router, prefix="/chat", tags=["智能对话"])
router.include_router(orders.router, prefix="/orders", tags=["报单管理"])


# 导出所有模块的路由
__all__ = [
    "router",
    "balances",
    "contracts",
    "customers",
    "deliveries",
    "payment",
    "weighbills",
    "chat",
    "orders"
]