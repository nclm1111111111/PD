"""
磅单模型 - pymysql 版本
提供 pd_weighbills 表的 CRUD 操作封装
"""
from typing import Optional, Dict, Any, List
from datetime import datetime

from core.database import get_conn
from core.logging import get_logger

logger = get_logger(__name__)


class WeighbillModel:
    """磅单模型 - 对应 pd_weighbills 表"""

    TABLE_NAME = "pd_weighbills"

    # 表结构定义（供参考）
    SCHEMA = {
        "id": "INT PRIMARY KEY AUTO_INCREMENT",
        "order_id": "INT",
        "delivery_id": "INT",
        "weigh_date": "VARCHAR(20)",
        "delivery_time": "VARCHAR(20)",
        "weigh_ticket_no": "VARCHAR(50)",
        "contract_no": "VARCHAR(50)",
        "vehicle_no": "VARCHAR(20) NOT NULL",
        "product_name": "VARCHAR(100)",
        "gross_weight": "DECIMAL(10,2)",
        "tare_weight": "DECIMAL(10,2)",
        "net_weight": "DECIMAL(10,2) NOT NULL",
        "unit_price": "DECIMAL(10,2)",
        "total_amount": "DECIMAL(10,2)",
        "warehouse": "VARCHAR(100)",
        "target_factory_name": "VARCHAR(100)",
        "driver_name": "VARCHAR(50)",
        "driver_phone": "VARCHAR(20)",
        "driver_id_card": "VARCHAR(30)",
        "weighbill_image": "VARCHAR(500)",
        "ocr_status": "VARCHAR(20) DEFAULT '待确认'",
        "ocr_raw_data": "TEXT",
        "is_manual_corrected": "TINYINT(1) DEFAULT 0",
        "uploader_id": "INT",
        "uploader_name": "VARCHAR(50) DEFAULT 'system'",
        "uploaded_at": "DATETIME",
        "created_at": "DATETIME NOT NULL",
        "updated_at": "DATETIME"
    }

    # 常用字段列表
    BASE_FIELDS = [
        "id", "order_id", "delivery_id", "weigh_date", "delivery_time",
        "weigh_ticket_no", "contract_no", "vehicle_no", "product_name",
        "gross_weight", "tare_weight", "net_weight", "unit_price", "total_amount",
        "warehouse", "target_factory_name", "driver_name", "driver_phone", "driver_id_card",
        "weighbill_image", "ocr_status", "is_manual_corrected", "uploader_name",
        "uploaded_at", "created_at", "updated_at"
    ]

    @classmethod
    def get_by_id(cls, bill_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取磅单"""
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(f"""
                    SELECT w.*, d.shipper, d.payee
                    FROM {cls.TABLE_NAME} w
                    LEFT JOIN pd_deliveries d ON w.delivery_id = d.id
                    WHERE w.id = %s
                """, (bill_id,))

                row = cur.fetchone()
                if row:
                    # 转换时间字段为字符串
                    for key in ["weigh_date", "delivery_time", "uploaded_at", "created_at", "updated_at"]:
                        if row.get(key):
                            row[key] = str(row[key])
                return row

    @classmethod
    def create(cls, data: Dict[str, Any], image_path: str = None) -> int:
        """创建磅单"""
        fields = [
            "weigh_date", "delivery_time", "weigh_ticket_no", "contract_no",
            "delivery_id", "vehicle_no", "product_name", "gross_weight",
            "tare_weight", "net_weight", "unit_price", "total_amount",
            "weighbill_image", "ocr_status", "ocr_raw_data", "is_manual_corrected",
            "uploader_id", "uploader_name", "uploaded_at", "created_at", "updated_at"
        ]

        values = [
            data.get("weigh_date"),
            data.get("delivery_time"),
            data.get("weigh_ticket_no"),
            data.get("contract_no"),
            data.get("delivery_id"),
            data.get("vehicle_no"),
            data.get("product_name"),
            data.get("gross_weight"),
            data.get("tare_weight"),
            data.get("net_weight"),
            data.get("unit_price"),
            data.get("total_amount"),
            image_path,
            data.get("ocr_status", "待确认"),
            data.get("raw_text"),
            1 if data.get("is_manual") else 0,
            data.get("uploader_id"),
            data.get("uploader_name", "system"),
            datetime.now() if data.get("uploaded_at") else None,
            datetime.now(),
            datetime.now()
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
                return cur.lastrowid

    @classmethod
    def update(cls, bill_id: int, update_data: Dict[str, Any]) -> bool:
        """更新磅单"""
        allowed_fields = [
            "weigh_date", "delivery_time", "weigh_ticket_no", "contract_no",
            "delivery_id", "vehicle_no", "product_name", "gross_weight",
            "tare_weight", "net_weight", "unit_price", "total_amount",
            "warehouse", "target_factory_name", "driver_name", "driver_phone",
            "driver_id_card", "ocr_status", "is_manual_corrected"
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
        values.append(bill_id)
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
    def update_status(cls, bill_id: int, status: str) -> bool:
        """更新OCR状态"""
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(f"""
                    UPDATE {cls.TABLE_NAME}
                    SET ocr_status = %s, updated_at = NOW()
                    WHERE id = %s
                """, (status, bill_id))
                conn.commit()
                return cur.rowcount > 0

    @classmethod
    def delete(cls, bill_id: int) -> bool:
        """删除磅单"""
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(f"DELETE FROM {cls.TABLE_NAME} WHERE id = %s", (bill_id,))
                conn.commit()
                return cur.rowcount > 0

    @classmethod
    def list_weighbills(
            cls,
            status: Optional[str] = None,
            vehicle_no: Optional[str] = None,
            contract_no: Optional[str] = None,
            keyword: Optional[str] = None,
            date_from: Optional[str] = None,
            date_to: Optional[str] = None,
            page: int = 1,
            page_size: int = 20
    ) -> Dict[str, Any]:
        """查询磅单列表"""
        where_conditions = ["1=1"]
        params = []

        if status:
            where_conditions.append("ocr_status = %s")
            params.append(status)

        if vehicle_no:
            where_conditions.append("vehicle_no = %s")
            params.append(vehicle_no)

        if contract_no:
            where_conditions.append("contract_no = %s")
            params.append(contract_no)

        if date_from:
            where_conditions.append("weigh_date >= %s")
            params.append(date_from)

        if date_to:
            where_conditions.append("weigh_date <= %s")
            params.append(date_to)

        if keyword:
            where_conditions.append(
                "(contract_no LIKE %s OR vehicle_no LIKE %s OR product_name LIKE %s OR weigh_ticket_no LIKE %s)"
            )
            like = f"%{keyword}%"
            params.extend([like, like, like, like])

        where_clause = " AND ".join(where_conditions)

        with get_conn() as conn:
            with conn.cursor() as cur:
                # 查询总数
                cur.execute(f"""
                    SELECT COUNT(*) as total
                    FROM {cls.TABLE_NAME}
                    WHERE {where_clause}
                """, tuple(params))
                total = cur.fetchone()["total"]

                # 查询列表
                offset = (page - 1) * page_size
                cur.execute(f"""
                    SELECT w.*, d.shipper, d.payee, d.warehouse, d.target_factory_name,
                           d.driver_name, d.driver_phone, d.driver_id_card
                    FROM {cls.TABLE_NAME} w
                    LEFT JOIN pd_deliveries d ON w.delivery_id = d.id
                    WHERE {where_clause}
                    ORDER BY w.created_at DESC
                    LIMIT %s OFFSET %s
                """, tuple(params + [page_size, offset]))

                rows = cur.fetchall()
                for row in rows:
                    for key in ["weigh_date", "delivery_time", "uploaded_at", "created_at", "updated_at"]:
                        if row.get(key):
                            row[key] = str(row[key])

                return {
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                    "pages": (total + page_size - 1) // page_size,
                    "items": rows
                }

    @classmethod
    def get_user_weighbills(
            cls,
            user_id: int,
            skip: int = 0,
            limit: int = 100
    ) -> List[Dict[str, Any]]:
        """获取用户的磅单列表"""
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(f"""
                    SELECT {', '.join(cls.BASE_FIELDS)}
                    FROM {cls.TABLE_NAME}
                    WHERE uploader_id = %s
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                """, (user_id, limit, skip))

                rows = cur.fetchall()
                for row in rows:
                    for key in ["weigh_date", "delivery_time", "uploaded_at", "created_at", "updated_at"]:
                        if row.get(key):
                            row[key] = str(row[key])
                return rows

    @classmethod
    def get_by_order_id(cls, order_id: int) -> List[Dict[str, Any]]:
        """获取订单的所有磅单"""
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(f"""
                    SELECT {', '.join(cls.BASE_FIELDS)}
                    FROM {cls.TABLE_NAME}
                    WHERE order_id = %s
                    ORDER BY created_at DESC
                """, (order_id,))

                rows = cur.fetchall()
                for row in rows:
                    for key in ["weigh_date", "delivery_time", "uploaded_at", "created_at", "updated_at"]:
                        if row.get(key):
                            row[key] = str(row[key])
                return rows

    @classmethod
    def get_stats(cls, user_id: Optional[int] = None) -> Dict[str, int]:
        """获取统计信息"""
        with get_conn() as conn:
            with conn.cursor() as cur:
                if user_id:
                    cur.execute("""
                        SELECT 
                            COUNT(*) as total,
                            SUM(CASE WHEN ocr_status = '待确认' THEN 1 ELSE 0 END) as pending,
                            SUM(CASE WHEN ocr_status = '已确认' THEN 1 ELSE 0 END) as confirmed,
                            SUM(CASE WHEN ocr_status = '已修正' THEN 1 ELSE 0 END) as corrected
                        FROM pd_weighbills
                        WHERE uploader_id = %s
                    """, (user_id,))
                else:
                    cur.execute("""
                        SELECT 
                            COUNT(*) as total,
                            SUM(CASE WHEN ocr_status = '待确认' THEN 1 ELSE 0 END) as pending,
                            SUM(CASE WHEN ocr_status = '已确认' THEN 1 ELSE 0 END) as confirmed,
                            SUM(CASE WHEN ocr_status = '已修正' THEN 1 ELSE 0 END) as corrected
                        FROM pd_weighbills
                    """)

                row = cur.fetchone()
                return {
                    "total": row["total"] or 0,
                    "pending": row["pending"] or 0,
                    "confirmed": row["confirmed"] or 0,
                    "corrected": row["corrected"] or 0
                }