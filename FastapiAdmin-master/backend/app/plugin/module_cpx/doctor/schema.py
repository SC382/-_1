# -*- coding: utf-8 -*-
"""医生端 Schema"""

from pydantic import BaseModel, Field


class CaseCreateSchema(BaseModel):
    """患者建档（生成病例）"""
    patient_name: str = Field(..., min_length=1, max_length=50, description="患者姓名")
    gender: str | None = Field(default=None, max_length=10, description="性别")
    age: int | None = Field(default=None, ge=0, le=200, description="年龄")
    phone: str | None = Field(default=None, max_length=20, description="联系电话")
    template_id: int = Field(..., description="填报模板ID")
    come_type: str | None = Field(default=None, max_length=20, description="来院方式")
    diagnose_type: str | None = Field(default=None, max_length=30, description="诊断类型")
    first_contact_time: str | None = Field(default=None, description="首次医疗接触时间 yyyy-MM-dd HH:mm")
    id_type: str | None = Field(default=None, max_length=30, description="证件类型")
    id_number: str | None = Field(default=None, max_length=50, description="证件号码")
    birth_date: str | None = Field(default=None, description="出生日期 yyyy-MM-dd")
    onset_address: str | None = Field(default=None, max_length=200, description="发病地址")
    detail_address: str | None = Field(default=None, max_length=500, description="详细地址")
    insurance_type: str | None = Field(default=None, max_length=30, description="医保类型")
    insurance_no: str | None = Field(default=None, max_length=50, description="医保编号")


class CaseUpdateSchema(BaseModel):
    """更新患者基础信息（草稿/驳回状态下）"""
    patient_name: str | None = Field(default=None, min_length=1, max_length=50, description="患者姓名")
    gender: str | None = Field(default=None, max_length=10, description="性别")
    age: int | None = Field(default=None, ge=0, le=200, description="年龄")
    phone: str | None = Field(default=None, max_length=20, description="联系电话")
    come_type: str | None = Field(default=None, max_length=20, description="来院方式")
    diagnose_type: str | None = Field(default=None, max_length=30, description="诊断类型")
    first_contact_time: str | None = Field(default=None, description="首次医疗接触时间")
    id_type: str | None = Field(default=None, max_length=30, description="证件类型")
    id_number: str | None = Field(default=None, max_length=50, description="证件号码")
    birth_date: str | None = Field(default=None, description="出生日期")
    onset_address: str | None = Field(default=None, max_length=200, description="发病地址")
    detail_address: str | None = Field(default=None, max_length=500, description="详细地址")
    insurance_type: str | None = Field(default=None, max_length=30, description="医保类型")
    insurance_no: str | None = Field(default=None, max_length=50, description="医保编号")


class FormSaveSchema(BaseModel):
    """保存动态表单数据（草稿/提交）"""
    template_id: int = Field(..., description="填报模板ID")
    form_data: dict = Field(default_factory=dict, description="表单数据（字段编码→值）")


class PasswordChangeSchema(BaseModel):
    """修改密码"""
    old_password: str = Field(..., min_length=1, description="原密码")
    new_password: str = Field(..., min_length=6, max_length=50, description="新密码")


class FollowUpSubmitSchema(BaseModel):
    """提交随访表单"""
    follow_date: str | None = Field(default=None, description="随访日期 yyyy-MM-dd")
    follow_status: str | None = Field(default=None, description="followed/unfollowed")
    survival_status: str | None = Field(default=None, description="alive/dead/unknown")
    risk_control: str | None = Field(default=None, max_length=200, description="危险因素控制")
    medication: str | None = Field(default=None, max_length=500, description="用药情况")
    remark: str | None = Field(default=None, max_length=500, description="备注")
