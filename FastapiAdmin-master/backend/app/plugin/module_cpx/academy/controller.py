# -*- coding: utf-8 -*-
"""胸痛学院路由：管理端 /cpx/academy/*，医生端 /cpx/academy/doctor/*"""

from typing import Annotated

from fastapi import APIRouter, Body, Depends, File, Path, Query, Request, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import SuccessResponse
from app.core.dependencies import db_getter

from app.plugin.module_cpx.academy.schema import AcademyCreateSchema, AcademyUpdateSchema
from app.plugin.module_cpx.academy.service import AcademyService
from app.plugin.module_cpx.auth.dependencies import ROLE_ADMIN, ROLE_DOCTOR, BizAuth, BusinessRole
from app.plugin.module_cpx.log.service import LogService, get_client_ip

AcademyRouter = APIRouter(prefix="/academy", tags=["胸痛学院"])


# ── 管理端（仅管理员） ─────────────────────────────────

@AcademyRouter.get("/list", summary="分页查询学院内容")
async def academy_list_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_ADMIN]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    page_no: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    keyword: str | None = Query(default=None, description="标题关键字"),
    content_type: str | None = Query(default=None, description="类型"),
    category: str | None = Query(default=None, description="分类"),
    published: int | None = Query(default=None, description="发布状态"),
) -> JSONResponse:
    service = AcademyService(auth, db)
    result = await service.page(
        page_no=page_no, page_size=page_size, keyword=keyword,
        content_type=content_type, category=category, published=published,
    )
    return SuccessResponse(data=result, msg="查询成功")


@AcademyRouter.get("/detail/{id}", summary="学院内容详情")
async def academy_detail_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_ADMIN]))],
    id: Annotated[int, Path(description="内容ID")],
    db: Annotated[AsyncSession, Depends(db_getter)],
) -> JSONResponse:
    result = await AcademyService(auth, db).detail(id=id)
    return SuccessResponse(data=result, msg="查询成功")


@AcademyRouter.post("/create", summary="新增学院内容")
async def academy_create_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_ADMIN]))],
    data: Annotated[AcademyCreateSchema, Body(description="新增参数")],
    db: Annotated[AsyncSession, Depends(db_getter)],
    request: Request,
) -> JSONResponse:
    service = AcademyService(auth, db)
    result = await service.create(data=data)
    await LogService.create(
        db, user_id=auth.user.id, module="胸痛学院", operation="新增内容",
        description=f"新增学院内容：{result['title']}", ip_address=get_client_ip(request),
    )
    return SuccessResponse(data=result, msg="新增成功")


@AcademyRouter.put("/update/{id}", summary="修改学院内容")
async def academy_update_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_ADMIN]))],
    id: Annotated[int, Path(description="内容ID")],
    data: Annotated[AcademyUpdateSchema, Body(description="修改参数（仅传入字段生效）")],
    db: Annotated[AsyncSession, Depends(db_getter)],
    request: Request,
) -> JSONResponse:
    service = AcademyService(auth, db)
    result = await service.update(id=id, data=data)
    await LogService.create(
        db, user_id=auth.user.id, module="胸痛学院", operation="修改内容",
        description=f"修改学院内容：{result['title']}", ip_address=get_client_ip(request),
    )
    return SuccessResponse(data=result, msg="修改成功")


@AcademyRouter.delete("/{id}", summary="删除学院内容")
async def academy_delete_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_ADMIN]))],
    id: Annotated[int, Path(description="内容ID")],
    db: Annotated[AsyncSession, Depends(db_getter)],
    request: Request,
) -> JSONResponse:
    service = AcademyService(auth, db)
    result = await service.delete(id=id)
    await LogService.create(
        db, user_id=auth.user.id, module="胸痛学院", operation="删除内容",
        description=f"删除学院内容：{result['title']}", ip_address=get_client_ip(request),
    )
    return SuccessResponse(data=result, msg="删除成功")


@AcademyRouter.put("/publish/{id}", summary="发布 / 下架切换")
async def academy_publish_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_ADMIN]))],
    id: Annotated[int, Path(description="内容ID")],
    db: Annotated[AsyncSession, Depends(db_getter)],
    request: Request,
) -> JSONResponse:
    service = AcademyService(auth, db)
    result = await service.toggle_publish(id=id)
    action = "发布" if result["published"] == 1 else "下架"
    await LogService.create(
        db, user_id=auth.user.id, module="胸痛学院", operation=action,
        description=f"{action}学院内容：{result['title']}", ip_address=get_client_ip(request),
    )
    return SuccessResponse(data=result, msg=f"{action}成功")


@AcademyRouter.post("/upload", summary="上传学习资源文件")
async def academy_upload_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_ADMIN]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    request: Request,
    file: UploadFile = File(..., description="学习资源文件（视频/PPT/Word/PDF/Excel/图片/文本）"),
) -> JSONResponse:
    service = AcademyService(auth, db)
    result = await service.upload(file)
    await LogService.create(
        db, user_id=auth.user.id, module="胸痛学院", operation="上传文件",
        description=f"上传文件：{result['file_name']}（{result['content_type']}）", ip_address=get_client_ip(request),
    )
    return SuccessResponse(data=result, msg="上传成功")


# ── 医生端（只读） ─────────────────────────────────────

@AcademyRouter.get("/doctor/list", summary="医生端：已发布学院内容列表")
async def academy_doctor_list_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_DOCTOR]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    page_no: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    content_type: str | None = Query(default=None, description="类型"),
    category: str | None = Query(default=None, description="分类"),
) -> JSONResponse:
    result = await AcademyService(auth, db).doctor_list(
        page_no=page_no, page_size=page_size, content_type=content_type, category=category
    )
    return SuccessResponse(data=result, msg="查询成功")


@AcademyRouter.get("/doctor/detail/{id}", summary="医生端：学院内容详情（浏览量+1）")
async def academy_doctor_detail_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_DOCTOR]))],
    id: Annotated[int, Path(description="内容ID")],
    db: Annotated[AsyncSession, Depends(db_getter)],
) -> JSONResponse:
    result = await AcademyService(auth, db).doctor_detail(id=id)
    return SuccessResponse(data=result, msg="查询成功")
