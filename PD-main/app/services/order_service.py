"""
报单管理服务
"""
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime

from core.logging import get_logger
from core.table_access import _quote_identifier

logger = get_logger(__name__)


class OrderService:
    """报单服务"""

    def __init__(self, cursor):
        self.cursor = cursor

    def generate_order_id(self) -> str:
        """生成唯一报单ID"""
        date_str = datetime.now().strftime("%Y%m%d")
        unique_id = str(uuid.uuid4())[:8].upper()
        return f"BD{date_str}{unique_id}"

    def create_order(
        self,
        user_id: int,
        order_data: Dict[str, Any]
    ) -> str:
        """
        创建报单
        """
        order_id = self.generate_order_id()
        now = datetime.now()

        self.cursor.execute("""
            INSERT INTO orders (
                order_id, user_id, order_date, delivery_smelter,
                driver_name, driver_id_card, driver_phone, category,
                has_weighbill, license_plate, weighbill_status,
                is_completed, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            order_id,
            user_id,
            now,
            order_data.get("delivery_smelter"),
            order_data.get("driver_name"),
            order_data.get("driver_id_card"),
            order_data.get("driver_phone"),
            order_data.get("category"),
            order_data.get("has_weighbill"),
            order_data.get("license_plate"),
            order_data.get("weighbill_status", "待处理"),
            0,  # is_completed
            now,
            now
        ))

        logger.info(f"创建报单成功: {order_id}, 用户: {user_id}")
        return order_id

    def get_user_orders(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        获取用户报单列表
        """
        self.cursor.execute("""
            SELECT id, order_id, user_id, order_date, delivery_smelter,
                   driver_name, driver_id_card, driver_phone, category,
                   has_weighbill, license_plate, weighbill_status,
                   is_completed, created_at, updated_at
            FROM orders
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
        """, (user_id, limit, skip))

        rows = self.cursor.fetchall()
        for row in rows:
            for key in ["order_date", "created_at", "updated_at"]:
                if row.get(key):
                    row[key] = str(row[key])
        return rows

    def get_order_by_id(self, order_id: str) -> Optional[Dict[str, Any]]:
        """
        根据报单ID查询
        """
        self.cursor.execute("""
            SELECT id, order_id, user_id, order_date, delivery_smelter,
                   driver_name, driver_id_card, driver_phone, category,
                   has_weighbill, license_plate, weighbill_status,
                   is_completed, created_at, updated_at
            FROM orders
            WHERE order_id = %s
        """, (order_id,))

        row = self.cursor.fetchone()
        if row:
            for key in ["order_date", "created_at", "updated_at"]:
                if row.get(key):
                    row[key] = str(row[key])
        return row

    def get_order_by_pk(self, id: int) -> Optional[Dict[str, Any]]:
        """
        根据主键ID查询
        """
        self.cursor.execute("""
            SELECT id, order_id, user_id, order_date, delivery_smelter,
                   driver_name, driver_id_card, driver_phone, category,
                   has_weighbill, license_plate, weighbill_status,
                   is_completed, created_at, updated_at
            FROM orders
            WHERE id = %s
        """, (id,))

        row = self.cursor.fetchone()
        if row:
            for key in ["order_date", "created_at", "updated_at"]:
                if row.get(key):
                    row[key] = str(row[key])
        return row

    def update_order(
        self,
        id: int,
        update_data: Dict[str, Any]
    ) -> bool:
        """
        更新报单
        """
        allowed_fields = [
            "delivery_smelter", "driver_name", "driver_id_card",
            "driver_phone", "category", "has_weighbill",
            "license_plate", "weighbill_status", "is_completed"
        ]
        updates = {k: v for k, v in update_data.items() if k in allowed_fields}

        if not updates:
            return False

        set_clause = ", ".join([f"{k} = %s" for k in updates.keys()])
        updates["updated_at"] = datetime.now()
        params = list(updates.values()) + [id]

        self.cursor.execute(f"""
            UPDATE orders
            SET {set_clause}, updated_at = %s
            WHERE id = %s
        """, tuple(params))

        return self.cursor.rowcount > 0

    def search_orders(
        self,
        user_id: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        driver_name: Optional[str] = None,
        license_plate: Optional[str] = None,
        category: Optional[str] = None,
        weighbill_status: Optional[str] = None,
        is_completed: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        搜索报单
        """
        where_conditions = ["1=1"]
        params = []

        if user_id:
            where_conditions.append("user_id = %s")
            params.append(user_id)

        if start_date:
            where_conditions.append("order_date >= %s")
            params.append(start_date)

        if end_date:
            where_conditions.append("order_date <= %s")
            params.append(end_date)

        if driver_name:
            where_conditions.append("driver_name LIKE %s")
            params.append(f"%{driver_name}%")

        if license_plate:
            where_conditions.append("license_plate LIKE %s")
            params.append(f"%{license_plate}%")

        if category:
            where_conditions.append("category = %s")
            params.append(category)

        if weighbill_status:
            where_conditions.append("weighbill_status = %s")
            params.append(weighbill_status)

        if is_completed is not None:
            where_conditions.append("is_completed = %s")
            params.append(1 if is_completed else 0)

        where_clause = " AND ".join(where_conditions)

        self.cursor.execute(f"""
            SELECT id, order_id, user_id, order_date, delivery_smelter,
                   driver_name, driver_id_card, driver_phone, category,
                   has_weighbill, license_plate, weighbill_status,
                   is_completed, created_at, updated_at
            FROM orders
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
        """, tuple(params + [limit, skip]))

        rows = self.cursor.fetchall()
        for row in rows:
            for key in ["order_date", "created_at", "updated_at"]:
                if row.get(key):
                    row[key] = str(row[key])
        return rows

    def count_orders(self, user_id: Optional[int] = None) -> int:
        """
        统计报单数量
        """
        if user_id:
            self.cursor.execute(
                "SELECT COUNT(*) as total FROM orders WHERE user_id = %s",
                (user_id,)
            )
        else:
            self.cursor.execute("SELECT COUNT(*) as total FROM orders")

        result = self.cursor.fetchone()
        return result["total"] if result else 0

    def update_weighbill_status(self, order_id: int, status: str) -> bool:
        """
        更新磅单状态
        """
        self.cursor.execute("""
            UPDATE orders
            SET weighbill_status = %s, updated_at = NOW()
            WHERE id = %s
        """, (status, order_id))

        return self.cursor.rowcount > 0