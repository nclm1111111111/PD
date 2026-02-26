"""
订单模型 - pymysql 版本
提供 orders 表的 CRUD 操作封装
"""
import uuid
from typing import Optional, Dict, Any, List
from datetime import datetime

from core.database import get_conn
from core.logging import get_logger

logger = get_logger(__name__)


class OrderModel:
    """订单模型 - 对应 orders 表"""

    TABLE_NAME = "orders"

    # 表结构定义（供参考）
    SCHEMA = {
        "id": "INT PRIMARY KEY AUTO_INCREMENT",
        "order_id": "VARCHAR(50) NOT NULL UNIQUE",
        "user_id": "INT NOT NULL",
        "order_date": "DATETIME NOT NULL",
        "delivery_smelter": "VARCHAR(100)",
        "driver_name": "VARCHAR(50)",
        "driver_id_card": "VARCHAR(30)",
        "driver_phone": "VARCHAR(20)",
        "category": "VARCHAR(50)",
        "has_weighbill": "VARCHAR(20)",
        "license_plate": "VARCHAR(20)",
        "weighbill_status": "VARCHAR(20) DEFAULT '待处理'",
        "is_completed": "TINYINT(1) DEFAULT 0",
        "chat_history": "TEXT",
        "created_at": "DATETIME NOT NULL",
        "updated_at": "DATETIME"
    }

    # 常用字段列表
    BASE_FIELDS = [
        "id", "order_id", "user_id", "order_date", "delivery_smelter",
        "driver_name", "driver_id_card", "driver_phone", "category",
        "has_weighbill", "license_plate", "weighbill_status", "is_completed",
        "created_at", "updated_at"
    ]

    @staticmethod
    def generate_order_id() -> str:
        """生成唯一报单ID"""
        date_str = datetime.now().strftime("%Y%m%d")
        unique_id = str(uuid.uuid4())[:8].upper()
        return f"BD{date_str}{unique_id}"

    @classmethod
    def get_by_id(cls, order_id: str) -> Optional[Dict[str, Any]]:
        """根据报单ID查询"""
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(f"""
                    SELECT {', '.join(cls.BASE_FIELDS)}
                    FROM {cls.TABLE_NAME}
                    WHERE order_id = %s
                """, (order_id,))
                row = cur.fetchone()
                if row:
                    # 转换时间字段为字符串
                    for key in ["order_date", "created_at", "updated_at"]:
                        if row.get(key):
                            row[key] = str(row[key])
                return row

    @classmethod
    def get_by_pk(cls, id: int) -> Optional[Dict[str, Any]]:
        """根据主键ID查询"""
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(f"""
                    SELECT {', '.join(cls.BASE_FIELDS)}
                    FROM {cls.TABLE_NAME}
                    WHERE id = %s
                """, (id,))
                row = cur.fetchone()
                if row:
                    for key in ["order_date", "created_at", "updated_at"]:
                        if row.get(key):
                            row[key] = str(row[key])
                return row

    @classmethod
    def create(cls, user_id: int, order_data: Dict[str, Any]) -> str:
        """创建订单"""
        order_id = cls.generate_order_id()
        now = datetime.now()

        fields = [
            "order_id", "user_id", "order_date", "delivery_smelter",
            "driver_name", "driver_id_card", "driver_phone", "category",
            "has_weighbill", "license_plate", "weighbill_status",
            "is_completed", "created_at", "updated_at"
        ]

        values = [
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
        ]

        placeholders = ", ".join(["%s"] * len(fields))
        fields_str = ", ".join(fields)

        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(f"""
                    INSERT INTO {cls.TABLE_NAME} ({fields_str})
                    VALUES ({placeholders})
                """, tuple(values))
                conn.commit()

                logger.info(f"创建报单成功: {order_id}, 用户: {user_id}")
                return order_id

    @classmethod
    def update(cls, id: int, update_data: Dict[str, Any]) -> bool:
        """更新订单"""
        allowed_fields = [
            "delivery_smelter", "driver_name", "driver_id_card",
            "driver_phone", "category", "has_weighbill",
            "license_plate", "weighbill_status", "is_completed"
        ]

        set_parts = []
        values = []

        for key, value in update_data.items():
            if key in allowed_fields and value is not None:
                set_parts.append(f"{key} = %s")
                values.append(value)

        if not set_parts:
            return False

        set_parts.append("updated_at = NOW()")
        values.append(id)
        set_clause = ", ".join(set_parts)

        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(f"""
                    UPDATE {cls.TABLE_NAME}
                    SET {set_clause}
                    WHERE id = %s
                """, tuple(values))
                conn.commit()
                return cur.rowcount > 0

    @classmethod
    def get_user_orders(
            cls,
            user_id: int,
            skip: int = 0,
            limit: int = 100
    ) -> List[Dict[str, Any]]:
        """获取用户订单列表"""
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(f"""
                    SELECT {', '.join(cls.BASE_FIELDS)}
                    FROM {cls.TABLE_NAME}
                    WHERE user_id = %s
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                """, (user_id, limit, skip))

                rows = cur.fetchall()
                for row in rows:
                    for key in ["order_date", "created_at", "updated_at"]:
                        if row.get(key):
                            row[key] = str(row[key])
                return rows

    @classmethod
    def search(
            cls,
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
        """搜索订单"""
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

        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(f"""
                    SELECT {', '.join(cls.BASE_FIELDS)}
                    FROM {cls.TABLE_NAME}
                    WHERE {where_clause}
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                """, tuple(params + [limit, skip]))

                rows = cur.fetchall()
                for row in rows:
                    for key in ["order_date", "created_at", "updated_at"]:
                        if row.get(key):
                            row[key] = str(row[key])
                return rows

    @classmethod
    def count(cls, user_id: Optional[int] = None) -> int:
        """统计订单数量"""
        if user_id:
            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        f"SELECT COUNT(*) as total FROM {cls.TABLE_NAME} WHERE user_id = %s",
                        (user_id,)
                    )
                    result = cur.fetchone()
                    return result["total"] if result else 0
        else:
            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(f"SELECT COUNT(*) as total FROM {cls.TABLE_NAME}")
                    result = cur.fetchone()
                    return result["total"] if result else 0

    @classmethod
    def update_weighbill_status(cls, order_id: int, status: str) -> bool:
        """更新磅单状态"""
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(f"""
                    UPDATE {cls.TABLE_NAME}
                    SET weighbill_status = %s, updated_at = NOW()
                    WHERE id = %s
                """, (status, order_id))
                conn.commit()
                return cur.rowcount > 0