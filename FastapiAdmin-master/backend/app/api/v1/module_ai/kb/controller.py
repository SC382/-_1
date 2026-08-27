# -*- coding: utf-8 -*-
"""AI 助手知识库问答接口 /api/v1/ai/kb/*"""
from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, Security
from fastapi.responses import JSONResponse

from app.common.response import ResponseSchema, SuccessResponse
from app.core.base_schema import AuthSchema
from app.core.dependencies import AuthPermission
from app.core.exceptions import CustomException
from app.core.router_class import OperationLogRoute

from .service import KbService

KbRouter = APIRouter(route_class=OperationLogRoute, prefix="/kb", tags=["AI知识库"])


@KbRouter.post("/ask", summary="知识库问答（基于胸痛中心认证标准 PDF）", response_model=ResponseSchema[dict[str, Any]])
async def kb_ask_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_ai:chat:query"]))],
    body: Annotated[dict, Body(description="{\"question\": \"问题\"}")],
) -> JSONResponse:
    question = str(body.get("question", "")).strip()
    if not question:
        raise CustomException(msg="问题不能为空")
    result = await KbService(auth).ask(question)
    return SuccessResponse(data=result, msg="知识库回答生成成功")


@KbRouter.get("/status", summary="知识库状态（已导入文件与分片数）", response_model=ResponseSchema[dict[str, Any]])
async def kb_status_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_ai:chat:query"]))],
) -> JSONResponse:
    result = await KbService(auth).status()
    return SuccessResponse(data=result, msg="查询知识库状态成功")
