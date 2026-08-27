# -*- coding: utf-8 -*-
"""医院用户管理路由 /cpx/user/*"""

from typing import Annotated

from fastapi import APIRouter, Body, Depends, Path, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import SuccessResponse
from app.core.dependencies import db_getter

from app.plugin.module_cpx.auth.dependencies import ROLE_ADMIN, BizAuth, BusinessRole
from app.plugin.module_cpx.log.service import LogService, get_client_ip
from app.plugin.module_cpx.user.schema import (
    AuditorCreateSchema,
    AuditorUpdateSchema,
    DoctorCreateSchema,
    DoctorUpdateSchema,
    ResetPasswordSchema,
    UserStatusSchema,
)
from app.plugin.module_cpx.user.service import UserService

UserRouter = APIRouter(prefix="/user", tags=["医院用户管理"])


@UserRouter.get("/doctors", summary="分页查询医生")
async def get_doctor_list_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_ADMIN]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    page_no: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=10, ge=1, le=100, description="每页条数"),
    hospital_id: int | None = Query(default=None, description="医院ID"),
    keyword: str | None = Query(default=None, description="姓名/账号/工号"),
    phone: str | None = Query(default=None, description="手机号"),
    department: str | None = Query(default=None, description="科室"),
    title: str | None = Query(default=None, description="职称"),
    status: int | None = Query(default=None, description="账号状态"),
) -> JSONResponse:
    service = UserService(auth, db)
    result = await service.list_doctors(
        page_no=page_no,
        page_size=page_size,
        hospital_id=hospital_id,
        keyword=keyword,
        phone=phone,
        department=department,
        title=title,
        status=status,
    )
    return SuccessResponse(data=result, msg="查询医生列表成功")


@UserRouter.get("/auditors", summary="分页查询审核员")
async def get_auditor_list_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_ADMIN]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    page_no: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=10, ge=1, le=100, description="每页条数"),
    hospital_id: int | None = Query(default=None, description="医院ID"),
    keyword: str | None = Query(default=None, description="姓名/账号"),
    phone: str | None = Query(default=None, description="手机号"),
    status: int | None = Query(default=None, description="账号状态"),
) -> JSONResponse:
    service = UserService(auth, db)
    result = await service.list_auditors(
        page_no=page_no,
        page_size=page_size,
        hospital_id=hospital_id,
        keyword=keyword,
        phone=phone,
        status=status,
    )
    return SuccessResponse(data=result, msg="查询审核员列表成功")


@UserRouter.get("/detail/{id}", summary="获取用户详情")
async def get_user_detail_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_ADMIN]))],
    id: Annotated[int, Path(description="用户ID")],
    db: Annotated[AsyncSession, Depends(db_getter)],
) -> JSONResponse:
    service = UserService(auth, db)
    result = await service.detail(id=id)
    return SuccessResponse(data=result, msg="获取用户详情成功")


@UserRouter.post("/doctor", summary="新增医生")
async def create_doctor_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_ADMIN]))],
    data: Annotated[DoctorCreateSchema, Body(description="新增参数")],
    db: Annotated[AsyncSession, Depends(db_getter)],
    request: Request,
) -> JSONResponse:
    service = UserService(auth, db)
    result = await service.create_doctor(data=data)
    await LogService.create(
        db,
        user_id=auth.user.id,
        module="医院人员管理",
        operation="新增医生",
        description=f"新增医生：{result['real_name']}（{result['username']}）",
        ip_address=get_client_ip(request),
    )
    return SuccessResponse(data=result, msg="新增医生成功")


@UserRouter.post("/auditor", summary="新增审核员")
async def create_auditor_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_ADMIN]))],
    data: Annotated[AuditorCreateSchema, Body(description="新增参数")],
    db: Annotated[AsyncSession, Depends(db_getter)],
    request: Request,
) -> JSONResponse:
    service = UserService(auth, db)
    result = await service.create_auditor(data=data)
    await LogService.create(
        db,
        user_id=auth.user.id,
        module="医院人员管理",
        operation="新增审核员",
        description=f"新增审核员：{result['real_name']}（{result['username']}）",
        ip_address=get_client_ip(request),
    )
    return SuccessResponse(data=result, msg="新增审核员成功")


@UserRouter.put("/doctor/{id}", summary="修改医生")
async def update_doctor_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_ADMIN]))],
    id: Annotated[int, Path(description="用户ID")],
    data: Annotated[DoctorUpdateSchema, Body(description="修改参数")],
    db: Annotated[AsyncSession, Depends(db_getter)],
    request: Request,
) -> JSONResponse:
    service = UserService(auth, db)
    result = await service.update_doctor(id=id, data=data)
    await LogService.create(
        db,
        user_id=auth.user.id,
        module="医院人员管理",
        operation="修改医生",
        description=f"修改医生：{result['username']}",
        ip_address=get_client_ip(request),
    )
    return SuccessResponse(data=result, msg="修改医生成功")


@UserRouter.put("/auditor/{id}", summary="修改审核员")
async def update_auditor_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_ADMIN]))],
    id: Annotated[int, Path(description="用户ID")],
    data: Annotated[AuditorUpdateSchema, Body(description="修改参数")],
    db: Annotated[AsyncSession, Depends(db_getter)],
    request: Request,
) -> JSONResponse:
    service = UserService(auth, db)
    result = await service.update_auditor(id=id, data=data)
    await LogService.create(
        db,
        user_id=auth.user.id,
        module="医院人员管理",
        operation="修改审核员",
        description=f"修改审核员：{result['username']}",
        ip_address=get_client_ip(request),
    )
    return SuccessResponse(data=result, msg="修改审核员成功")


@UserRouter.patch("/status/batch", summary="批量启用/禁用用户")
async def set_user_status_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_ADMIN]))],
    data: Annotated[UserStatusSchema, Body(description="状态设置")],
    db: Annotated[AsyncSession, Depends(db_getter)],
    request: Request,
) -> JSONResponse:
    service = UserService(auth, db)
    await service.set_status(ids=data.ids, status=data.status)
    await LogService.create(
        db,
        user_id=auth.user.id,
        module="医院人员管理",
        operation="启用" if data.status == 1 else "禁用",
        description=f"用户ID {data.ids} 状态改为 {data.status}",
        ip_address=get_client_ip(request),
    )
    return SuccessResponse(msg="修改用户状态成功")


@UserRouter.put("/password/{id}", summary="重置密码")
async def reset_password_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_ADMIN]))],
    id: Annotated[int, Path(description="用户ID")],
    data: Annotated[ResetPasswordSchema, Body(description="新密码")],
    db: Annotated[AsyncSession, Depends(db_getter)],
    request: Request,
) -> JSONResponse:
    service = UserService(auth, db)
    await service.reset_password(id=id, password=data.password)
    await LogService.create(
        db,
        user_id=auth.user.id,
        module="医院人员管理",
        operation="重置密码",
        description=f"重置用户ID {id} 密码",
        ip_address=get_client_ip(request),
    )
    return SuccessResponse(msg="重置密码成功")
