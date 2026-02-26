"""
智能体对话路由 - 报单信息提取
"""
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import json
from datetime import datetime

from core.database import get_conn
from core.logging import get_logger
from core.auth import get_current_user
from app.services.agent_service import OrderAgent
from app.services.order_service import OrderService

logger = get_logger(__name__)

router = APIRouter(prefix="/chat", tags=["智能对话"])


# ========== Pydantic 模型 ==========

class ChatMessage(BaseModel):
    """聊天消息请求"""
    message: str = Field(..., description="用户消息")
    user_id: int = Field(..., description="用户ID")


class ChatResponse(BaseModel):
    """聊天响应"""
    reply: str = Field(..., description="助手回复")
    order_id: Optional[str] = Field(None, description="报单ID")
    is_completed: bool = Field(False, description="是否已完成报单")
    extracted_info: Optional[Dict[str, Any]] = Field(None, description="提取的信息")
    missing_fields: Optional[List[str]] = Field(None, description="缺失的字段")


class OrderConfirmReq(BaseModel):
    """报单确认请求"""
    order_id: str = Field(..., description="报单ID")
    confirmed: bool = Field(..., description="是否确认")


# 存储活跃会话
active_sessions: Dict[int, Dict[str, Any]] = {}


@router.post("/message", response_model=ChatResponse)
def chat_message(
    body: ChatMessage,
    current_user: dict = Depends(get_current_user)
):
    """
    发送聊天消息，提取报单信息
    """
    # 确保用户ID匹配
    if body.user_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="用户ID不匹配")

    # 获取或创建会话
    session_key = current_user["id"]
    if session_key not in active_sessions:
        active_sessions[session_key] = {
            "agent": OrderAgent(),
            "current_order": None,
            "order_id": None
        }

    session = active_sessions[session_key]
    agent = session["agent"]

    # 处理消息
    result = agent.process_message(
        body.message,
        current_user["id"],
        session["current_order"]
    )

    # 更新会话状态
    if result.get("extracted_info"):
        session["current_order"] = result["extracted_info"]

    # 如果报单完成，保存到数据库
    if result.get("order_completed") and session["current_order"]:
        with get_conn() as conn:
            with conn.cursor() as cur:
                order_service = OrderService(cur)
                order_id = order_service.create_order(
                    user_id=current_user["id"],
                    order_data=session["current_order"]
                )
                session["order_id"] = order_id
                session["current_order"] = None

        logger.info(f"用户 {current_user['id']} 报单成功，订单号: {session['order_id']}")

    return ChatResponse(
        reply=result["reply"],
        order_id=session.get("order_id"),
        is_completed=result.get("order_completed", False),
        extracted_info=result.get("extracted_info"),
        missing_fields=result.get("missing_fields")
    )


@router.post("/orders/{order_id}/confirm")
def confirm_order(
    order_id: str,
    body: OrderConfirmReq,
    current_user: dict = Depends(get_current_user)
):
    """
    确认报单
    """
    if body.order_id != order_id:
        raise HTTPException(status_code=400, detail="订单ID不匹配")

    with get_conn() as conn:
        with conn.cursor() as cur:
            # 查询订单
            cur.execute(
                "SELECT id FROM orders WHERE order_id = %s AND user_id = %s",
                (order_id, current_user["id"])
            )
            order = cur.fetchone()

            if not order:
                raise HTTPException(status_code=404, detail="订单不存在")

            if body.confirmed:
                cur.execute(
                    "UPDATE orders SET is_completed = 1, updated_at = NOW() WHERE order_id = %s",
                    (order_id,)
                )
                conn.commit()
                return {"msg": "订单确认成功"}
            else:
                return {"msg": "订单确认已取消"}


@router.get("/orders/history")
def get_order_history(
    skip: int = 0,
    limit: int = 100,
    current_user: dict = Depends(get_current_user)
):
    """
    获取用户报单历史
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            order_service = OrderService(cur)
            orders = order_service.get_user_orders(
                user_id=current_user["id"],
                skip=skip,
                limit=limit
            )
            return {
                "total": len(orders),
                "skip": skip,
                "limit": limit,
                "orders": orders
            }


@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    """
    WebSocket 实时对话
    """
    await websocket.accept()

    try:
        # 创建会话
        agent = OrderAgent()
        current_order = None

        while True:
            # 接收消息
            data = await websocket.receive_text()
            message_data = json.loads(data)
            user_message = message_data.get("message", "")

            # 处理消息
            result = agent.process_message(user_message, user_id, current_order)

            # 更新当前订单
            if result.get("extracted_info"):
                current_order = result["extracted_info"]

            # 如果报单完成，保存到数据库
            if result.get("order_completed") and current_order:
                with get_conn() as conn:
                    with conn.cursor() as cur:
                        order_service = OrderService(cur)
                        order_id = order_service.create_order(
                            user_id=user_id,
                            order_data=current_order
                        )
                        result["order_id"] = order_id
                        current_order = None

            # 发送响应
            await websocket.send_json(result)

    except WebSocketDisconnect:
        logger.info(f"用户 {user_id} 断开连接")
    except Exception as e:
        logger.exception(f"WebSocket错误: {e}")
        await websocket.close()