# -*- coding: utf-8 -*-
"""胸痛中心业务表 ORM 模型 — 精确映射现有数据库表结构（无软删除，物理删除）。

约定：
- 全部继承 ``MappedBase``（仅自动生成表名），显式声明所有列。
- 主键统一 ``BigInteger``（对应库表 bigint）。
- 时间字段 ``create_time / update_time``，默认交由 MySQL 的 CURRENT_TIMESTAMP 处理。
"""

from datetime import date, datetime

from sqlalchemy import JSON, BigInteger, Date, DateTime, ForeignKey, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base_model import MappedBase
from app.core.crypto import EncryptedJson, EncryptedString


class HospitalModel(MappedBase):
    """医院信息表"""
    __tablename__: str = "hospital"
    __table_args__: dict[str, str] = {"comment": "医院信息表"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="医院ID")
    hospital_name: Mapped[str] = mapped_column(String(100), nullable=False, comment="医院名称")
    hospital_level: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="医院等级")
    province: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="省")
    city: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="城市")
    address: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="详细地址")
    contact_name: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="联系人")
    contact_phone: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="联系电话")
    status: Mapped[int | None] = mapped_column(SmallInteger, nullable=True, default=1, comment="状态 1正常 0禁用")
    create_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=datetime.now, comment="创建时间")
    update_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=datetime.now, onupdate=datetime.now, comment="更新时间")


class CpxRoleModel(MappedBase):
    """角色表（命名避免与框架 sys_role 的 RoleModel 冲突）"""
    __tablename__: str = "role"
    __table_args__: dict[str, str] = {"comment": "角色表"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="角色ID")
    role_name: Mapped[str] = mapped_column(String(50), nullable=False, comment="角色名称")
    description: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="角色描述")
    create_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=datetime.now, comment="创建时间")


class UserAccountModel(MappedBase):
    """用户账号表（管理员/审核员/医生共用）"""
    __tablename__: str = "user_account"
    __table_args__: dict[str, str] = {"comment": "用户账号表"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="用户ID")
    username: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, comment="登录账号")
    password: Mapped[str] = mapped_column(String(255), nullable=False, comment="密码")
    real_name: Mapped[str] = mapped_column(String(50), nullable=False, comment="姓名")
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="手机号")
    role_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("role.id"), nullable=False, comment="角色ID")
    hospital_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("hospital.id"), nullable=True, comment="所属医院")
    status: Mapped[int | None] = mapped_column(SmallInteger, nullable=True, default=1, comment="状态 1正常 0禁用")
    last_login_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="最后登录时间")
    create_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=datetime.now, comment="创建时间")
    update_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    role: Mapped[CpxRoleModel | None] = relationship(foreign_keys=[role_id], lazy="joined")
    hospital: Mapped[HospitalModel | None] = relationship(foreign_keys=[hospital_id], lazy="joined")


class DoctorInfoModel(MappedBase):
    """医生信息表"""
    __tablename__: str = "doctor_info"
    __table_args__: dict[str, str] = {"comment": "医生信息表"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("user_account.id"), nullable=False, comment="用户ID")
    hospital_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("hospital.id"), nullable=False, comment="医院ID")
    doctor_no: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="医生工号")
    department: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="科室")
    title: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="职称")
    create_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=datetime.now, comment="创建时间")

    user: Mapped[UserAccountModel | None] = relationship(foreign_keys=[user_id], lazy="joined")
    hospital: Mapped[HospitalModel | None] = relationship(foreign_keys=[hospital_id], lazy="joined")


class AuditorInfoModel(MappedBase):
    """审核员信息表"""
    __tablename__: str = "auditor_info"
    __table_args__: dict[str, str] = {"comment": "审核员信息表"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("user_account.id"), nullable=False, comment="用户ID")
    hospital_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("hospital.id"), nullable=False, comment="所属医院")
    audit_level: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="审核权限")
    create_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=datetime.now, comment="创建时间")

    user: Mapped[UserAccountModel | None] = relationship(foreign_keys=[user_id], lazy="joined")
    hospital: Mapped[HospitalModel | None] = relationship(foreign_keys=[hospital_id], lazy="joined")


