# -*- coding: utf-8 -*-
"""医院管理 Schema"""

from pydantic import BaseModel, Field


class HospitalCreateSchema(BaseModel):
    """新增医院"""
    hospital_name: str = Field(..., description="医院名称")
    hospital_level: str | None = Field(default=None, description="医院等级")
    province: str | None = Field(default=None, description="省")
    city: str | None = Field(default=None, description="城市")
    address: str | None = Field(default=None, description="详细地址")
    contact_name: str | None = Field(default=None, description="联系人")
    contact_phone: str | None = Field(default=None, description="联系电话")
    status: int = Field(default=1, ge=0, le=1, description="状态 1正常 0禁用")


class HospitalUpdateSchema(BaseModel):
    """修改医院（字段均可选）"""
    hospital_name: str | None = Field(default=None, description="医院名称")
    hospital_level: str | None = Field(default=None, description="医院等级")
    province: str | None = Field(default=None, description="省")
    city: str | None = Field(default=None, description="城市")
    address: str | None = Field(default=None, description="详细地址")
    contact_name: str | None = Field(default=None, description="联系人")
    contact_phone: str | None = Field(default=None, description="联系电话")
    status: int | None = Field(default=None, ge=0, le=1, description="状态 1正常 0禁用")


class HospitalStatusSchema(BaseModel):
    """批量启用/禁用"""
    ids: list[int] = Field(..., description="医院ID列表")
    status: int = Field(..., ge=0, le=1, description="目标状态")
