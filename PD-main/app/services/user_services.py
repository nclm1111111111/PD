
import bcrypt
import re
from typing import Optional, Dict, Any, List
from enum import IntEnum
from datetime import datetime
import requests

from core.database import get_conn
from core.table_access import _quote_identifier
from core.logging import get_logger
from app.core.config import settings

logger = get_logger(__name__)


# ========== 枚举定义 ==========

class UserStatus(IntEnum):
    """用户状态枚举"""
    NORMAL = 0  # 正常
    FROZEN = 1  # 冻结
    DELETED = 2  # 已注销（软删除）


class UserRole:
    """用户角色"""
    ADMIN = "管理员"
    MANAGER = "大区经理"
    WAREHOUSE = "自营库管理"
    FINANCE = "财务"
    ACCOUNTANT = "会计"

    VALID_ROLES = [ADMIN, MANAGER, WAREHOUSE, FINANCE, ACCOUNTANT]

    # 角色层级（数字越大权限越高）
    HIERARCHY = {
        ADMIN: 100,
        MANAGER: 80,
        WAREHOUSE: 60,
        FINANCE: 60,
        ACCOUNTANT: 40
    }


# ========== 工具函数 ==========

def hash_pwd(password: str) -> str:
    """密码加密"""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()


def verify_pwd(password: str, hashed: str) -> bool:
    """密码校验"""
    return bcrypt.checkpw(password.encode(), hashed.encode())


def validate_account(account: str) -> bool:
    """验证账号格式（字母数字下划线，3-20位）"""
    return bool(re.match(r'^[a-zA-Z0-9_]{3,20}$', account))


def validate_phone(phone: str) -> bool:
    """验证手机号格式"""
    return bool(re.match(r'^1[3-9]\d{9}$', phone))


def validate_email(email: str) -> bool:
    """验证邮箱格式"""
    return bool(re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email))


# ========== 微信小程序服务 ==========

class WechatService:
    """微信小程序服务"""

    @staticmethod
    def code2session(code: str) -> dict:
        """获取openid和session_key"""
        url = settings.WECHAT_LOGIN_URL
        params = {
            "appid": settings.WECHAT_APP_ID,
            "secret": settings.WECHAT_APP_SECRET,
            "js_code": code,
            "grant_type": "authorization_code"
        }

        response = requests.get(url, params=params)
        result = response.json()

        if "errcode" in result and result["errcode"] != 0:
            raise Exception(f"微信接口错误: {result.get('errmsg')}")

        return result

    @staticmethod
    def get_phone_number(session_key: str, encrypted_data: str, iv: str) -> Optional[str]:
        """
        解密手机号
        实际实现需要根据微信官方文档
        """
        # 这里简化处理，实际需要 AES 解密
        # 建议使用 wechatpy 或自行实现解密
        return None


# ========== 用户认证服务 ==========