class CaseRecordModel(MappedBase):
    """病例主表"""
    __tablename__: str = "case_record"
    __table_args__: dict[str, str] = {"comment": "病例主表"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    case_no: Mapped[str | None] = mapped_column(String(50), nullable=True, unique=True, comment="病例编号")
    hospital_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("hospital.id"), nullable=False, comment="医院ID")
    doctor_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("user_account.id"), nullable=False, comment="提交医生")
    patient_name: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="患者姓名")
    gender: Mapped[str | None] = mapped_column(String(10), nullable=True, comment="性别")
    age: Mapped[int | None] = mapped_column(nullable=True, comment="年龄")
    phone: Mapped[str | None] = mapped_column(EncryptedString(255), nullable=True, comment="联系电话")
    first_contact_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="首次医疗接触时间")
    id_type: Mapped[str | None] = mapped_column(String(30), nullable=True, comment="证件类型 身份证/社保卡/其他")
    id_number: Mapped[str | None] = mapped_column(EncryptedString(255), nullable=True, comment="证件号码")
    birth_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="出生日期")
    onset_address: Mapped[str | None] = mapped_column(String(200), nullable=True, comment="发病地址")
    detail_address: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="详细地址")
    insurance_type: Mapped[str | None] = mapped_column(String(30), nullable=True, comment="医保类型")
    insurance_no: Mapped[str | None] = mapped_column(EncryptedString(255), nullable=True, comment="医保编号")
    come_type: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="来院方式 120/自行/转诊")
    diagnose_type: Mapped[str | None] = mapped_column(String(30), nullable=True, comment="诊断类型 STEMI/NSTEMI/UA/主动脉夹层/肺栓塞/低危胸痛")
    status: Mapped[str | None] = mapped_column(String(20), nullable=True, default="draft", comment="draft草稿 submitted待审核 approved通过 rejected驳回")
    create_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=datetime.now, comment="创建时间")
    update_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    hospital: Mapped[HospitalModel | None] = relationship(foreign_keys=[hospital_id], lazy="joined")
    doctor: Mapped[UserAccountModel | None] = relationship(foreign_keys=[doctor_id], lazy="joined")
    details: Mapped[list["CaseDetailModel"]] = relationship(back_populates="case", lazy="selectin")
    audit_records: Mapped[list["AuditRecordModel"]] = relationship(back_populates="case", lazy="selectin")


class CaseDetailModel(MappedBase):
    """病例详情表（模板驱动的动态表单数据）"""
    __tablename__: str = "case_detail"
    __table_args__: dict[str, str] = {"comment": "病例详情表"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    case_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("case_record.id"), nullable=False, comment="病例ID")
    template_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("report_template.id"), nullable=False, comment="模板ID")
    form_data: Mapped[dict | None] = mapped_column(EncryptedJson, nullable=True, comment="动态表单数据")
    create_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=datetime.now, comment="创建时间")
    update_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    case: Mapped[CaseRecordModel | None] = relationship(back_populates="details", foreign_keys=[case_id])
    template: Mapped["ReportTemplateModel | None"] = relationship(foreign_keys=[template_id], lazy="joined")


class AuditRecordModel(MappedBase):
    """审核记录表"""
    __tablename__: str = "audit_record"
    __table_args__: dict[str, str] = {"comment": "审核记录表"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    case_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("case_record.id"), nullable=False, comment="病例ID")
    auditor_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("user_account.id"), nullable=False, comment="审核员ID")
    audit_result: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="pass通过 reject驳回")
    audit_comment: Mapped[str | None] = mapped_column(Text, nullable=True, comment="审核意见")
    audit_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="审核时间")

    case: Mapped[CaseRecordModel | None] = relationship(back_populates="audit_records", foreign_keys=[case_id])
    auditor: Mapped[UserAccountModel | None] = relationship(foreign_keys=[auditor_id], lazy="joined")


