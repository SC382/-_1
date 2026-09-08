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
    """提交随访表单（35 字段分组；核心必填在 service 层按是否已随访校验）"""
    # ── 基本信息 ──────────────────────────────
    follow_date: str | None = Field(default=None, description="实际随访/评估日期 yyyy-MM-dd")
    follow_status: str | None = Field(default=None, description="followed已随访/unfollowed未随访")
    survival_status: str | None = Field(default=None, description="alive存活/dead死亡/unknown未知")
    plan_date_start: str | None = Field(default=None, description="随访计划日期起")
    plan_date_end: str | None = Field(default=None, description="随访计划日期止")
    follow_dept: str | None = Field(default=None, max_length=50, description="随访科室")
    follow_user: str | None = Field(default=None, max_length=50, description="随访人")
    unplanned_admission: str | None = Field(default=None, max_length=10, description="非计划入院 是/否")
    info_channel: str | None = Field(default=None, max_length=30, description="信息获取途径")
    current_condition: str | None = Field(default=None, max_length=30, description="目前状况")
    cardiac_rehab: str | None = Field(default=None, max_length=10, description="加入心脏康复计划 是/否")
    mace: str | None = Field(default=None, max_length=200, description="出院后主要心血管不良事件")
    # ── 危险因素控制 ──────────────────────────
    bp_monitor: str | None = Field(default=None, max_length=20, description="血压监测")
    lipid_panel: str | None = Field(default=None, max_length=20, description="血脂四项")
    lpa: str | None = Field(default=None, max_length=20, description="脂蛋白a(LPa)")
    fasting_glucose: str | None = Field(default=None, max_length=20, description="空腹血糖")
    hba1c: str | None = Field(default=None, max_length=20, description="糖化血红蛋白")
    smoking: str | None = Field(default=None, max_length=10, description="吸烟 是/否")
    alcohol: str | None = Field(default=None, max_length=10, description="饮酒 是/否")
    height: str | None = Field(default=None, max_length=10, description="身高(cm)")
    weight: str | None = Field(default=None, max_length=10, description="体重(kg)")
    bmi: str | None = Field(default=None, max_length=10, description="BMI 自动计算")
    # ── 躯体症状与心功能评价 ──────────────────
    symptoms: str | None = Field(default=None, max_length=50, description="躯体症状")
    nyha: str | None = Field(default=None, max_length=20, description="心脏纽约分级 NYHA")
    # ── 心电图 ────────────────────────────────
    ecg_result: str | None = Field(default=None, max_length=50, description="心电图结果（阴性/阳性/未查）")
    ecg_image: str | None = Field(default=None, max_length=500, description="心电图图片 URL（上传接口返回）")
    ecg_record_id: int | None = Field(default=None, description="关联 ECG 记录ID（可选，历史兼容）")
    # ── 检查项目 ──────────────────────────────
    ckmb: str | None = Field(default=None, max_length=20, description="CKMB")
    troponin: str | None = Field(default=None, max_length=20, description="肌钙蛋白")
    bnp: str | None = Field(default=None, max_length=20, description="脑钠肽")
    echocardiography: str | None = Field(default=None, max_length=20, description="超声心动图")
    coronary_angiography: str | None = Field(default=None, max_length=20, description="冠脉造影")
    coronary_cta: str | None = Field(default=None, max_length=20, description="冠脉CTA")
    # ── 用药情况（是/否）──────────────────────
    med_antiplatelet: str | None = Field(default=None, max_length=10, description="抗血小板")
    med_lipid_lowering: str | None = Field(default=None, max_length=10, description="调脂")
    med_acei: str | None = Field(default=None, max_length=10, description="ACEI")
    med_arb: str | None = Field(default=None, max_length=10, description="ARB")
    med_arni: str | None = Field(default=None, max_length=10, description="ARNI")
    med_beta_blocker: str | None = Field(default=None, max_length=10, description="β受体阻滞剂")
    med_hypoglycemic: str | None = Field(default=None, max_length=10, description="降糖")
    med_anticoagulant: str | None = Field(default=None, max_length=10, description="抗凝")
    med_diuretic: str | None = Field(default=None, max_length=10, description="利尿剂")
    # ── 旧字段兼容 ────────────────────────────
    risk_control: str | None = Field(default=None, max_length=200, description="危险因素控制(旧)")
    medication: str | None = Field(default=None, max_length=500, description="用药情况(旧)")
    remark: str | None = Field(default=None, max_length=500, description="备注/失访原因")