class AuthService:

    # ========== 微信小程序认证 ==========

    @staticmethod
    def wechat_login(code: str, user_info: Optional[Dict] = None) -> Dict[str, Any]:
        """
        微信小程序登录
        """
        try:
            # 1. 调用微信接口
            wechat_result = WechatService.code2session(code)
            openid = wechat_result["openid"]
            session_key = wechat_result["session_key"]
            unionid = wechat_result.get("unionid")

            # 2. 查找或创建用户
            with get_conn() as conn:
                with conn.cursor() as cur:
                    # 查找用户
                    cur.execute(
                        "SELECT id, nickname, avatar_url FROM pd_users WHERE openid = %s",
                        (openid,)
                    )
                    user = cur.fetchone()
                    is_new_user = False

                    if not user:
                        # 创建新用户
                        cur.execute("""
                            INSERT INTO pd_users (openid, session_key, unionid, status, created_at)
                            VALUES (%s, %s, %s, %s, NOW())
                        """, (openid, session_key, unionid, UserStatus.NORMAL))

                        user_id = cur.lastrowid
                        is_new_user = True
                        nickname = None
                        avatar_url = None

                        # 如果有用户信息，更新资料
                        if user_info:
                            update_fields = []
                            update_params = []

                            if user_info.get("nickName"):
                                update_fields.append("nickname = %s")
                                update_params.append(user_info["nickName"])
                                nickname = user_info["nickName"]
                            if user_info.get("avatarUrl"):
                                update_fields.append("avatar_url = %s")
                                update_params.append(user_info["avatarUrl"])
                                avatar_url = user_info["avatarUrl"]
                            if user_info.get("gender") is not None:
                                update_fields.append("gender = %s")
                                update_params.append(user_info["gender"])

                            if update_fields:
                                update_params.append(user_id)
                                cur.execute(f"""
                                    UPDATE pd_users 
                                    SET {', '.join(update_fields)}
                                    WHERE id = %s
                                """, tuple(update_params))
                    else:
                        user_id = user["id"]
                        nickname = user.get("nickname")
                        avatar_url = user.get("avatar_url")
                        # 更新session_key
                        cur.execute(
                            "UPDATE pd_users SET session_key = %s WHERE id = %s",
                            (session_key, user_id)
                        )

                    # 更新最后登录时间
                    cur.execute(
                        "UPDATE pd_users SET last_login_at = NOW() WHERE id = %s",
                        (user_id,)
                    )

                    conn.commit()

            return {
                "success": True,
                "user_id": user_id,
                "is_new_user": is_new_user,
                "nickname": nickname,
                "avatar_url": avatar_url
            }

        except Exception as e:
            logger.exception("微信登录失败")
            raise ValueError(f"微信登录失败: {str(e)}")
    # ========== 后台用户认证 ==========

    @staticmethod
    def authenticate(account: str, password: str) -> Dict[str, Any]:
        """
        后台用户认证（登录）
        """
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, name, account, password_hash, role, status, phone, email
                    FROM pd_users
                    WHERE account = %s AND status != %s
                """, (account, UserStatus.DELETED))

                user = cur.fetchone()

                if not user:
                    raise ValueError("账号或密码错误")

                # 验证密码
                stored_hash = user.pop("password_hash")
                if not verify_pwd(password, stored_hash):
                    raise ValueError("账号或密码错误")

                return user

    @staticmethod
    def create_user(
            name: str,
            account: str,
            password: str,
            role: str,
            phone: Optional[str] = None,
            email: Optional[str] = None,
            created_by: Optional[int] = None
    ) -> int:
        """
        创建后台用户
        """
        # 参数校验
        if not validate_account(account):
            raise ValueError("账号格式错误（3-20位字母数字下划线）")

        if phone and not validate_phone(phone):
            raise ValueError("手机号格式错误")

        if email and not validate_email(email):
            raise ValueError("邮箱格式错误")

        if role not in UserRole.VALID_ROLES:
            raise ValueError(f"无效的角色: {role}")

        pwd_hash = hash_pwd(password)

        with get_conn() as conn:
            with conn.cursor() as cur:
                # 检查账号是否已存在
                cur.execute("SELECT 1 FROM pd_users WHERE account = %s", (account,))
                if cur.fetchone():
                    raise ValueError("账号已存在")

                # 检查手机号是否已被使用
                if phone:
                    cur.execute(
                        "SELECT 1 FROM pd_users WHERE phone = %s AND status != %s",
                        (phone, UserStatus.DELETED)
                    )
                    if cur.fetchone():
                        raise ValueError("手机号已被注册")

                # 插入用户
                cur.execute("""
                    INSERT INTO pd_users 
                    (name, account, password_hash, role, phone, email, created_by, status, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
                """, (name, account, pwd_hash, role, phone, email, created_by, UserStatus.NORMAL))

                user_id = cur.lastrowid
                conn.commit()

                logger.info(f"创建用户成功: {account} (ID: {user_id}, 角色: {role})")
                return user_id

    @staticmethod
    def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
        """
        根据ID获取用户信息
        """
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, name, account, role, phone, email, status, created_at, updated_at
                    FROM pd_users
                    WHERE id = %s
                """, (user_id,))
                return cur.fetchone()

    @staticmethod
    def get_user_by_account(account: str) -> Optional[Dict[str, Any]]:
        """
        根据账号获取用户信息
        """
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, name, account, role, phone, email, status
                    FROM pd_users
                    WHERE account = %s AND status != %s
                """, (account, UserStatus.DELETED))
                return cur.fetchone()

    @staticmethod
    def update_user(user_id: int, **kwargs) -> bool:
        """
        更新用户信息
        """
        allowed_fields = ["name", "phone", "email", "role"]
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields and v is not None}

        if not updates:
            raise ValueError("无有效更新字段")

        # 验证数据
        if "phone" in updates and updates["phone"] and not validate_phone(updates["phone"]):
            raise ValueError("手机号格式错误")
        if "email" in updates and updates["email"] and not validate_email(updates["email"]):
            raise ValueError("邮箱格式错误")
        if "role" in updates and updates["role"] not in UserRole.VALID_ROLES:
            raise ValueError("无效的角色")

        with get_conn() as conn:
            with conn.cursor() as cur:
                # 检查用户是否存在
                cur.execute("SELECT 1 FROM pd_users WHERE id = %s", (user_id,))
                if not cur.fetchone():
                    raise ValueError("用户不存在")

                # 检查手机号唯一性
                if "phone" in updates and updates["phone"]:
                    cur.execute("""
                        SELECT 1 FROM pd_users 
                        WHERE phone = %s AND id != %s AND status != %s
                    """, (updates["phone"], user_id, UserStatus.DELETED))
                    if cur.fetchone():
                        raise ValueError("手机号已被其他用户使用")

                # 构建更新SQL
                set_clause = ", ".join([f"{k} = %s" for k in updates.keys()])
                params = list(updates.values()) + [user_id]

                cur.execute(f"UPDATE pd_users SET {set_clause} WHERE id = %s", tuple(params))
                conn.commit()

                logger.info(f"更新用户成功: ID={user_id}, 字段={list(updates.keys())}")
                return True

    @staticmethod
    def change_password(user_id: int, old_password: str, new_password: str) -> bool:
        """
        用户修改密码
        """
        with get_conn() as conn:
            with conn.cursor() as cur:
                # 获取当前密码哈希
                cur.execute(
                    "SELECT password_hash FROM pd_users WHERE id = %s AND status != %s",
                    (user_id, UserStatus.DELETED)
                )
                row = cur.fetchone()
                if not row:
                    raise ValueError("用户不存在")

                # 验证旧密码
                if not verify_pwd(old_password, row["password_hash"]):
                    raise ValueError("旧密码错误")

                # 更新密码
                new_hash = hash_pwd(new_password)
                cur.execute(
                    "UPDATE pd_users SET password_hash = %s WHERE id = %s",
                    (new_hash, user_id)
                )
                conn.commit()

                logger.info(f"用户修改密码成功: ID={user_id}")
                return True

    @staticmethod
    def admin_reset_password(user_id: int, new_password: str) -> bool:
        """
        管理员重置密码
        """
        with get_conn() as conn:
            with conn.cursor() as cur:
                # 检查用户是否存在
                cur.execute("SELECT 1 FROM pd_users WHERE id = %s", (user_id,))
                if not cur.fetchone():
                    raise ValueError("用户不存在")

                new_hash = hash_pwd(new_password)
                cur.execute(
                    "UPDATE pd_users SET password_hash = %s WHERE id = %s",
                    (new_hash, user_id)
                )
                conn.commit()

                logger.info(f"管理员重置密码: ID={user_id}")
                return True

    @staticmethod
    def set_user_status(user_id: int, status: UserStatus) -> bool:
        """
        设置用户状态（冻结/解冻/注销）
        """
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT status FROM pd_users WHERE id = %s", (user_id,))
                row = cur.fetchone()
                if not row:
                    raise ValueError("用户不存在")

                old_status = row["status"]
                if old_status == status:
                    raise ValueError("状态未变化")

                cur.execute(
                    "UPDATE pd_users SET status = %s WHERE id = %s",
                    (int(status), user_id)
                )
                conn.commit()

                status_names = {0: "正常", 1: "冻结", 2: "注销"}
                logger.info(
                    f"用户状态变更: ID={user_id}, {status_names.get(old_status)} -> {status_names.get(int(status))}")
                return True

    @staticmethod
    def delete_user(user_id: int) -> bool:
        """
        删除用户（软删除）
        """
        return AuthService.set_user_status(user_id, UserStatus.DELETED)

    @staticmethod
    def list_users(
            page: int = 1,
            size: int = 20,
            role: Optional[str] = None,
            keyword: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取用户列表（分页）
        """
        with get_conn() as conn:
            with conn.cursor() as cur:
                # 构建WHERE条件
                where_conditions = ["status != %s"]
                params = [UserStatus.DELETED]

                if role:
                    where_conditions.append("role = %s")
                    params.append(role)

                if keyword:
                    where_conditions.append("(name LIKE %s OR account LIKE %s)")
                    params.extend([f"%{keyword}%", f"%{keyword}%"])

                where_clause = " AND ".join(where_conditions)

                # 查询总数
                cur.execute(f"SELECT COUNT(*) as total FROM pd_users WHERE {where_clause}", tuple(params))
                total = cur.fetchone()["total"]

                # 查询列表
                offset = (page - 1) * size
                cur.execute(f"""
                    SELECT id, name, account, role, phone, email, status, created_at, updated_at
                    FROM pd_users
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

    @staticmethod
    def check_permission(user_role: str, required_role: str) -> bool:
        """
        检查角色权限
        """
        user_level = UserRole.HIERARCHY.get(user_role, 0)
        required_level = UserRole.HIERARCHY.get(required_role, 0)
        return user_level >= required_levellevel >= required_level