class ReportTemplateModel(MappedBase):
    """填报模板表"""
    __tablename__: str = "report_template"
    __table_args__: dict[str, str] = {"comment": "填报模板表"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    template_name: Mapped[str] = mapped_column(String(100), nullable=False, comment="模板名称")
    version: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="版本号")
    status: Mapped[int | None] = mapped_column(SmallInteger, nullable=True, default=1, comment="状态 1启用 0停用")
    published: Mapped[int | None] = mapped_column(SmallInteger, nullable=True, default=0, comment="发布状态 0未发布 1已发布")
    creator_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="创建人")
    create_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=datetime.now, comment="创建时间")
    update_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    fields: Mapped[list["TemplateFieldModel"]] = relationship(back_populates="template", lazy="selectin")


class TemplateFieldModel(MappedBase):
    """模板字段表"""
    __tablename__: str = "template_field"
    __table_args__: dict[str, str] = {"comment": "模板字段表"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    template_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("report_template.id"), nullable=False, comment="模板ID")
    tab_name: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="所属分类名称")
    tab_order: Mapped[int | None] = mapped_column(nullable=True, default=0, comment="分类排序")
    field_name: Mapped[str] = mapped_column(String(100), nullable=False, comment="字段名称")
    field_code: Mapped[str] = mapped_column(String(50), nullable=False, comment="字段编码")
    field_type: Mapped[str | None] = mapped_column(String(30), nullable=True, comment="字段类型 text/number/date/time/datetime/select/image")
    field_options: Mapped[dict | list | None] = mapped_column(JSON, nullable=True, comment="选项（select 类型用）")
    required_flag: Mapped[int | None] = mapped_column(SmallInteger, nullable=True, default=0, comment="是否必填 1是 0否")
    sort_num: Mapped[int | None] = mapped_column(nullable=True, default=0, comment="排序")
    create_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=datetime.now, comment="创建时间")

    template: Mapped[ReportTemplateModel | None] = relationship(back_populates="fields", foreign_keys=[template_id])


class FollowUpModel(MappedBase):
    """ACS 随访管理表"""
    __tablename__: str = "follow_up"
    __table_args__: dict[str, str] = {"comment": "ACS随访管理表"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    case_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("case_record.id"), nullable=False, comment="病例ID")
    patient_name: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="患者姓名")
    hospital_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("hospital.id"), nullable=False, comment="医院ID")
    doctor_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("user_account.id"), nullable=False, comment="创建医生")
    plan_month: Mapped[int | None] = mapped_column(nullable=True, comment="随访计划 1/3/6/12月")
    due_date: Mapped[datetime | None] = mapped_column(nullable=True, comment="应随访日期")
    status: Mapped[str | None] = mapped_column(String(20), nullable=True, default="pending", comment="pending随访中 submitted已提交 overdue已过期")
    follow_date: Mapped[datetime | None] = mapped_column(nullable=True, comment="实际随访日期")
    follow_status: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="followed已随访 unfollowed未随访")
    survival_status: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="alive存活 dead死亡 unknown未知")
    risk_control: Mapped[str | None] = mapped_column(String(200), nullable=True, comment="危险因素控制")
    medication: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="用药情况")
    remark: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="备注")
    form_data: Mapped[str | None] = mapped_column(Text, nullable=True, comment="随访表单扩展数据 JSON（分组字段）")
    create_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=datetime.now, comment="创建时间")
    update_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    case: Mapped[CaseRecordModel | None] = relationship(foreign_keys=[case_id], lazy="joined")


class TreatmentUnitModel(MappedBase):
    """胸痛救治单元表"""
    __tablename__: str = "treatment_unit"
    __table_args__: dict[str, str] = {"comment": "胸痛救治单元表"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    unit_name: Mapped[str] = mapped_column(String(100), nullable=False, comment="单元名称")
    hospital_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("hospital.id"), nullable=False, comment="所属医院")
    contact_name: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="联系人")
    contact_phone: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="联系电话")
    status: Mapped[int | None] = mapped_column(SmallInteger, nullable=True, default=1, comment="1启用 0停用")
    create_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=datetime.now, comment="创建时间")

    hospital: Mapped[HospitalModel | None] = relationship(foreign_keys=[hospital_id], lazy="joined")


