# -*- coding: utf-8 -*-
"""胸痛中心业务认证依赖（与框架 sys_user 认证完全隔离）。

- ``get_current_business_user``：解析 Bearer JWT → Redis ``cpx_session:{sid}`` → 实时加载 user_account。
- ``BusinessRole``：按角色码（admin/auditor/doctor）做接口级权限校验。
"""

import json
from typing import Any

from fastapi import Depends
from redis.asyncio.client import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import RET
from app.config.setting import settings
from app.core.dependencies import db_getter, redis_getter
from app.core.exceptions import CustomException
from app.core.redis_crud import RedisCURD
from app.core.security import OAuth2Schema, decode_access_token

from app.plugin.module_cpx.models import UserAccountModel

# 业务会话 Redis key 前缀（与框架 user_session 隔离）
CPX_SESSION_PREFIX = "cpx_session"

# 角色名 → 角色码
ROLE_ADMIN = "admin"
ROLE_AUDITOR = "auditor"
ROLE_DOCTOR = "doctor"

ROLE_NAME_ADMIN = "管理员"
ROLE_NAME_AUDITOR = "审核员"
ROLE_NAME_DOCTOR = "医生"

ROLE_CODE_MAP: dict[str, str] = {
    ROLE_NAME_ADMIN: ROLE_ADMIN,
    ROLE_NAME_AUDITOR: ROLE_AUDITOR,
    ROLE_NAME_DOCTOR: ROLE_DOCTOR,
}


class BizUser:
    """业务登录用户上下文（当前登录的业务用户）"""

    def __init__(
        self,
        *,
        id: int,
        username: str,
        real_name: str,
        role_id: int,
        role_name: str,
        role_code: str,
        hospital_id: int | None,
        hospital_name: str | None,
        hospital_status: int | None = None,
    ) -> None:
        self.id = id
        self.username = username
        self.real_name = real_name
        self.role_id = role_id
        self.role_name = role_name
        self.role_code = role_code
        self.hospital_id = hospital_id
        self.hospital_name = hospital_name
        self.hospital_status = hospital_status

    def is_admin(self) -> bool:
        return self.role_code == ROLE_ADMIN

    def is_auditor(self) -> bool:
        return self.role_code == ROLE_AUDITOR

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "username": self.username,
            "real_name": self.real_name,
            "role_id": self.role_id,
            "role_name": self.role_name,
            "role_code": self.role_code,
            "hospital_id": self.hospital_id,
            "hospital_name": self.hospital_name,
        }


class BizAuth:
    """业务认证上下文（等价框架 AuthSchema）"""

    def __init__(self, user: BizUser) -> None:
        self.user = user


async def get_current_business_user(
    db: AsyncSession = Depends(db_getter),
    redis: Redis = Depends(redis_getter),
    token: str = Depends(OAuth2Schema),
) -> BizAuth:
    """业务认证：校验 token → 读 cpx_session → 实时加载 user_account 与角色/医院。"""
    if not token:
        raise CustomException(msg="认证已失效", code=RET.UNAUTHORIZED.code, status_code=401)
    if token.startswith("Bearer"):
        token = token.split(" ")[1]

    payload = decode_access_token(token, verify_exp=not settings.TOKEN_SLIDING_EXPIRE)
    if not payload or payload.is_refresh:
        raise CustomException(msg="非法凭证", code=RET.INVALID_CREDENTIALS.code, status_code=401)

    session_id = payload.sub
    if not session_id:
        raise CustomException(msg="认证已失效", code=RET.UNAUTHORIZED.code, status_code=401)

    raw = await RedisCURD(redis).get(f"{CPX_SESSION_PREFIX}:{session_id}")
    if not raw:
        raise CustomException(msg="认证已失效", code=RET.UNAUTHORIZED.code, status_code=401)

    try:
        session: dict[str, Any] = json.loads(raw)
    except json.JSONDecodeError:
        raise CustomException(msg="认证已失效", code=RET.UNAUTHORIZED.code, status_code=401)

    user_id = session.get("user_id")
    if not user_id:
        raise CustomException(msg="认证已失效", code=RET.UNAUTHORIZED.code, status_code=401)

    user = await db.get(UserAccountModel, user_id)
    if not user:
        raise CustomException(msg="用户不存在", code=RET.NOT_FOUND.code, status_code=401)
    if user.status == 0:
        raise CustomException(msg="账号已被禁用", code=RET.UNAUTHORIZED.code, status_code=401)

    role = await user.awaitable_attrs.role
    role_name = role.role_name if role else ""
    role_code = ROLE_CODE_MAP.get(role_name, "")
    hospital = await user.awaitable_attrs.hospital

    return BizAuth(
        user=BizUser(
            id=user.id,
            username=user.username,
            real_name=user.real_name,
            role_id=user.role_id,
            role_name=role_name,
            role_code=role_code,
            hospital_id=user.hospital_id,
            hospital_name=hospital.hospital_name if hospital else None,
            hospital_status=hospital.status if hospital else None,
        )
    )


class BusinessRole:
    """角色校验依赖：仅允许指定角色码访问。"""

    def __init__(self, roles: list[str]) -> None:
        self.roles = roles

    async def __call__(self, auth: BizAuth = Depends(get_current_business_user)) -> BizAuth:
        if auth.user.role_code in self.roles:
            return auth
        raise CustomException(msg="无权限操作", code=RET.FORBIDDEN.code, status_code=403)
