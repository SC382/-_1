# -*- coding: utf-8 -*-
"""医院管理路由 /cpx/hospital/*"""

from typing import Annotated

from fastapi import APIRouter, Body, Depends, Path, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import SuccessResponse
from app.core.dependencies import db_getter

from app.plugin.module_cpx.auth.dependencies import (
    ROLE_ADMIN,
    ROLE_AUDITOR,
    BizAuth,
    BusinessRole,
)
from app.plugin.module_cpx.hospital.schema import (
    HospitalCreateSchema,
    HospitalStatusSchema,
    HospitalUpdateSchema,
)
from app.plugin.module_cpx.hospital.service import HospitalService
from app.plugin.module_cpx.log.service import LogService, get_client_ip

HospitalRouter = APIRouter(prefix="/hospital", tags=["医院管理"])


@HospitalRouter.get("/list", summary="分页查询医院")
async def get_hospital_list_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_ADMIN]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    request: Request,
    page_no: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=10, ge=1, le=100, description="每页条数"),
    hospital_name: str | None = Query(default=None, description="医院名称"),
    hospital_level: str | None = Query(default=None, description="医院等级"),
    province: str | None = Query(default=None, description="省份/地区"),
    status: int | None = Query(default=None, description="状态"),
) -> JSONResponse:
    service = HospitalService(auth, db)
    result = await service.page(
        page_no=page_no,
        page_size=page_size,
        search={
            "hospital_name": hospital_name,
            "hospital_level": hospital_level,
            "province": province,
            "status": status,
        },
    )
    return SuccessResponse(data=result, msg="查询医院列表成功")


@HospitalRouter.get("/all", summary="全部启用医院（下拉选项）")
async def get_hospital_all_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_ADMIN, ROLE_AUDITOR]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    request: Request,
) -> JSONResponse:
    from sqlalchemy import select

    from app.plugin.module_cpx.models import HospitalModel

    result = await db.execute(
        select(HospitalModel).where(HospitalModel.status == 1).order_by(HospitalModel.id.asc())
    )
    rows = result.scalars().all()
    items = [{"id": h.id, "hospital_name": h.hospital_name} for h in rows]
    return SuccessResponse(data=items, msg="查询医院选项成功")


@HospitalRouter.get("/detail/{id}", summary="获取医院详情")
async def get_hospital_detail_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_ADMIN]))],
    id: Annotated[int, Path(description="医院ID")],
    db: Annotated[AsyncSession, Depends(db_getter)],
) -> JSONResponse:
    service = HospitalService(auth, db)
    result = await service.detail(id=id)
    return SuccessResponse(data=result, msg="获取医院详情成功")


@HospitalRouter.post("/create", summary="新增医院")
async def create_hospital_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_ADMIN]))],
    data: Annotated[HospitalCreateSchema, Body(description="新增参数")],
    db: Annotated[AsyncSession, Depends(db_getter)],
    request: Request,
) -> JSONResponse:
    service = HospitalService(auth, db)
    result = await service.create(data=data)
    await LogService.create(
        db,
        user_id=auth.user.id,
        module="医院管理",
        operation="新增医院",
        description=f"新增医院：{result['hospital_name']}",
        ip_address=get_client_ip(request),
    )
    return SuccessResponse(data=result, msg="新增医院成功")


@HospitalRouter.put("/update/{id}", summary="修改医院")
async def update_hospital_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_ADMIN]))],
    id: Annotated[int, Path(description="医院ID")],
    data: Annotated[HospitalUpdateSchema, Body(description="修改参数")],
    db: Annotated[AsyncSession, Depends(db_getter)],
    request: Request,
) -> JSONResponse:
    service = HospitalService(auth, db)
    result = await service.update(id=id, data=data)
    await LogService.create(
        db,
        user_id=auth.user.id,
        module="医院管理",
        operation="修改医院",
        description=f"修改医院：{result['hospital_name']}",
        ip_address=get_client_ip(request),
    )
    return SuccessResponse(data=result, msg="修改医院成功")


@HospitalRouter.patch("/status/batch", summary="批量启用/禁用医院")
async def set_hospital_status_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_ADMIN]))],
    data: Annotated[HospitalStatusSchema, Body(description="状态设置")],
    db: Annotated[AsyncSession, Depends(db_getter)],
    request: Request,
) -> JSONResponse:
    service = HospitalService(auth, db)
    await service.set_status(ids=data.ids, status=data.status)
    await LogService.create(
        db,
        user_id=auth.user.id,
        module="医院管理",
        operation="启用" if data.status == 1 else "禁用",
        description=f"医院ID {data.ids} 状态改为 {data.status}",
        ip_address=get_client_ip(request),
    )
    return SuccessResponse(msg="修改医院状态成功")
