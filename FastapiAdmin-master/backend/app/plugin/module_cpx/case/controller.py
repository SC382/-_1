# -*- coding: utf-8 -*-
"""病例管理路由 /cpx/case/*"""

from typing import Annotated

from fastapi import APIRouter, Body, Depends, Path, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import SuccessResponse
from app.core.dependencies import db_getter

from app.plugin.module_cpx.auth.dependencies import ROLE_ADMIN, BizAuth, BusinessRole
from app.plugin.module_cpx.case.schema import CaseCreateSchema, CaseUpdateSchema
from app.plugin.module_cpx.case.service import CaseService
from app.plugin.module_cpx.log.service import LogService, get_client_ip

CaseRouter = APIRouter(prefix="/case", tags=["病例管理"])


@CaseRouter.get("/list", summary="分页查询病例")
async def get_case_list_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_ADMIN]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    page_no: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=10, ge=1, le=100, description="每页条数"),
    hospital_id: int | None = Query(default=None, description="医院ID"),
    doctor_id: int | None = Query(default=None, description="医生ID"),
    case_no: str | None = Query(default=None, description="病例编号（完整精确/片段模糊）"),
    patient_name: str | None = Query(default=None, description="患者姓名（模糊）"),
    doctor_name: str | None = Query(default=None, description="医生姓名（模糊）"),
    status: str | None = Query(default=None, description="状态"),
    start_time: str | None = Query(default=None, description="开始时间 yyyy-MM-dd"),
    end_time: str | None = Query(default=None, description="结束时间 yyyy-MM-dd"),
) -> JSONResponse:
    service = CaseService(auth, db)
    result = await service.page(
        page_no=page_no,
        page_size=page_size,
        hospital_id=hospital_id,
        doctor_id=doctor_id,
        case_no=case_no,
        patient_name=patient_name,
        doctor_name=doctor_name,
        status=status,
        start_time=start_time,
        end_time=end_time,
    )
    return SuccessResponse(data=result, msg="查询病例列表成功")


@CaseRouter.get("/detail/{id}", summary="获取病例详情")
async def get_case_detail_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_ADMIN]))],
    id: Annotated[int, Path(description="病例ID")],
    db: Annotated[AsyncSession, Depends(db_getter)],
) -> JSONResponse:
    service = CaseService(auth, db)
    result = await service.detail(id=id)
    return SuccessResponse(data=result, msg="获取病例详情成功")


@CaseRouter.post("/create", summary="新增病例（测试/联调）")
async def create_case_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_ADMIN]))],
    data: Annotated[CaseCreateSchema, Body(description="新增参数")],
    db: Annotated[AsyncSession, Depends(db_getter)],
    request: Request,
) -> JSONResponse:
    service = CaseService(auth, db)
    result = await service.create(data=data)
    await LogService.create(
        db,
        user_id=auth.user.id,
        module="病例管理",
        operation="新增病例",
        description=f"新增病例：{data.patient_name or '未命名'}",
        ip_address=get_client_ip(request),
    )
    return SuccessResponse(data=result, msg="新增病例成功")


@CaseRouter.post("/submit/{id}", summary="提交病例（草稿/驳回 → 待审核）")
async def submit_case_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_ADMIN]))],
    id: Annotated[int, Path(description="病例ID")],
    db: Annotated[AsyncSession, Depends(db_getter)],
) -> JSONResponse:
    service = CaseService(auth, db)
    result = await service.submit(id=id)
    return SuccessResponse(data=result, msg="提交病例成功")


@CaseRouter.put("/{id}", summary="更新病例基础信息（web 与 APP 互通）")
async def update_case_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_ADMIN]))],
    id: Annotated[int, Path(description="病例ID")],
    data: Annotated[CaseUpdateSchema, Body(description="更新参数（仅传入字段生效）")],
    db: Annotated[AsyncSession, Depends(db_getter)],
    request: Request,
) -> JSONResponse:
    service = CaseService(auth, db)
    result = await service.update(id=id, data=data)
    await LogService.create(
        db,
        user_id=auth.user.id,
        module="病例管理",
        operation="更新病例基础信息",
        description=f"更新病例 {id}：电话={data.phone or '-'}",
        ip_address=get_client_ip(request),
    )
    return SuccessResponse(data=result, msg="更新病例成功")


@CaseRouter.delete("/{id}", summary="删除病例（级联删除详情/审核/随访/心电）")
async def delete_case_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_ADMIN]))],
    id: Annotated[int, Path(description="病例ID")],
    db: Annotated[AsyncSession, Depends(db_getter)],
    request: Request,
) -> JSONResponse:
    service = CaseService(auth, db)
    result = await service.delete(id=id)
    await LogService.create(
        db,
        user_id=auth.user.id,
        module="病例管理",
        operation="删除病例",
        description=f"删除病例 {result['case_no']}（{result['patient_name']}），连带 {result['deleted']} 条关联记录",
        ip_address=get_client_ip(request),
    )
    return SuccessResponse(data=result, msg="病例已删除")
