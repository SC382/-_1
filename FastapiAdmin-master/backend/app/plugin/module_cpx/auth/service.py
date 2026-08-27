# -*- coding: utf-8 -*-
"""业务认证服务：登录 / 登出 / 用户信息。"""

import json
from datetime import datetime, timedelta

from redis.asyncio.client import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.setting import settings
from app.core.base_schema import JWTPayloadSchema
from app.core.exceptions import CustomException
from app.core.redis_crud import RedisCURD
from app.core.security import create_access_token
from app.utils.common_util import uuid4_str
from app.utils.password_util import PwdUtil

from app.plugin.module_cpx.auth.dependencies import (
    ROLE_CODE_MAP,
    ROLE_NAME_ADMIN,
    ROLE_NAME_AUDITOR,
    ROLE_NAME_DOCTOR,
    BizAuth,
    CPX_SESSION_PREFIX,
)
from app.plugin.module_cpx.models import UserAccountModel


class AuthService:
    """业务认证服务"""

    def __init__(self, db: AsyncSession, redis: Redis) -> None:
        self.db = db
        self.redis = redis

    async def login(self, username: str, password: str) -> dict:
        """业务登录：校验 user_account + 密码 + 状态 + 角色 + 医院状态。"""
        result = await self.db.execute(
            select(UserAccountModel).where(UserAccountModel.username == username)
        )
        user = result.scalars().first()

        if not user:
            raise CustomException(msg="用户不存在", code=10401, status_code=401)
        if not PwdUtil.verify_password(password, user.password):
            raise CustomException(msg="密码错误", code=10401, status_code=401)
        if user.status == 0:
            raise CustomException(msg="账号已被禁用", code=10401, status_code=401)

        role = await user.awaitable_attrs.role
        role_name = role.role_name if role else ""
        role_code = ROLE_CODE_MAP.get(role_name, "")

        # 允许 管理员 / 审核员 / 医生 三种角色登录（Web 管理端 / APP 医生端共用业务登录）
        if role_name not in (ROLE_NAME_ADMIN, ROLE_NAME_AUDITOR, ROLE_NAME_DOCTOR):
            raise CustomException(msg="该账号无登录权限", code=10403, status_code=403)

        hospital = await user.awaitable_attrs.hospital
        # 审核员 / 医生必须关联正常状态的医院
        if role_code in ("auditor", "doctor"):
            if not hospital:
                raise CustomException(msg="账号未关联医院", code=10401, status_code=401)
            if hospital.status == 0:
                raise CustomException(msg="所属医院已被禁用", code=10401, status_code=401)

        now = datetime.now()
        session_id = uuid4_str()
        access_expires = timedelta(seconds=settings.ACCESS_TOKEN_EXPIRE_SECONDS)

        session_dict: dict = {
            "session_id": session_id,
            "user_id": user.id,
            "username": user.username,
            "real_name": user.real_name,
            "role_id": user.role_id,
            "role_name": role_name,
            "role_code": role_code,
            "hospital_id": user.hospital_id,
            "hospital_name": hospital.hospital_name if hospital else None,
            "user_status": user.status,
        }
        await RedisCURD(self.redis).set(
            key=f"{CPX_SESSION_PREFIX}:{session_id}",
            value=json.dumps(session_dict, default=str),
            expire=settings.ACCESS_TOKEN_EXPIRE_SECONDS,
        )

        access_token = create_access_token(
            payload=JWTPayloadSchema(sub=session_id, is_refresh=False, exp=now + access_expires)
        )

        user.last_login_time = now
        self.db.add(user)
        await self.db.flush()

        return {
            "access_token": access_token,
            "token_type": settings.TOKEN_TYPE,
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_SECONDS,
            "userinfo": session_dict,
        }

    async def logout(self, token: str) -> None:
        """登出：删除业务会话并记录退出日志（不因 token 失效而报错）。"""
        token = token.removeprefix("Bearer ").strip()
        from app.core.security import decode_access_token
        from app.plugin.module_cpx.log.service import LogService

        try:
            payload = decode_access_token(token)
            session_id = payload.sub

            # 从会话中取 user_id，写退出日志
            user_id = None
            raw = await RedisCURD(self.redis).get(f"{CPX_SESSION_PREFIX}:{session_id}")
            if raw:
                try:
                    import json

                    user_id = json.loads(raw).get("user_id")
                except Exception:
                    user_id = None

            await RedisCURD(self.redis).delete(f"{CPX_SESSION_PREFIX}:{session_id}")

            if user_id:
                from app.plugin.module_cpx.models import UserAccountModel

                user = await self.db.get(UserAccountModel, user_id)
                if user:
                    await LogService.create(
                        self.db,
                        user_id=user.id,
                        module="认证管理",
                        operation="退出",
                        description=f"用户 {user.real_name}（{user.username}）退出系统",
                    )
        except Exception:
            # 登出不因 token 失效而报错
            pass

    async def userinfo(self, auth: BizAuth) -> dict:
        """当前业务用户信息（含角色码，供前端渲染菜单）。"""
        return auth.user.to_dict()
