"""
报单管理路由
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

from core.database import get_conn
from core.logging import get_logger
from core.auth import get_current_user
from app.services.order_service import OrderService

logger = get_logger(__name__)

router = APIRouter(prefix="/orders", tags=["报单管理"])


# ========== Pydantic 模型 ==========

class OrderBase(BaseModel):
    """报单基础信息"""
    driver_name: Optional[str] = Field(None, description="司机姓名")
    driver_id_card: Optional[str] = Field(None, description="身份证号")
    driver_phone: Optional[str] = Field(None, description="司机电话")
    category: Optional[str] = Field(None, description="品类")
    has_weighbill: Optional[str] = Field(None, description="是否自带联单")
    delivery_smelter: Optional[str] = Field(None, description="送货冶炼厂")
    license_plate: Optional[str] = Field(None, description="车牌号")


class OrderCreate(OrderBase):
    """创建报单请求"""
    pass


class OrderUpdate(BaseModel):
    """更新报单请求"""
    driver_name: Optional[str] = None
    driver_id_card: Optional[str] = None
    driver_phone: Optional[str] = None
    category: Optional[str] = None
    has_weighbill: Optional[str] = None
    delivery_smelter: Optional[str] = None
    license_plate: Optional[str] = None
    weighbill_status: Optional[str] = None
    is_completed: Optional[bool] = None


class OrderInDB(OrderBase):
    """报单响应"""
    id: int
    order_id: str
    user_id: int
    order_date: str
    weighbill_status: str
    is_completed: bool
    created_at: str
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class OrderListResp(BaseModel):
    """报单列表响应"""
    total: int
    page: int
    page_size: int
    pages: int
    items: List[Dict[str, Any]]


# ========== 路由 ==========

@router.post("/", response_model=Dict[str, Any])
def create_order(
    body: OrderCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    创建报单
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            order_service = OrderService(cur)
            order_id = order_service.create_order(
                user_id=current_user["id"],
                order_data=body.dict(exclude_none=True)
            )
            conn.commit()

            return {
                "success": True,
                "message": "报单创建成功",
                "order_id": order_id
            }


@router.get("/", response_model=OrderListResp)
def list_orders(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    current_user: dict = Depends(get_current_user)
):
    """
    获取当前用户的报单列表
    """
    skip = (page - 1) * page_size

    with get_conn() as conn:
        with conn.cursor() as cur:
            order_service = OrderService(cur)
            orders = order_service.get_user_orders(
                user_id=current_user["id"],
                skip=skip,
                limit=page_size
            )
            total = order_service.count_orders(user_id=current_user["id"])

            return OrderListResp(
                total=total,
                page=page,
                page_size=page_size,
                pages=(total + page_size - 1) // page_size,
                items=orders
            )


@router.get("/search", response_model=OrderListResp)
def search_orders(
    start_date: Optional[str] = Query(None, description="开始日期"),
    end_date: Optional[str] = Query(None, description="结束日期"),
    driver_name: Optional[str] = Query(None, description="司机姓名"),
    license_plate: Optional[str] = Query(None, description="车牌号"),
    category: Optional[str] = Query(None, description="品类"),
    weighbill_status: Optional[str] = Query(None, description="磅单状态"),
    is_completed: Optional[bool] = Query(None, description="是否完成"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    current_user: dict = Depends(get_current_user)
):
    """
    搜索报单
    """
    skip = (page - 1) * page_size

    with get_conn() as conn:
        with conn.cursor() as cur:
            order_service = OrderService(cur)
            orders = order_service.search_orders(
                user_id=current_user["id"],
                start_date=start_date,
                end_date=end_date,
                driver_name=driver_name,
                license_plate=license_plate,
                category=category,
                weighbill_status=weighbill_status,
                is_completed=is_completed,
                skip=skip,
                limit=page_size
            )
            total = order_service.count_orders(user_id=current_user["id"])

            return OrderListResp(
                total=total,
                page=page,
                page_size=page_size,
                pages=(total + page_size - 1) // page_size,
                items=orders
            )


@router.get("/{order_id}", response_model=OrderInDB)
def get_order(
    order_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    获取报单详情
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            order_service = OrderService(cur)
            order = order_service.get_order_by_id(order_id)

            if not order:
                raise HTTPException(status_code=404, detail="报单不存在")

            if order["user_id"] != current_user["id"]:
                raise HTTPException(status_code=403, detail="无权访问此报单")

            return OrderInDB(**order)


@router.put("/{order_id}")
def update_order(
    order_id: str,
    body: OrderUpdate,
    current_user: dict = Depends(get_current_user)
):
    """
    更新报单
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            # 先查询订单
            order_service = OrderService(cur)
            order = order_service.get_order_by_id(order_id)

            if not order:
                raise HTTPException(status_code=404, detail="报单不存在")

            if order["user_id"] != current_user["id"]:
                raise HTTPException(status_code=403, detail="无权修改此报单")

            # 更新订单
            success = order_service.update_order(
                order["id"],
                body.dict(exclude_none=True)
            )

            if success:
                conn.commit()
                return {"msg": "更新成功"}
            else:
                raise HTTPException(status_code=400, detail="更新失败")


@router.delete("/{order_id}")
def delete_order(
    order_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    删除报单
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            # 先查询订单
            order_service = OrderService(cur)
            order = order_service.get_order_by_id(order_id)

            if not order:
                raise HTTPException(status_code=404, detail="报单不存在")

            if order["user_id"] != current_user["id"]:
                raise HTTPException(status_code=403, detail="无权删除此报单")

            # 删除订单
            cur.execute("DELETE FROM orders WHERE id = %s", (order["id"],))
            conn.commit()

            return {"msg": "报单删除成功"}


@router.post("/{order_id}/confirm")
def confirm_order(
    order_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    确认报单完成
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            order_service = OrderService(cur)
            order = order_service.get_order_by_id(order_id)

            if not order:
                raise HTTPException(status_code=404, detail="报单不存在")

            if order["user_id"] != current_user["id"]:
                raise HTTPException(status_code=403, detail="无权操作此报单")

            success = order_service.update_order(
                order["id"],
                {"is_completed": True}
            )

            if success:
                conn.commit()
                return {"msg": "报单已确认"}
            else:
                raise HTTPException(status_code=400, detail="确认失败")