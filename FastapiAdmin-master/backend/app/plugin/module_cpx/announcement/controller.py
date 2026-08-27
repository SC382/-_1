# -*- coding: utf-8 -*-
"""公告管理路由 /cpx/announcement/*"""

from typing import Annotated

from fastapi import APIRouter, Body, Depends, Path, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import SuccessResponse
from app.core.dependencies import db_getter

from app.plugin.module_cpx.announcement.schema import AnnouncementCreateSchema, AnnouncementUpdateSchema
from app.plugin.module_cpx.announcement.service import AnnouncementService
from app.plugin.module_cpx.auth.dependencies import ROLE_ADMIN, ROLE_DOCTOR, BizAuth, BusinessRole
from app.plugin.module_cpx.log.service import LogService, get_client_ip

AnnouncementRouter = APIRouter(prefix="/announcement", tags=["公告管理"])


# ── Web 端管理（admin） ────────────────────────────────────────


@AnnouncementRouter.get("/list", summary="分页查询公告")
async def get_announcement_list_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_ADMIN]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    page_no: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=10, ge=1, le=100, description="每页条数"),
    keyword: str | None = Query(default=None, description="标题模糊查询"),
    status: str | None = Query(default=None, description="状态 draft/published/offline"),
    type: str | None = Query(default=None, description="类型 system/version/activity/notice"),
) -> JSONResponse:
    service = AnnouncementService(auth, db)
    result = await service.page(page_no=page_no, page_size=page_size, keyword=keyword, status=status, type_=type)
    return SuccessResponse(data=result, msg="查询公告列表成功")


@AnnouncementRouter.get("/detail/{id}", summary="获取公告详情")
async def get_announcement_detail_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_ADMIN]))],
    id: Annotated[int, Path(description="公告ID")],
    db: Annotated[AsyncSession, Depends(db_getter)],
) -> JSONResponse:
    service = AnnouncementService(auth, db)
    result = await service.detail(id=id)
    return SuccessResponse(data=result, msg="获取公告详情成功")


@AnnouncementRouter.post("/create", summary="新增公告")
async def create_announcement_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_ADMIN]))],
    data: Annotated[AnnouncementCreateSchema, Body(description="新增参数")],
    db: Annotated[AsyncSession, Depends(db_getter)],
    request: Request,
) -> JSONResponse:
    service = AnnouncementService(auth, db)
    result = await service.create(data=data)
    await LogService.create(
        db,
        user_id=auth.user.id,
        module="公告管理",
        operation="新增公告",
        description=f"新增公告：{result['title']}",
        ip_address=get_client_ip(request),
    )
    return SuccessResponse(data=result, msg="新增公告成功")


@AnnouncementRouter.put("/update/{id}", summary="修改公告")
async def update_announcement_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_ADMIN]))],
    id: Annotated[int, Path(description="公告ID")],
    data: Annotated[AnnouncementUpdateSchema, Body(description="修改参数")],
    db: Annotated[AsyncSession, Depends(db_getter)],
    request: Request,
) -> JSONResponse:
    service = AnnouncementService(auth, db)
    result = await service.update(id=id, data=data)
    await LogService.create(
        db,
        user_id=auth.user.id,
        module="公告管理",
        operation="修改公告",
        description=f"修改公告：{result['title']}",
        ip_address=get_client_ip(request),
    )
    return SuccessResponse(data=result, msg="修改公告成功")


@AnnouncementRouter.put("/publish/{id}", summary="发布公告")
async def publish_announcement_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_ADMIN]))],
    id: Annotated[int, Path(description="公告ID")],
    db: Annotated[AsyncSession, Depends(db_getter)],
    request: Request,
) -> JSONResponse:
    service = AnnouncementService(auth, db)
    result = await service.publish(id=id)
    await LogService.create(
        db,
        user_id=auth.user.id,
        module="公告管理",
        operation="发布公告",
        description=f"发布公告：{result['title']}",
        ip_address=get_client_ip(request),
    )
    return SuccessResponse(data=result, msg="发布公告成功")


@AnnouncementRouter.put("/offline/{id}", summary="下线公告")
async def offline_announcement_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_ADMIN]))],
    id: Annotated[int, Path(description="公告ID")],
    db: Annotated[AsyncSession, Depends(db_getter)],
    request: Request,
) -> JSONResponse:
    service = AnnouncementService(auth, db)
    result = await service.offline(id=id)
    await LogService.create(
        db,
        user_id=auth.user.id,
        module="公告管理",
        operation="下线公告",
        description=f"下线公告：{result['title']}",
        ip_address=get_client_ip(request),
    )
    return SuccessResponse(data=result, msg="已下线公告")


@AnnouncementRouter.delete("/{id}", summary="删除公告")
async def delete_announcement_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_ADMIN]))],
    id: Annotated[int, Path(description="公告ID")],
    db: Annotated[AsyncSession, Depends(db_getter)],
    request: Request,
) -> JSONResponse:
    service = AnnouncementService(auth, db)
    result = await service.delete(id=id)
    await LogService.create(
        db,
        user_id=auth.user.id,
        module="公告管理",
        operation="删除公告",
        description=f"删除公告：{result['title']}",
        ip_address=get_client_ip(request),
    )
    return SuccessResponse(data=result, msg="公告已删除")


# ── App 端公开（已登录医生可访问） ─────────────────────────────


@AnnouncementRouter.get("/active", summary="App 端：当前生效公告列表")
async def active_announcements_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_DOCTOR]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    limit: int = Query(default=10, ge=1, le=20, description="返回条数"),
) -> JSONResponse:
    service = AnnouncementService(auth, db)
    items = await service.active_list(limit=limit)
    return SuccessResponse(data=items, msg="查询成功")


@AnnouncementRouter.get("/active/{id}", summary="App 端：公告详情")
async def active_announcement_detail_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_DOCTOR]))],
    id: Annotated[int, Path(description="公告ID")],
    db: Annotated[AsyncSession, Depends(db_getter)],
) -> JSONResponse:
    service = AnnouncementService(auth, db)
    result = await service.active_detail(id=id)
    return SuccessResponse(data=result, msg="查询成功")