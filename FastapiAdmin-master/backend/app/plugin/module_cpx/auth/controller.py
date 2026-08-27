# -*- coding: utf-8 -*-
"""业务认证路由 /cpx/auth/*"""

from typing import Annotated

from fastapi import APIRouter, Body, Depends, Request
from fastapi.responses import JSONResponse
from redis.asyncio.client import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import SuccessResponse
from app.core.dependencies import db_getter, redis_getter
from app.core.security import OAuth2Schema

from app.plugin.module_cpx.auth.dependencies import BizAuth, get_current_business_user
from app.plugin.module_cpx.auth.schema import LoginSchema
from app.plugin.module_cpx.auth.service import AuthService
from app.plugin.module_cpx.log.service import LogService, get_client_ip

AuthRouter = APIRouter(prefix="/auth", tags=["业务登录认证"])


@AuthRouter.post("/login", summary="业务登录")
async def login_controller(
    data: Annotated[LoginSchema, Body(description="登录参数")],
    db: Annotated[AsyncSession, Depends(db_getter)],
    redis: Annotated[Redis, Depends(redis_getter)],
    request: Request,
) -> JSONResponse:
    service = AuthService(db, redis)
    result = await service.login(username=data.username, password=data.password)
    # 记录登录日志（强制留痕）
    userinfo = result.get("userinfo") or {}
    await LogService.create(
        db,
        user_id=userinfo.get("id"),
        module="认证管理",
        operation="登录",
        description=f"用户 {userinfo.get('real_name') or data.username}（{data.username}）登录系统",
        ip_address=get_client_ip(request),
    )
    return SuccessResponse(data=result, msg="登录成功")


@AuthRouter.post("/logout", summary="业务登出")
async def logout_controller(
    db: Annotated[AsyncSession, Depends(db_getter)],
    redis: Annotated[Redis, Depends(redis_getter)],
    token: str = Depends(OAuth2Schema),
) -> JSONResponse:
    service = AuthService(db, redis)
    await service.logout(token)
    return SuccessResponse(msg="退出成功")


@AuthRouter.get("/userinfo", summary="当前用户信息")
async def userinfo_controller(
    auth: Annotated[BizAuth, Depends(get_current_business_user)],
    db: Annotated[AsyncSession, Depends(db_getter)],
    redis: Annotated[Redis, Depends(redis_getter)],
) -> JSONResponse:
    service = AuthService(db, redis)
    result = await service.userinfo(auth)
    return SuccessResponse(data=result, msg="获取用户信息成功")