class EcgConsultModel(MappedBase):
    """远程心电AI诊断与会诊表

    状态机：draft(待上传) → uploaded(已上传/AI完成) → consult_sent(已发送会诊)
            → received(接收方已接收) → closed(已反馈)
    """
    __tablename__: str = "ecg_consult"
    __table_args__: dict[str, str] = {"comment": "远程心电AI诊断与会诊表"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    case_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("case_record.id"), nullable=True, comment="关联病例")
    hospital_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("hospital.id"), nullable=False, comment="发起医院")
    doctor_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("user_account.id"), nullable=False, comment="发起医生")
    target_hospital_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("hospital.id"), nullable=True, comment="接收会诊医院（未选则仅做 AI 诊断）")
    target_doctor_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("user_account.id"), nullable=True, comment="接收会诊医生（反馈时填）")
    image_path: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="心电图图片")
    patient_info_json: Mapped[str | None] = mapped_column(Text, nullable=True, comment="上传时病例基础信息快照（JSON）")
    ai_diagnosis: Mapped[str | None] = mapped_column(Text, nullable=True, comment="AI 诊断意见（mock，后续接真模型）")
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True, comment="AI 协同意见总结（发给接收方）")
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True, comment="接收方反馈意见")
    feedback_doctor_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("user_account.id"), nullable=True, comment="反馈医生")
    feedback_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="反馈时间")
    status: Mapped[str | None] = mapped_column(String(20), nullable=True, default="draft", comment="状态 draft/uploaded/consult_sent/received/closed")
    create_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=datetime.now, comment="创建时间")
    update_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    case: Mapped[CaseRecordModel | None] = relationship(foreign_keys=[case_id], lazy="joined")


class MeetingRecordModel(MappedBase):
    """三会 PPT 生成记录表"""
    __tablename__: str = "meeting_record"
    __table_args__: dict[str, str] = {"comment": "三会PPT生成记录表"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    meeting_type: Mapped[str] = mapped_column(String(30), nullable=False, comment="quality/joint/case")
    title: Mapped[str] = mapped_column(String(100), nullable=False, comment="标题")
    hospital_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("hospital.id"), nullable=False, comment="医院")
    doctor_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("user_account.id"), nullable=False, comment="生成医生")
    case_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="典型病例讨论会关联病例ID")
    start_date: Mapped[datetime | None] = mapped_column(nullable=True, comment="统计开始")
    end_date: Mapped[datetime | None] = mapped_column(nullable=True, comment="统计结束")
    file_path: Mapped[str | None] = mapped_column(String(300), nullable=True, comment="PPT文件路径")
    file_size: Mapped[int | None] = mapped_column(nullable=True, comment="文件大小")
    create_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=datetime.now, comment="生成时间")

    hospital: Mapped[HospitalModel | None] = relationship(foreign_keys=[hospital_id], lazy="joined")


class AcademyContentModel(MappedBase):
    """胸痛学院内容表（PPT / 视频 / 文档等学习资源）"""
    __tablename__: str = "academy_content"
    __table_args__: dict[str, str] = {"comment": "胸痛学院内容表"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False, comment="标题")
    content_type: Mapped[str] = mapped_column(String(20), nullable=False, comment="类型 video/ppt/doc/pdf/other")
    category: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="分类（如 指南共识/培训课程/学术会议）")
    summary: Mapped[str | None] = mapped_column(Text, nullable=True, comment="简介")
    file_path: Mapped[str] = mapped_column(String(300), nullable=False, comment="文件相对路径（static 下）")
    file_name: Mapped[str | None] = mapped_column(String(200), nullable=True, comment="原始文件名")
    file_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="文件大小（字节）")
    cover_path: Mapped[str | None] = mapped_column(String(300), nullable=True, comment="封面图（可选）")
    published: Mapped[int | None] = mapped_column(SmallInteger, nullable=True, default=0, comment="发布状态 0草稿 1发布")
    sort_num: Mapped[int | None] = mapped_column(nullable=True, default=0, comment="排序")
    view_count: Mapped[int | None] = mapped_column(nullable=True, default=0, comment="浏览量")
    download_count: Mapped[int | None] = mapped_column(nullable=True, default=0, comment="下载量")
    creator_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="创建人")
    create_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=datetime.now, comment="创建时间")
    update_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=datetime.now, onupdate=datetime.now, comment="更新时间")


