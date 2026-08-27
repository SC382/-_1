# -*- coding: utf-8 -*-
"""动态模板管理路由 /cpx/template/*"""

from typing import Annotated

from fastapi import APIRouter, Body, Depends, Path, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import SuccessResponse
from app.core.dependencies import db_getter

from app.plugin.module_cpx.auth.dependencies import ROLE_ADMIN, ROLE_AUDITOR, BizAuth, BusinessRole
from app.plugin.module_cpx.log.service import LogService, get_client_ip
from app.plugin.module_cpx.template.schema import (
    TemplateCreateSchema,
    TemplateFieldCreateSchema,
    TemplateFieldUpdateSchema,
    TemplateUpdateSchema,
)
from app.plugin.module_cpx.template.service import TemplateService

TemplateRouter = APIRouter(prefix="/template", tags=["动态模板管理"])


@TemplateRouter.get("/list", summary="分页查询模板")
async def get_template_list_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_ADMIN]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    page_no: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=10, ge=1, le=100, description="每页条数"),
    keyword: str | None = Query(default=None, description="模板名称"),
    status: int | None = Query(default=None, description="使用状态"),
) -> JSONResponse:
    service = TemplateService(auth, db)
    result = await service.page(page_no=page_no, page_size=page_size, keyword=keyword, status=status)
    return SuccessResponse(data=result, msg="查询模板列表成功")


@TemplateRouter.get("/all", summary="全部启用模板（下拉选项）")
async def get_template_all_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_ADMIN, ROLE_AUDITOR]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
) -> JSONResponse:
    service = TemplateService(auth, db)
    result = await service.all_active()
    return SuccessResponse(data=result, msg="查询模板选项成功")


@TemplateRouter.get("/detail/{id}", summary="获取模板详情（含字段）")
async def get_template_detail_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_ADMIN]))],
    id: Annotated[int, Path(description="模板ID")],
    db: Annotated[AsyncSession, Depends(db_getter)],
) -> JSONResponse:
    service = TemplateService(auth, db)
    result = await service.detail(id=id)
    return SuccessResponse(data=result, msg="获取模板详情成功")


@TemplateRouter.post("/create", summary="新增模板")
async def create_template_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_ADMIN]))],
    data: Annotated[TemplateCreateSchema, Body(description="新增参数")],
    db: Annotated[AsyncSession, Depends(db_getter)],
    request: Request,
) -> JSONResponse:
    service = TemplateService(auth, db)
    result = await service.create(data=data)
    await LogService.create(
        db,
        user_id=auth.user.id,
        module="模板管理",
        operation="新增模板",
        description=f"新增模板：{result['template_name']}",
        ip_address=get_client_ip(request),
    )
    return SuccessResponse(data=result, msg="新增模板成功")


@TemplateRouter.put("/update/{id}", summary="修改模板")
async def update_template_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_ADMIN]))],
    id: Annotated[int, Path(description="模板ID")],
    data: Annotated[TemplateUpdateSchema, Body(description="修改参数")],
    db: Annotated[AsyncSession, Depends(db_getter)],
    request: Request,
) -> JSONResponse:
    service = TemplateService(auth, db)
    result = await service.update(id=id, data=data)
    await LogService.create(
        db,
        user_id=auth.user.id,
        module="模板管理",
        operation="修改模板",
        description=f"修改模板：{result['template_name']}",
        ip_address=get_client_ip(request),
    )
    return SuccessResponse(data=result, msg="修改模板成功")


@TemplateRouter.put("/publish/{id}", summary="发布模板")
async def publish_template_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_ADMIN]))],
    id: Annotated[int, Path(description="模板ID")],
    db: Annotated[AsyncSession, Depends(db_getter)],
    request: Request,
) -> JSONResponse:
    service = TemplateService(auth, db)
    result = await service.publish(id=id)
    await LogService.create(
        db,
        user_id=auth.user.id,
        module="模板管理",
        operation="发布模板",
        description=f"发布模板：{result['template_name']}",
        ip_address=get_client_ip(request),
    )
    return SuccessResponse(data=result, msg="发布模板成功")


@TemplateRouter.put("/unpublish/{id}", summary="取消发布（仅未被病例使用时允许）")
async def unpublish_template_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_ADMIN]))],
    id: Annotated[int, Path(description="模板ID")],
    db: Annotated[AsyncSession, Depends(db_getter)],
    request: Request,
) -> JSONResponse:
    service = TemplateService(auth, db)
    result = await service.unpublish(id=id)
    await LogService.create(
        db,
        user_id=auth.user.id,
        module="模板管理",
        operation="取消发布",
        description=f"取消发布模板：{result['template_name']}",
        ip_address=get_client_ip(request),
    )
    return SuccessResponse(data=result, msg="已取消发布，模板回退为草稿")


@TemplateRouter.post("/fields", summary="添加模板字段")
async def add_template_field_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_ADMIN]))],
    data: Annotated[TemplateFieldCreateSchema, Body(description="字段参数")],
    db: Annotated[AsyncSession, Depends(db_getter)],
    request: Request,
) -> JSONResponse:
    service = TemplateService(auth, db)
    result = await service.add_field(data=data)
    await LogService.create(
        db,
        user_id=auth.user.id,
        module="模板管理",
        operation="添加字段",
        description=f"模板ID {data.template_id} 添加字段：{result['field_name']}",
        ip_address=get_client_ip(request),
    )
    return SuccessResponse(data=result, msg="添加字段成功")


