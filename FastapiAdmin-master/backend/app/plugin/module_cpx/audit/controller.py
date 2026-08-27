# -*- coding: utf-8 -*-
"""病例审核路由 /cpx/audit/*"""

from typing import Annotated

from fastapi import APIRouter, Body, Depends, Path, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import SuccessResponse
from app.core.dependencies import db_getter

from app.plugin.module_cpx.audit.schema import (
    AuditApproveSchema,
    AuditRecordUpdateSchema,
    AuditRejectSchema,
)
from app.plugin.module_cpx.audit.service import AuditService
from app.plugin.module_cpx.auth.dependencies import ROLE_AUDITOR, BizAuth, BusinessRole
from app.plugin.module_cpx.log.service import LogService, get_client_ip

AuditRouter = APIRouter(prefix="/audit", tags=["病例审核"])


@AuditRouter.get("/workbench", summary="审核工作台统计")
async def get_workbench_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_AUDITOR]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
) -> JSONResponse:
    service = AuditService(auth, db)
    result = await service.workbench()
    return SuccessResponse(data=result, msg="查询工作台统计成功")


@AuditRouter.get("/pending", summary="待审核病例列表")
async def get_pending_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_AUDITOR]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    page_no: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=10, ge=1, le=100, description="每页条数"),
    keyword: str | None = Query(default=None, description="患者姓名"),
    case_no: str | None = Query(default=None, description="病例编号（模糊）"),
) -> JSONResponse:
    service = AuditService(auth, db)
    result = await service.pending(page_no=page_no, page_size=page_size, keyword=keyword, case_no=case_no)
    return SuccessResponse(data=result, msg="查询待审核列表成功")


@AuditRouter.get("/detail/{case_id}", summary="病例审核详情（含校验提示）")
async def get_audit_detail_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_AUDITOR]))],
    case_id: Annotated[int, Path(description="病例ID")],
    db: Annotated[AsyncSession, Depends(db_getter)],
) -> JSONResponse:
    service = AuditService(auth, db)
    result = await service.detail(case_id=case_id)
    return SuccessResponse(data=result, msg="获取审核详情成功")


@AuditRouter.post("/approve", summary="审核通过")
async def approve_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_AUDITOR]))],
    data: Annotated[AuditApproveSchema, Body(description="审核参数")],
    db: Annotated[AsyncSession, Depends(db_getter)],
    request: Request,
) -> JSONResponse:
    service = AuditService(auth, db)
    result = await service.approve(case_id=data.case_id, audit_comment=data.audit_comment)
    await LogService.create(
        db,
        user_id=auth.user.id,
        module="病例审核",
        operation="审核通过",
        description=f"病例ID {data.case_id} 审核通过",
        ip_address=get_client_ip(request),
    )
    return SuccessResponse(data=result, msg="审核通过成功")


@AuditRouter.post("/reject", summary="审核驳回")
async def reject_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_AUDITOR]))],
    data: Annotated[AuditRejectSchema, Body(description="审核参数")],
    db: Annotated[AsyncSession, Depends(db_getter)],
    request: Request,
) -> JSONResponse:
    service = AuditService(auth, db)
    result = await service.reject(case_id=data.case_id, audit_comment=data.audit_comment)
    await LogService.create(
        db,
        user_id=auth.user.id,
        module="病例审核",
        operation="审核驳回",
        description=f"病例ID {data.case_id} 驳回：{data.audit_comment}",
        ip_address=get_client_ip(request),
    )
    return SuccessResponse(data=result, msg="审核驳回成功")


@AuditRouter.get("/history", summary="审核记录")
async def get_history_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_AUDITOR]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    page_no: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=10, ge=1, le=100, description="每页条数"),
    case_no: str | None = Query(default=None, description="病例编号（模糊）"),
) -> JSONResponse:
    service = AuditService(auth, db)
    result = await service.history(page_no=page_no, page_size=page_size, case_no=case_no)
    return SuccessResponse(data=result, msg="查询审核记录成功")


@AuditRouter.put("/record/{record_id}", summary="修改审核记录")
async def update_record_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_AUDITOR]))],
    record_id: Annotated[int, Path(description="审核记录ID")],
    data: Annotated[AuditRecordUpdateSchema, Body(description="修改参数")],
    db: Annotated[AsyncSession, Depends(db_getter)],
    request: Request,
) -> JSONResponse:
    service = AuditService(auth, db)
    result = await service.update_record(
        record_id=record_id,
        audit_result=data.audit_result,
        audit_comment=data.audit_comment,
    )
    await LogService.create(
        db,
        user_id=auth.user.id,
        module="病例审核",
        operation="修改审核",
        description=f"审核记录ID {record_id} 修改为：{'通过' if data.audit_result == 'pass' else '驳回'} {data.audit_comment or ''}",
        ip_address=get_client_ip(request),
    )
    return SuccessResponse(data=result, msg="修改审核记录成功")