class SystemLogModel(MappedBase):
    """系统操作日志表"""
    __tablename__: str = "system_log"
    __table_args__: dict[str, str] = {"comment": "系统操作日志"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("user_account.id"), nullable=True, comment="操作用户")
    module: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="模块")
    operation: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="操作类型")
    description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="操作描述")
    ip_address: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="IP地址")
    result: Mapped[str | None] = mapped_column(String(20), nullable=True, default="success", comment="操作结果 success成功 fail失败")
    create_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=datetime.now, comment="创建时间")

    user: Mapped[UserAccountModel | None] = relationship(foreign_keys=[user_id], lazy="joined")


# 统计表（二期使用，先注册模型便于 create_all 一致性）
class StatisticDailyModel(MappedBase):
    """每日统计表（二期）"""
    __tablename__: str = "statistic_daily"
    __table_args__: dict[str, str] = {"comment": "每日统计表"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    hospital_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("hospital.id"), nullable=False, comment="医院ID")
    stat_date: Mapped[date | None] = mapped_column(Date, nullable=True, comment="统计日期")
    case_count: Mapped[int | None] = mapped_column(nullable=True, default=0, comment="病例数量")
    audit_count: Mapped[int | None] = mapped_column(nullable=True, default=0, comment="审核数量")
    pass_count: Mapped[int | None] = mapped_column(nullable=True, default=0, comment="通过数量")
    reject_count: Mapped[int | None] = mapped_column(nullable=True, default=0, comment="驳回数量")
    create_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=datetime.now, comment="创建时间")


class AiKbChunkModel(MappedBase):
    """AI 助手知识库分片表（PDF 导入）"""
    __tablename__: str = "ai_kb_chunk"
    __table_args__: dict[str, str] = {"comment": "AI助手知识库分片"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    source_file: Mapped[str] = mapped_column(String(200), nullable=False, comment="来源文件名")
    page_no: Mapped[int | None] = mapped_column(nullable=True, comment="来源页码")
    chunk_index: Mapped[int | None] = mapped_column(nullable=True, comment="文件内分片序号")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="分片内容")
    create_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=datetime.now, comment="导入时间")


class AnnouncementModel(MappedBase):
    """公告表（Web 端管理发布，App 端首页 banner + 详情查看）"""
    __tablename__: str = "announcement"
    __table_args__: dict[str, str] = {"comment": "公告表"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(80), nullable=False, comment="公告标题")
    subtitle: Mapped[str | None] = mapped_column(String(120), nullable=True, comment="副标题/banner 显示用")
    content: Mapped[str | None] = mapped_column(Text, nullable=True, comment="详情内容（HTML/Markdown）")
    cover: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="详情页封面图")
    type: Mapped[str | None] = mapped_column(String(30), nullable=True, default="notice", comment="类型 system/version/activity/notice")
    sort_order: Mapped[int | None] = mapped_column(nullable=True, default=0, comment="排序（值大者靠前）")
    status: Mapped[str | None] = mapped_column(String(20), nullable=True, default="draft", comment="状态 draft/published/offline")
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="发布时间")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="失效时间（null=永久）")
    creator_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="创建人")
    remark: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="备注")
    create_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=datetime.now, comment="创建时间")
    update_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=datetime.now, onupdate=datetime.now, comment="更新时间")


class ValueAddedServiceModel(MappedBase):
    """增值服务表（Web 端管理发布，App 端首页区块卡片展示 + 跳转）"""
    __tablename__: str = "value_added_service"
    __table_args__: dict[str, str] = {"comment": "增值服务表"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="服务名称")
    subtitle: Mapped[str | None] = mapped_column(String(120), nullable=True, comment="副标题")
    icon: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="图标 URL/路径")
    cover: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="大卡片背景图")
    link_type: Mapped[str | None] = mapped_column(String(20), nullable=True, default="internal", comment="跳转类型 h5/external/internal")
    link_url: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="跳转 URL（H5 路径或外链）")
    sort_order: Mapped[int | None] = mapped_column(nullable=True, default=0, comment="排序")
    status: Mapped[str | None] = mapped_column(String(20), nullable=True, default="draft", comment="状态 draft/online/offline")
    creator_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="创建人")
    remark: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="备注")
    create_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=datetime.now, comment="创建时间")
    update_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=datetime.now, onupdate=datetime.now, comment="更新时间")