@TemplateRouter.put("/field/{id}", summary="修改模板字段")
async def update_template_field_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_ADMIN]))],
    id: Annotated[int, Path(description="字段ID")],
    data: Annotated[TemplateFieldUpdateSchema, Body(description="字段参数")],
    db: Annotated[AsyncSession, Depends(db_getter)],
    request: Request,
) -> JSONResponse:
    service = TemplateService(auth, db)
    result = await service.update_field(id=id, data=data)
    await LogService.create(
        db,
        user_id=auth.user.id,
        module="模板管理",
        operation="修改字段",
        description=f"修改字段：{result['field_name']}",
        ip_address=get_client_ip(request),
    )
    return SuccessResponse(data=result, msg="修改字段成功")


@TemplateRouter.delete("/field/{id}", summary="删除模板字段")
async def delete_template_field_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_ADMIN]))],
    id: Annotated[int, Path(description="字段ID")],
    db: Annotated[AsyncSession, Depends(db_getter)],
    request: Request,
) -> JSONResponse:
    service = TemplateService(auth, db)
    await service.delete_field(id=id)
    await LogService.create(
        db,
        user_id=auth.user.id,
        module="模板管理",
        operation="删除字段",
        description=f"删除字段ID {id}",
        ip_address=get_client_ip(request),
    )
    return SuccessResponse(msg="删除字段成功")


@TemplateRouter.delete("/{id}", summary="删除模板（未被病例使用时允许）")
async def delete_template_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_ADMIN]))],
    id: Annotated[int, Path(description="模板ID")],
    db: Annotated[AsyncSession, Depends(db_getter)],
    request: Request,
) -> JSONResponse:
    service = TemplateService(auth, db)
    result = await service.delete(id=id)
    await LogService.create(
        db,
        user_id=auth.user.id,
        module="模板管理",
        operation="删除模板",
        description=f"删除模板：{result['template_name']}（连带 {result['deleted_fields']} 个字段）",
        ip_address=get_client_ip(request),
    )
    return SuccessResponse(data=result, msg="模板已删除")


@TemplateRouter.post("/copy-standard/{template_id}", summary="复制标准模板（覆盖现有字段）")
async def copy_standard_template_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_ADMIN]))],
    template_id: Annotated[int, Path(description="目标模板ID")],
    db: Annotated[AsyncSession, Depends(db_getter)],
    request: Request,
) -> JSONResponse:
    service = TemplateService(auth, db)
    result = await service.copy_standard(template_id=template_id)
    await LogService.create(
        db,
        user_id=auth.user.id,
        module="模板管理",
        operation="复制标准模板",
        description=f"向模板 {template_id} 复制标准字段集（{result['copied']} 个字段，{result['tabs']} 个分类）",
        ip_address=get_client_ip(request),
    )
    return SuccessResponse(data=result, msg=f"已复制 {result['copied']} 个标准字段")


@TemplateRouter.post("/tab-rename", summary="重命名模板内某分类（批量更新）")
async def rename_tab_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_ADMIN]))],
    body: Annotated[dict, Body(description="template_id / old_name / new_name / tab_order?")],
    db: Annotated[AsyncSession, Depends(db_getter)],
    request: Request,
) -> JSONResponse:
    service = TemplateService(auth, db)
    result = await service.rename_tab(
        template_id=int(body["template_id"]),
        old_name=str(body["old_name"]),
        new_name=str(body["new_name"]),
        tab_order=body.get("tab_order"),
    )
    await LogService.create(
        db,
        user_id=auth.user.id,
        module="模板管理",
        operation="重命名分类",
        description=f"模板 {result['template_id']} 分类「{result['old_name']}」→「{result['new_name']}」（{result['count']} 个字段）",
        ip_address=get_client_ip(request),
    )
    return SuccessResponse(data=result, msg=f"已重命名分类（{result['count']} 个字段）")


@TemplateRouter.post("/tab-delete", summary="删除模板内某分类及其所有字段")
async def delete_tab_controller(
    auth: Annotated[BizAuth, Depends(BusinessRole([ROLE_ADMIN]))],
    body: Annotated[dict, Body(description="template_id / tab_name")],
    db: Annotated[AsyncSession, Depends(db_getter)],
    request: Request,
) -> JSONResponse:
    service = TemplateService(auth, db)
    result = await service.delete_tab(
        template_id=int(body["template_id"]),
        tab_name=str(body["tab_name"]),
    )
    await LogService.create(
        db,
        user_id=auth.user.id,
        module="模板管理",
        operation="删除分类",
        description=f"模板 {result['template_id']} 删除分类「{result['tab_name']}」（{result['deleted']} 个字段）",
        ip_address=get_client_ip(request),
    )
    return SuccessResponse(data=result, msg=f"已删除分类（{result['deleted']} 个字段）")
