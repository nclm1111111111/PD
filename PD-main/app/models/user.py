"""
用户模型 - pymysql 版本
提供用户表的 CRUD 操作封装
"""
from typing import Optional, Dict, Any, List
from core.database import get_conn
from core.logging import get_logger

logger = get_logger(__name__)


class UserModel:
    """用户模型 - 对应 pd_users 表"""

    TABLE_NAME = "pd_users"

    # 表结构定义（供参考）
    SCHEMA = {
        "id": "INT PRIMARY KEY AUTO_INCREMENT",
        "name": "VARCHAR(50) NOT NULL",
        "account": "VARCHAR(50) NOT NULL UNIQUE",
        "password_hash": "VARCHAR(200) NOT NULL",
        "role": "VARCHAR(20) NOT NULL",
        "phone": "VARCHAR(20) UNIQUE",
        "email": "VARCHAR(100)",
        "openid": "VARCHAR(100) UNIQUE",
        "unionid": "VARCHAR(100)",
        "session_key": "VARCHAR(100)",
        "nickname": "VARCHAR(100)",
        "avatar_url": "VARCHAR(500)",
        "gender": "TINYINT DEFAULT 0",
        "is_verified": "TINYINT(1) DEFAULT 0",
        "status": "TINYINT DEFAULT 0",
        "created_by": "INT",
        "created_at": "DATETIME NOT NULL",
        "updated_at": "DATETIME",
        "last_login_at": "DATETIME"
    }

    # 常用字段列表
    BASE_FIELDS = ["id", "name", "account", "role", "phone", "email", "status", "created_at", "updated_at"]
    PROFILE_FIELDS = ["id", "name", "account", "role", "phone", "email", "nickname", "avatar_url", "gender",
                      "is_verified", "status", "created_at", "last_login_at"]
    WECHAT_FIELDS = ["id", "openid", "unionid", "nickname", "avatar_url", "gender", "is_verified"]

    @classmethod
    def get_by_id(cls, user_id: int, fields: List[str] = None) -> Optional[Dict[str, Any]]:
        """根据ID获取用户"""
        if fields is None:
            fields = cls.BASE_FIELDS

        fields_str = ", ".join(fields)

        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(f"""
                    SELECT {fields_str}
                    FROM {cls.TABLE_NAME}
                    WHERE id = %s
                """, (user_id,))
                return cur.fetchone()

    @classmethod
    def get_by_account(cls, account: str, fields: List[str] = None) -> Optional[Dict[str, Any]]:
        """根据账号获取用户"""
        if fields is None:
            fields = cls.BASE_FIELDS + ["password_hash"]

        fields_str = ", ".join(fields)

        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(f"""
                    SELECT {fields_str}
                    FROM {cls.TABLE_NAME}
                    WHERE account = %s AND status != 2
                """, (account,))
                return cur.fetchone()

    @classmethod
    def get_by_openid(cls, openid: str) -> Optional[Dict[str, Any]]:
        """根据openid获取用户"""
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(f"""
                    SELECT id, openid, unionid, nickname, avatar_url, session_key
                    FROM {cls.TABLE_NAME}
                    WHERE openid = %s
                """, (openid,))
                return cur.fetchone()

    @classmethod
    def get_by_phone(cls, phone: str) -> Optional[Dict[str, Any]]:
        """根据手机号获取用户"""
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(f"""
                    SELECT id, name, account, role
                    FROM {cls.TABLE_NAME}
                    WHERE phone = %s AND status != 2
                """, (phone,))
                return cur.fetchone()

    @classmethod
    def create(cls, data: Dict[str, Any]) -> int:
        """创建用户"""
        fields = []
        placeholders = []
        values = []

        for key, value in data.items():
            if key in cls.SCHEMA:
                fields.append(key)
                placeholders.append("%s")
                values.append(value)

        fields_str = ", ".join(fields)
        placeholders_str = ", ".join(placeholders)

        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(f"""
                    INSERT INTO {cls.TABLE_NAME} ({fields_str})
                    VALUES ({placeholders_str})
                """, tuple(values))
                conn.commit()
                return cur.lastrowid

    @classmethod
    def update(cls, user_id: int, data: Dict[str, Any]) -> bool:
        """更新用户"""
        set_parts = []
        values = []

        for key, value in data.items():
            if key in cls.SCHEMA and key not in ["id", "created_at"]:
                set_parts.append(f"{key} = %s")
                values.append(value)

        if not set_parts:
            return False

        values.append(user_id)
        set_clause = ", ".join(set_parts)

        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(f"""
                    UPDATE {cls.TABLE_NAME}
                    SET {set_clause}, updated_at = NOW()
                    WHERE id = %s
                """, tuple(values))
                conn.commit()
                return cur.rowcount > 0

    @classmethod
    def update_last_login(cls, user_id: int) -> bool:
        """更新最后登录时间"""
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(f"""
                    UPDATE {cls.TABLE_NAME}
                    SET last_login_at = NOW()
                    WHERE id = %s
                """, (user_id,))
                conn.commit()
                return cur.rowcount > 0

    @classmethod
    def update_password(cls, user_id: int, password_hash: str) -> bool:
        """更新密码"""
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(f"""
                    UPDATE {cls.TABLE_NAME}
                    SET password_hash = %s, updated_at = NOW()
                    WHERE id = %s
                """, (password_hash, user_id))
                conn.commit()
                return cur.rowcount > 0

    @classmethod
    def update_status(cls, user_id: int, status: int) -> bool:
        """更新状态"""
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(f"""
                    UPDATE {cls.TABLE_NAME}
                    SET status = %s, updated_at = NOW()
                    WHERE id = %s
                """, (status, user_id))
                conn.commit()
                return cur.rowcount > 0

    @classmethod
    def list_users(
            cls,
            page: int = 1,
            size: int = 20,
            role: Optional[str] = None,
            keyword: Optional[str] = None,
            status: Optional[int] = None
    ) -> Dict[str, Any]:
        """用户列表（分页）"""
        where_conditions = ["1=1"]
        params = []

        if role:
            where_conditions.append("role = %s")
            params.append(role)

        if status is not None:
            where_conditions.append("status = %s")
            params.append(status)
        else:
            where_conditions.append("status != 2")  # 默认排除已删除

        if keyword:
            where_conditions.append("(name LIKE %s OR account LIKE %s OR phone LIKE %s)")
            like = f"%{keyword}%"
            params.extend([like, like, like])

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
                offset = (page - 1) * size
                cur.execute(f"""
                    SELECT id, name, account, role, phone, email, status, created_at, updated_at
                    FROM {cls.TABLE_NAME}
                    WHERE {where_clause}
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                """, tuple(params + [size, offset]))

                rows = cur.fetchall()

                return {
                    "total": total,
                    "page": page,
                    "size": size,
                    "pages": (total + size - 1) // size,
                    "list": rows
                }

    @classmethod
    def count_by_role(cls, role: str) -> int:
        """按角色统计用户数"""
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(f"""
                    SELECT COUNT(*) as total
                    FROM {cls.TABLE_NAME}
                    WHERE role = %s AND status != 2
                """, (role,))
                result = cur.fetchone()
                return result["total"] if result else 0