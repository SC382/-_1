# -*- coding: utf-8 -*-
"""病例管理服务"""

import random
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import CustomException

from app.plugin.module_cpx.auth.dependencies import BizAuth
from app.plugin.module_cpx.case.schema import CaseCreateSchema
from app.plugin.module_cpx.fields import FIELDS
from app.plugin.module_cpx.models import (
    AuditRecordModel,
    CaseDetailModel,
    CaseRecordModel,
    EcgConsultModel,
    FollowUpModel,
    MeetingRecordModel,
)


class CaseService:
    """病例管理服务"""

    def __init__(self, auth: BizAuth, db: AsyncSession) -> None:
        self.auth = auth
        self.db = db

    @staticmethod
    def _generate_case_no() -> str:
        """生成病例编号：C + 年月日时分秒 + 4 位随机数（保证唯一）。"""
        return f"C{datetime.now().strftime('%Y%m%d%H%M%S')}{random.randint(1000, 9999)}"

    async def page(
        self,
        *,
        page_no: int,
        page_size: int,
        hospital_id: int | None,
        doctor_id: int | None,
        case_no: str | None = None,
        patient_name: str | None = None,
        doctor_name: str | None = None,
        status: str | None,
        start_time: str | None,
        end_time: str | None,
    ) -> dict:
        conditions = []
        if hospital_id:
            conditions.append(CaseRecordModel.hospital_id == hospital_id)
        if doctor_id:
            conditions.append(CaseRecordModel.doctor_id == doctor_id)
        # 病例编号：完整编号优先精确匹配；精确无结果时退化为片段模糊检索
        if case_no:
            case_no = case_no.strip()
            exact_count = (
                await self.db.execute(
                    select(func.count()).select_from(CaseRecordModel).where(CaseRecordModel.case_no == case_no)
                )
            ).scalar() or 0
            if exact_count > 0:
                conditions.append(CaseRecordModel.case_no == case_no)
            else:
                conditions.append(CaseRecordModel.case_no.like(f"%{case_no}%"))
        if patient_name:
            conditions.append(CaseRecordModel.patient_name.like(f"%{patient_name.strip()}%"))
        if doctor_name:
            # 提交医生姓名模糊：通过 doctor 账号表 real_name 匹配
            from app.plugin.module_cpx.models import UserAccountModel

            doctor_ids = select(UserAccountModel.id).where(
                UserAccountModel.real_name.like(f"%{doctor_name.strip()}%")
            )
            conditions.append(CaseRecordModel.doctor_id.in_(doctor_ids))
        if status:
            conditions.append(CaseRecordModel.status == status)
        if start_time:
            conditions.append(CaseRecordModel.create_time >= start_time)
        if end_time:
            conditions.append(CaseRecordModel.create_time <= f"{end_time} 23:59:59")

        total = await self.db.execute(
            select(func.count()).select_from(CaseRecordModel).where(*conditions)
        )
        total_count = total.scalar() or 0

        sql = (
            select(CaseRecordModel)
            .where(*conditions)
            .order_by(CaseRecordModel.create_time.desc(), CaseRecordModel.id.desc())
            .offset((page_no - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(sql)
        rows = result.scalars().all()

        items = [
            {
                "id": c.id,
                "case_no": c.case_no,
                "patient_name": c.patient_name,
                "gender": c.gender,
                "age": c.age,
                "phone": c.phone,
                "come_type": c.come_type,
                "diagnose_type": c.diagnose_type,
                "hospital_id": c.hospital_id,
                "hospital_name": c.hospital.hospital_name if c.hospital else None,
                "doctor_id": c.doctor_id,
                "doctor_name": c.doctor.real_name if c.doctor else None,
                "status": c.status,
                "create_time": c.create_time.isoformat() if c.create_time else None,
            }
            for c in rows
        ]
        return {
            "page_no": page_no,
            "page_size": page_size,
            "total": total_count,
            "has_next": page_no * page_size < total_count,
            "items": items,
        }

    async def detail(self, *, id: int) -> dict:
        from app.plugin.module_cpx.models import TemplateFieldModel

        case = await self.db.get(CaseRecordModel, id)
        if not case:
            raise CustomException(msg="病例不存在")

        detail = (
            await self.db.execute(select(CaseDetailModel).where(CaseDetailModel.case_id == id))
        ).scalars().first()

        audits = (
            await self.db.execute(
                select(AuditRecordModel)
                .where(AuditRecordModel.case_id == id)
                .order_by(AuditRecordModel.audit_time.desc())
            )
        ).scalars().all()

        # 模板字段定义（按 sort_num 排序），供前端按字段渲染动态表单数据
        template_fields: list[dict] = []
        if detail and detail.template_id:
            fields = (
                await self.db.execute(
                    select(TemplateFieldModel)
                    .where(TemplateFieldModel.template_id == detail.template_id)
                    .order_by(TemplateFieldModel.sort_num.asc(), TemplateFieldModel.id.asc())
                )
            ).scalars().all()
            template_fields = [
                {
                    "id": f.id,
                    "field_name": f.field_name,
                    "field_code": f.field_code,
                    "field_type": f.field_type,
                    "field_options": f.field_options,
                }
                for f in fields
            ]

        return {
            "id": case.id,
            "case_no": case.case_no,
            "patient_name": case.patient_name,
            "gender": case.gender,
            "age": case.age,
            "phone": case.phone,
            "come_type": case.come_type,
            "diagnose_type": case.diagnose_type,
            "hospital_id": case.hospital_id,
            "hospital_name": case.hospital.hospital_name if case.hospital else None,
            "doctor_id": case.doctor_id,
            "doctor_name": case.doctor.real_name if case.doctor else None,
            "status": case.status,
            "create_time": case.create_time.isoformat() if case.create_time else None,
            "update_time": case.update_time.isoformat() if case.update_time else None,
            "template_id": detail.template_id if detail else None,
            "template_name": detail.template.template_name if detail and detail.template else None,
            "form_data": detail.form_data if detail else None,
            "template_fields": template_fields,
            "field_dict": FIELDS,
            "audit_records": [
                {
                    "id": a.id,
                    "auditor_name": a.auditor.real_name if a.auditor else None,
                    "auditor_hospital_name": (a.auditor.hospital.hospital_name if a.auditor and a.auditor.hospital else None),
                    "audit_result": a.audit_result,
                    "audit_comment": a.audit_comment,
                    "audit_time": a.audit_time.isoformat() if a.audit_time else None,
                }
                for a in audits
            ],
        }

    async def create(self, data: CaseCreateSchema) -> dict:
        """新增病例（含详情，测试/联调用）。"""
        case = CaseRecordModel(
            case_no=self._generate_case_no(),
            hospital_id=data.hospital_id,
            doctor_id=data.doctor_id,
            patient_name=data.patient_name,
            gender=data.gender,
            age=data.age,
            phone=data.phone,
            status=data.status,
        )
        self.db.add(case)
        await self.db.flush()

        if data.template_id is not None:
            detail = CaseDetailModel(
                case_id=case.id,
                template_id=data.template_id,
                form_data=data.form_data or {},
            )
            self.db.add(detail)
            await self.db.flush()
        return {"id": case.id, "case_no": case.case_no}

    async def delete(self, *, id: int) -> dict:
        """删除病例：级联删除 详情/审核记录/随访/心电，三会记录保留（case_id 置空）。"""
        case = await self.db.get(CaseRecordModel, id)
        if not case:
            raise CustomException(msg="病例不存在")

        deleted = 0
        # 级联删除关联表
        for model in (CaseDetailModel, AuditRecordModel, FollowUpModel, EcgConsultModel):
            rows = (
                await self.db.execute(select(model).where(model.case_id == id))
            ).scalars().all()
            for r in rows:
                await self.db.delete(r)
            deleted += len(rows)
        # 三会记录保留：case_id 置空（PPT 文件仍在）
        meetings = (
            await self.db.execute(select(MeetingRecordModel).where(MeetingRecordModel.case_id == id))
        ).scalars().all()
        for m in meetings:
            m.case_id = None
            self.db.add(m)
        deleted += len(meetings)

        result = {"id": case.id, "case_no": case.case_no, "patient_name": case.patient_name, "deleted": deleted}
        await self.db.delete(case)
        await self.db.flush()
        return result

    async def submit(self, *, id: int) -> dict:
        """提交病例：draft → submitted。"""
        case = await self.db.get(CaseRecordModel, id)
        if not case:
            raise CustomException(msg="病例不存在")
        if case.status not in ("draft", "rejected"):
            raise CustomException(msg="当前状态不可提交")
        case.status = "submitted"
        self.db.add(case)
        await self.db.flush()
        return {"id": case.id, "status": case.status}

    async def update(self, *, id: int, data: dict) -> dict:
        """更新病例基础信息（web 端与 APP 端互通：电话/姓名/性别/年龄等）。"""
        case = await self.db.get(CaseRecordModel, id)
        if not case:
            raise CustomException(msg="病例不存在")
        payload = data.model_dump(exclude_unset=True)
        for key, value in payload.items():
            if value is not None:
                setattr(case, key, value)
        self.db.add(case)
        await self.db.flush()
        return {"id": case.id, "case_no": case.case_no, "phone": case.phone}
