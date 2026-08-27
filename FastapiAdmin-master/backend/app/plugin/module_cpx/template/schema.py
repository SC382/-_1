# -*- coding: utf-8 -*-
"""动态模板管理 Schema"""

from typing import Any

from pydantic import BaseModel, Field


class TemplateCreateSchema(BaseModel):
    """新增模板"""
    template_name: str = Field(..., max_length=100, description="模板名称")
    version: str | None = Field(default=None, max_length=20, description="版本号")
    status: int = Field(default=1, ge=0, le=1, description="状态 1启用 0停用")


class TemplateUpdateSchema(BaseModel):
    """修改模板"""
    template_name: str | None = Field(default=None, max_length=100, description="模板名称")
    version: str | None = Field(default=None, max_length=20, description="版本号")
    status: int | None = Field(default=None, ge=0, le=1, description="状态 1启用 0停用")


class TemplateFieldCreateSchema(BaseModel):
    """新增模板字段"""
    template_id: int = Field(..., description="模板ID")
    tab_name: str | None = Field(default=None, max_length=50, description="所属分类名称")
    tab_order: int = Field(default=0, ge=0, description="分类排序")
    field_name: str = Field(..., max_length=100, description="字段名称")
    field_code: str = Field(..., max_length=50, description="字段编码")
    field_type: str = Field(..., description="字段类型 text/number/date/time/datetime/select/image")
    field_options: Any | None = Field(default=None, description="选项（select 类型）")
    required_flag: int = Field(default=0, ge=0, le=1, description="是否必填 1是 0否")
    sort_num: int = Field(default=0, description="排序")


class TemplateFieldUpdateSchema(BaseModel):
    """修改模板字段"""
    tab_name: str | None = Field(default=None, max_length=50, description="所属分类名称")
    tab_order: int | None = Field(default=None, ge=0, description="分类排序")
    field_name: str | None = Field(default=None, max_length=100, description="字段名称")
    field_code: str | None = Field(default=None, max_length=50, description="字段编码")
    field_type: str | None = Field(default=None, description="字段类型")
    field_options: Any | None = Field(default=None, description="选项（select 类型）")
    required_flag: int | None = Field(default=None, ge=0, le=1, description="是否必填")
    sort_num: int | None = Field(default=None, description="排序")
