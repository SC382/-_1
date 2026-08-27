# -*- coding: utf-8 -*-
"""增值服务管理路由 /cpx/value-added/*"""

from typing import Annotated

from fastapi import APIRouter, Body, Depends, Path, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import SuccessResponse
from app.core.dependencies import db_getter

from app.plugin.module_cpx.auth.dependencies import ROLE_ADMIN, ROLE_DOCTOR, BizAuth, BusinessRole
from app.plugin.module_cpx.log.service import LogService, get_client_ip
from app.plugin.module_cpx.value_added.schema import ValueAddedCreateSchema, ValueAddedUpdateSchema
from app.plugin.module_cpx.value_added.service import ValueAddedService

ValueAddedRouter = APIRouter(prefix="/value-added", tags=["增值服务管理"])


# ── Web 端管理（admin） ────────────────────────────────────────


@ValueAddedRouter.get("/list", summary="分页查询增值服务")
async def get_value_added_list_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_ADMIN]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    page_no: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=10, ge=1, le=100, description="每页条数"),
    keyword: str | None = Query(default=None, description="名称模糊查询"),
    status: str | None = Query(default=None, description="状态 draft/online/offline"),
) -> JSONResponse:
    service = ValueAddedService(auth, db)
    result = await service.page(page_no=page_no, page_size=page_size, keyword=keyword, status=status)
    return SuccessResponse(data=result, msg="查询增值服务列表成功")


@ValueAddedRouter.get("/detail/{id}", summary="获取增值服务详情")
async def get_value_added_detail_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_ADMIN]))],
    id: Annotated[int, Path(description="服务ID")],
    db: Annotated[AsyncSession, Depends(db_getter)],
) -> JSONResponse:
    service = ValueAddedService(auth, db)
    result = await service.detail(id=id)
    return SuccessResponse(data=result, msg="获取详情成功")


@ValueAddedRouter.post("/create", summary="新增增值服务")
async def create_value_added_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_ADMIN]))],
    data: Annotated[ValueAddedCreateSchema, Body(description="新增参数")],
    db: Annotated[AsyncSession, Depends(db_getter)],
    request: Request,
) -> JSONResponse:
    service = ValueAddedService(auth, db)
    result = await service.create(data=data)
    await LogService.create(
        db,
        user_id=auth.user.id,
        module="增值服务管理",
        operation="新增服务",
        description=f"新增服务：{result['name']}",
        ip_address=get_client_ip(request),
    )
    return SuccessResponse(data=result, msg="新增成功")


@ValueAddedRouter.put("/update/{id}", summary="修改增值服务")
async def update_value_added_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_ADMIN]))],
    id: Annotated[int, Path(description="服务ID")],
    data: Annotated[ValueAddedUpdateSchema, Body(description="修改参数")],
    db: Annotated[AsyncSession, Depends(db_getter)],
    request: Request,
) -> JSONResponse:
    service = ValueAddedService(auth, db)
    result = await service.update(id=id, data=data)
    await LogService.create(
        db,
        user_id=auth.user.id,
        module="增值服务管理",
        operation="修改服务",
        description=f"修改服务：{result['name']}",
        ip_address=get_client_ip(request),
    )
    return SuccessResponse(data=result, msg="修改成功")


@ValueAddedRouter.put("/online/{id}", summary="上线增值服务")
async def online_value_added_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_ADMIN]))],
    id: Annotated[int, Path(description="服务ID")],
    db: Annotated[AsyncSession, Depends(db_getter)],
    request: Request,
) -> JSONResponse:
    service = ValueAddedService(auth, db)
    result = await service.online(id=id)
    await LogService.create(
        db,
        user_id=auth.user.id,
        module="增值服务管理",
        operation="上线服务",
        description=f"上线服务：{result['name']}",
        ip_address=get_client_ip(request),
    )
    return SuccessResponse(data=result, msg="上线成功")


@ValueAddedRouter.put("/offline/{id}", summary="下线增值服务")
async def offline_value_added_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_ADMIN]))],
    id: Annotated[int, Path(description="服务ID")],
    db: Annotated[AsyncSession, Depends(db_getter)],
    request: Request,
) -> JSONResponse:
    service = ValueAddedService(auth, db)
    result = await service.offline(id=id)
    await LogService.create(
        db,
        user_id=auth.user.id,
        module="增值服务管理",
        operation="下线服务",
        description=f"下线服务：{result['name']}",
        ip_address=get_client_ip(request),
    )
    return SuccessResponse(data=result, msg="下线成功")


@ValueAddedRouter.delete("/{id}", summary="删除增值服务")
async def delete_value_added_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_ADMIN]))],
    id: Annotated[int, Path(description="服务ID")],
    db: Annotated[AsyncSession, Depends(db_getter)],
    request: Request,
) -> JSONResponse:
    service = ValueAddedService(auth, db)
    result = await service.delete(id=id)
    await LogService.create(
        db,
        user_id=auth.user.id,
        module="增值服务管理",
        operation="删除服务",
        description=f"删除服务：{result['name']}",
        ip_address=get_client_ip(request),
    )
    return SuccessResponse(data=result, msg="已删除")


# ── App 端公开（已登录医生可访问） ─────────────────────────────


@ValueAddedRouter.get("/active", summary="App 端：已上线增值服务列表")
async def active_value_added_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_DOCTOR]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    limit: int = Query(default=20, ge=1, le=50, description="返回条数"),
) -> JSONResponse:
    service = ValueAddedService(auth, db)
    items = await service.active_list(limit=limit)
    return SuccessResponse(data=items, msg="查询成功")