# -*- coding: utf-8 -*-
"""胸痛学院 Schema"""

from pydantic import BaseModel, Field


class AcademyCreateSchema(BaseModel):
    """新增胸痛学院内容"""
    title: str = Field(..., max_length=200, description="标题")
    content_type: str = Field(..., description="类型 video/ppt/doc/pdf/other")
    category: str | None = Field(default=None, max_length=50, description="分类")
    summary: str | None = Field(default=None, description="简介")
    file_path: str = Field(..., max_length=300, description="文件相对路径")
    file_name: str | None = Field(default=None, max_length=200, description="原始文件名")
    file_size: int | None = Field(default=None, description="文件大小（字节）")
    cover_path: str | None = Field(default=None, max_length=300, description="封面图")
    published: int = Field(default=0, ge=0, le=1, description="发布状态 0草稿 1发布")
    sort_num: int = Field(default=0, description="排序")


class AcademyUpdateSchema(BaseModel):
    """修改胸痛学院内容（仅传入字段生效）"""
    title: str | None = Field(default=None, max_length=200, description="标题")
    content_type: str | None = Field(default=None, description="类型")
    category: str | None = Field(default=None, max_length=50, description="分类")
    summary: str | None = Field(default=None, description="简介")
    file_path: str | None = Field(default=None, max_length=300, description="文件相对路径")
    file_name: str | None = Field(default=None, max_length=200, description="原始文件名")
    file_size: int | None = Field(default=None, description="文件大小（字节）")
    cover_path: str | None = Field(default=None, max_length=300, description="封面图")
    published: int | None = Field(default=None, ge=0, le=1, description="发布状态")
    sort_num: int | None = Field(default=None, description="排序")
