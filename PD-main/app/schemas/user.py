"""
用户相关 Pydantic 模型
合并自：user.py + pd_user.py
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime
import re


# ========== 通用验证器 ==========

def validate_phone(v: Optional[str]) -> Optional[str]:
    """验证手机号"""
    if v and not re.match(r'^1[3-9]\d{9}$', v):
        raise ValueError('手机号格式错误')
    return v


def validate_email(v: Optional[str]) -> Optional[str]:
    """验证邮箱"""
    if v and not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', v):
        raise ValueError('邮箱格式错误')
    return v


def validate_account(v: str) -> str:
    """验证账号"""
    if not re.match(r'^[a-zA-Z0-9_]{3,20}$', v):
        raise ValueError('账号必须是3-20位字母数字下划线')
    return v


# ========== 微信小程序认证 ==========

class WechatLoginRequest(BaseModel):
    """微信小程序登录请求"""
    code: str = Field(..., description="微信登录code")
    encrypted_data: Optional[str] = Field(None, description="加密数据")
    iv: Optional[str] = Field(None, description="加密向量")
    user_info: Optional[Dict[str, Any]] = Field(None, description="用户信息")


class WechatLoginResponse(BaseModel):
    """微信小程序登录响应"""
    access_token: str = Field(..., description="访问令牌")
    token_type: str = "bearer"
    expires_in: int = Field(..., description="过期时间（秒）")
    is_new_user: bool = Field(..., description="是否新用户")
    user_id: int = Field(..., description="用户ID")
    nickname: Optional[str] = Field(None, description="昵称")
    avatar_url: Optional[str] = Field(None, description="头像URL")


class WechatPhoneRequest(BaseModel):
    """绑定手机号请求"""
    code: Optional[str] = Field(None, description="微信code")
    encrypted_data: str = Field(..., description="加密数据")
    iv: str = Field(..., description="加密向量")


# ========== 账号密码登录 ==========

class UserLogin(BaseModel):
    """用户名密码登录请求"""
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")

    class Config:
        json_schema_extra = {
            "example": {
                "username": "admin",
                "password": "password123"
            }
        }


class Token(BaseModel):
    """令牌响应"""
    access_token: str = Field(..., description="访问令牌")
    refresh_token: Optional[str] = Field(None, description="刷新令牌")
    token_type: str = "bearer"


class TokenData(BaseModel):
    """令牌数据"""
    user_id: Optional[int] = None
    openid: Optional[str] = None


# ========== 用户基础模型 ==========

class UserBase(BaseModel):
    """用户基础信息"""
    name: Optional[str] = Field(None, description="姓名")
    account: Optional[str] = Field(None, description="登录账号")
    username: Optional[str] = Field(None, description="用户名")
    phone: Optional[str] = Field(None, description="手机号")
    email: Optional[str] = Field(None, description="邮箱")
    nickname: Optional[str] = Field(None, description="昵称")
    avatar_url: Optional[str] = Field(None, description="头像URL")
    role: Optional[str] = Field(None, description="角色")

    @validator('phone')
    def validate_phone(cls, v):
        return validate_phone(v)

    @validator('email')
    def validate_email(cls, v):
        return validate_email(v)


class UserCreate(UserBase):
    """创建用户请求"""
    password: str = Field(..., min_length=6, description="密码")

    @validator('account')
    def validate_account(cls, v):
        if v:
            return validate_account(v)
        return v


class UserUpdate(BaseModel):
    """更新用户信息请求"""
    name: Optional[str] = Field(None, description="姓名")
    phone: Optional[str] = Field(None, description="手机号")
    email: Optional[str] = Field(None, description="邮箱")
    nickname: Optional[str] = Field(None, description="昵称")
    avatar_url: Optional[str] = Field(None, description="头像URL")
    role: Optional[str] = Field(None, description="角色")

    @validator('phone')
    def validate_phone(cls, v):
        return validate_phone(v)

    @validator('email')
    def validate_email(cls, v):
        return validate_email(v)


class UserInDB(UserBase):
    """数据库中的用户信息"""
    id: int
    openid: Optional[str] = None
    status: int = 0
    is_active: bool = True
    is_verified: bool = False
    created_by: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ========== PD后台用户 ==========

class PDLoginReq(BaseModel):
    """后台用户登录请求"""
    account: str = Field(..., description="登录账号")
    password: str = Field(..., description="密码")


class PDLoginResp(BaseModel):
    """后台用户登录响应"""
    uid: int = Field(..., description="用户ID")
    token: str = Field(..., description="访问令牌")
    expires_in: int = Field(..., description="过期时间（秒）")
    user: dict = Field(..., description="用户信息")


class PDUserCreate(BaseModel):
    """创建后台用户请求"""
    name: str = Field(..., description="用户姓名")
    account: str = Field(..., description="登录账号")
    password: str = Field(..., min_length=6, description="密码")
    role: str = Field(..., description="角色")
    phone: Optional[str] = Field(None, description="手机号")
    email: Optional[str] = Field(None, description="邮箱")

    @validator('account')
    def validate_account(cls, v):
        return validate_account(v)

    @validator('phone')
    def validate_phone(cls, v):
        return validate_phone(v)

    @validator('email')
    def validate_email(cls, v):
        return validate_email(v)


class PDUserUpdate(BaseModel):
    """更新后台用户请求"""
    name: Optional[str] = Field(None, description="用户姓名")
    phone: Optional[str] = Field(None, description="手机号")
    email: Optional[str] = Field(None, description="邮箱")
    role: Optional[str] = Field(None, description="角色")


class UpdatePwdReq(BaseModel):
    """修改密码请求"""
    old_password: str = Field(..., description="旧密码")
    new_password: str = Field(..., min_length=6, description="新密码")


class ResetPwdReq(BaseModel):
    """重置密码请求"""
    admin_key: str = Field(..., description="管理密钥")
    new_password: str = Field(..., min_length=6, description="新密码")


class UserListQuery(BaseModel):
    """用户列表查询参数"""
    page: int = Field(1, ge=1, description="页码")
    size: int = Field(20, ge=1, le=100, description="每页数量")
    role: Optional[str] = Field(None, description="按角色筛选")
    keyword: Optional[str] = Field(None, description="关键词搜索")


class UserResp(BaseModel):
    """用户响应"""
    id: int
    name: str
    account: str
    role: str
    phone: Optional[str] = None
    email: Optional[str] = None
    status: int
    created_at: datetime
    updated_at: Optional[datetime] = None


# ========== 角色接口 ==========

class RoleInfo(BaseModel):
    """角色信息"""
    code: str = Field(..., description="角色代码")
    name: str = Field(..., description="角色名称")
    description: str = Field(..., description="角色描述")