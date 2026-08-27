# -*- coding: utf-8 -*-
"""增值服务管理 Schema"""

from pydantic import BaseModel, Field


class ValueAddedCreateSchema(BaseModel):
    """新增增值服务"""

    name: str = Field(..., max_length=100, description="服务名称")
    subtitle: str | None = Field(default=None, max_length=120, description="副标题")
    icon: str | None = Field(default=None, max_length=500, description="图标 URL/路径")
    cover: str | None = Field(default=None, max_length=500, description="大卡片背景图")
    link_type: str = Field(default="internal", description="跳转类型 h5/external/internal")
    link_url: str | None = Field(default=None, max_length=500, description="跳转 URL")
    sort_order: int = Field(default=0, ge=0, description="排序")
    remark: str | None = Field(default=None, max_length=500, description="备注")


class ValueAddedUpdateSchema(BaseModel):
    """修改增值服务"""

    name: str | None = Field(default=None, max_length=100, description="服务名称")
    subtitle: str | None = Field(default=None, max_length=120, description="副标题")
    icon: str | None = Field(default=None, max_length=500, description="图标")
    cover: str | None = Field(default=None, max_length=500, description="封面图")
    link_type: str | None = Field(default=None, description="跳转类型")
    link_url: str | None = Field(default=None, max_length=500, description="跳转 URL")
    sort_order: int | None = Field(default=None, ge=0, description="排序")
    remark: str | None = Field(default=None, max_length=500, description="备注")