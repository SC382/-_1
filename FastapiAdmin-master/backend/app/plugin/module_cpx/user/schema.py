# -*- coding: utf-8 -*-
"""医院用户管理（医生/审核员）Schema"""

from pydantic import BaseModel, Field


class DoctorCreateSchema(BaseModel):
    """新增医生"""
    username: str = Field(..., min_length=2, max_length=50, description="登录账号")
    password: str = Field(..., min_length=6, max_length=50, description="密码")
    real_name: str = Field(..., max_length=50, description="姓名")
    phone: str | None = Field(default=None, max_length=20, description="手机号")
    hospital_id: int = Field(..., description="所属医院ID")
    doctor_no: str | None = Field(default=None, max_length=50, description="医生工号")
    department: str | None = Field(default=None, max_length=50, description="科室")
    title: str | None = Field(default=None, max_length=50, description="职称")
    status: int = Field(default=1, ge=0, le=1, description="状态")


class AuditorCreateSchema(BaseModel):
    """新增审核员"""
    username: str = Field(..., min_length=2, max_length=50, description="登录账号")
    password: str = Field(..., min_length=6, max_length=50, description="密码")
    real_name: str = Field(..., max_length=50, description="姓名")
    phone: str | None = Field(default=None, max_length=20, description="手机号")
    hospital_id: int = Field(..., description="所属医院ID")
    audit_level: str | None = Field(default=None, max_length=50, description="审核权限")
    status: int = Field(default=1, ge=0, le=1, description="状态")


class UserUpdateSchema(BaseModel):
    """修改用户公共字段（医生/审核员通用）"""
    real_name: str | None = Field(default=None, max_length=50, description="姓名")
    phone: str | None = Field(default=None, max_length=20, description="手机号")
    status: int | None = Field(default=None, ge=0, le=1, description="状态")


class DoctorUpdateSchema(UserUpdateSchema):
    """修改医生"""
    doctor_no: str | None = Field(default=None, max_length=50, description="医生工号")
    department: str | None = Field(default=None, max_length=50, description="科室")
    title: str | None = Field(default=None, max_length=50, description="职称")


class AuditorUpdateSchema(UserUpdateSchema):
    """修改审核员"""
    audit_level: str | None = Field(default=None, max_length=50, description="审核权限")


class UserStatusSchema(BaseModel):
    """批量启用/禁用"""
    ids: list[int] = Field(..., description="用户ID列表")
    status: int = Field(..., ge=0, le=1, description="目标状态")


class ResetPasswordSchema(BaseModel):
    """重置密码"""
    password: str = Field(..., min_length=6, max_length=50, description="新密码")
