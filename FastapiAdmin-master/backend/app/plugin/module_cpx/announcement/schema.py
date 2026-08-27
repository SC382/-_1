# -*- coding: utf-8 -*-
"""公告管理 Schema"""

from datetime import datetime

from pydantic import BaseModel, Field


class AnnouncementCreateSchema(BaseModel):
    """新增公告"""

    title: str = Field(..., max_length=80, description="公告标题")
    subtitle: str | None = Field(default=None, max_length=120, description="副标题/banner 显示用")
    content: str | None = Field(default=None, description="详情内容（HTML/Markdown）")
    cover: str | None = Field(default=None, max_length=500, description="详情页封面图")
    type: str = Field(default="notice", description="类型 system/version/activity/notice")
    sort_order: int = Field(default=0, ge=0, description="排序")
    expires_at: datetime | None = Field(default=None, description="失效时间")
    remark: str | None = Field(default=None, max_length=500, description="备注")


class AnnouncementUpdateSchema(BaseModel):
    """修改公告"""

    title: str | None = Field(default=None, max_length=80, description="公告标题")
    subtitle: str | None = Field(default=None, max_length=120, description="副标题")
    content: str | None = Field(default=None, description="详情内容")
    cover: str | None = Field(default=None, max_length=500, description="封面图")
    type: str | None = Field(default=None, description="类型")
    sort_order: int | None = Field(default=None, ge=0, description="排序")
    expires_at: datetime | None = Field(default=None, description="失效时间")
    remark: str | None = Field(default=None, max_length=500, description="备注")