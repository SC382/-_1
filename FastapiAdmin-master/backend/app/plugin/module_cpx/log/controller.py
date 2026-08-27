# -*- coding: utf-8 -*-
"""业务操作日志路由 /cpx/log/*（仅管理员）"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import SuccessResponse
from app.core.dependencies import db_getter

from app.plugin.module_cpx.auth.dependencies import ROLE_ADMIN, BizAuth, BusinessRole
from app.plugin.module_cpx.log.service import LogService

LogRouter = APIRouter(prefix="/log", tags=["系统日志"])


@LogRouter.get("/roles", summary="用户角色选项（日志筛选）")
async def get_log_roles_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_ADMIN]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
) -> JSONResponse:
    from sqlalchemy import select

    from app.plugin.module_cpx.models import CpxRoleModel

    result = await db.execute(select(CpxRoleModel).order_by(CpxRoleModel.id.asc()))
    items = [{"id": r.id, "role_name": r.role_name} for r in result.scalars().all()]
    return SuccessResponse(data=items, msg="查询角色选项成功")


@LogRouter.get("/list", summary="分页查询系统日志")
async def get_log_list_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_ADMIN]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    request: Request,
    page_no: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=10, ge=1, le=100, description="每页条数"),
    user_id: int | None = Query(default=None, description="操作用户ID"),
    user_name: str | None = Query(default=None, description="操作用户姓名（模糊）"),
    role_id: int | None = Query(default=None, description="用户角色ID"),
    hospital_id: int | None = Query(default=None, description="所属医院ID"),
    module: str | None = Query(default=None, description="模块"),
    operation: str | None = Query(default=None, description="操作类型"),
    start_time: str | None = Query(default=None, description="开始时间 yyyy-MM-dd"),
    end_time: str | None = Query(default=None, description="结束时间 yyyy-MM-dd"),
) -> JSONResponse:
    result = await LogService.page(
        db,
        page_no=page_no,
        page_size=page_size,
        user_id=user_id,
        user_name=user_name,
        role_id=role_id,
        hospital_id=hospital_id,
        module=module,
        operation=operation,
        start_time=start_time,
        end_time=end_time,
    )
    return SuccessResponse(data=result, msg="查询系统日志成功")
