# -*- coding: utf-8 -*-
"""病例管理 Schema"""

from typing import Any

from pydantic import BaseModel, Field


class CaseCreateSchema(BaseModel):
    """新增病例（测试/联调用；正式由医生 APP 提交）"""
    hospital_id: int = Field(..., description="医院ID")
    doctor_id: int = Field(..., description="提交医生ID")
    patient_name: str | None = Field(default=None, max_length=50, description="患者姓名")
    gender: str | None = Field(default=None, max_length=10, description="性别")
    age: int | None = Field(default=None, description="年龄")
    phone: str | None = Field(default=None, max_length=20, description="联系电话")
    template_id: int | None = Field(default=None, description="模板ID")
    form_data: dict[str, Any] | None = Field(default=None, description="动态表单数据")
    status: str = Field(default="draft", description="draft/submitted/approved/rejected")


class CaseUpdateSchema(BaseModel):
    """更新病例基础信息（web 端与 APP 端互通，仅更新传入字段）"""
    patient_name: str | None = Field(default=None, max_length=50, description="患者姓名")
    gender: str | None = Field(default=None, max_length=10, description="性别")
    age: int | None = Field(default=None, description="年龄")
    phone: str | None = Field(default=None, max_length=20, description="联系电话")


class CaseSubmitSchema(BaseModel):
    """提交病例（置为待审核）"""
    pass
