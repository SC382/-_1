# -*- coding: utf-8 -*-
"""数据统计路由 /cpx/stats/*"""

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import SuccessResponse
from app.core.dependencies import db_getter

from app.plugin.module_cpx.auth.dependencies import ROLE_ADMIN, BizAuth, BusinessRole
from app.plugin.module_cpx.stats.service import StatsService

StatsRouter = APIRouter(prefix="/stats", tags=["数据统计"])


@StatsRouter.get("/dashboard", summary="数据驾驶舱统计")
async def get_dashboard_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_ADMIN]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
) -> JSONResponse:
    service = StatsService(auth, db)
    result = await service.dashboard()
    return SuccessResponse(data=result, msg="获取驾驶舱统计成功")


@StatsRouter.get("/analysis", summary="统计分析")
async def get_analysis_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_ADMIN]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
) -> JSONResponse:
    service = StatsService(auth, db)
    result = await service.analysis()
    return SuccessResponse(data=result, msg="获取统计分析成功")


@StatsRouter.get("/qc-detail/{key}", summary="质控指标病例明细（驾驶舱下钻）")
async def get_qc_detail_controller(
    key: str,
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_ADMIN]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
) -> JSONResponse:
    service = StatsService(auth, db)
    result = await service.qc_detail(key=key)
    return SuccessResponse(data=result, msg="获取质控明细成功")
