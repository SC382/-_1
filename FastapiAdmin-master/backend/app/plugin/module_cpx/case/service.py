# -*- coding: utf-8 -*-
"""病例管理服务"""

import json
import random
from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import CustomException
from app.config.setting import settings
from app.core.signed_url import sign_static_url

from app.plugin.module_cpx.auth.dependencies import BizAuth
from app.plugin.module_cpx.case.schema import CaseCreateSchema
from app.plugin.module_cpx.fields import (
    FIELDS,
    QUALITY_METRICS,
    TIMELINE_NODES,
)
from app.plugin.module_cpx.models import (
    AuditRecordModel,
    CaseDetailModel,
    CaseRecordModel,
    EcgConsultModel,
    FollowUpModel,
    MeetingRecordModel,
    UserAccountModel,
)


def _cpx_abs_static_url(path: str | None) -> str | None:
    """心电图/图片相对路径转可访问绝对 URL（与 doctor.service._abs_static_url 同逻辑）。"""
    if not path:
        return None
    p = path.lstrip("/")
    if p.startswith("api/v1/") or p.startswith("http://") or p.startswith("https://"):
        return sign_static_url("/" + p)
    return sign_static_url(f"{settings.ROOT_PATH}{settings.STATIC_URL}/{p}")


def _cpx_parse_time(value) -> datetime | None:
    """解析时间字段（兼容多种格式），失败返回 None。"""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    text = str(value).strip().replace("T", " ")
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d", "%Y/%m/%d %H:%M:%S", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def _cpx_diff_minutes(t1: datetime | None, t2: datetime | None) -> int | None:
    if t1 and t2:
        return int((t2 - t1).total_seconds() // 60)
    return None


class CaseService:
    """病例管理服务"""

    def __init__(self, auth: BizAuth, db: AsyncSession) -> None:
        self.auth = auth
        self.db = db

    @staticmethod
    def _generate_case_no() -> str:
        """生成病例编号：C + 年月日时分秒 + 4 位随机数（保证唯一）。"""
        return f"C{datetime.now().strftime('%Y%m%d%H%M%S')}{random.randint(1000, 9999)}"

    async def _build_conditions(
        self,
        *,
        hospital_id: int | None,
        doctor_id: int | None,
        case_no: str | None,
        patient_name: str | None,
        doctor_name: str | None,
        status: str | None,
        start_time: str | None,
        end_time: str | None,
    ) -> list:
        """构建病例筛选条件（列表分页与导出共用，保持口径一致）"""
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
        return conditions

    async def export_data(
        self,
        *,
        hospital_id: int | None,
        doctor_id: int | None,
        case_no: str | None,
        patient_name: str | None,
        doctor_name: str | None,
        status: str | None,
        start_time: str | None,
        end_time: str | None,
    ) -> list[dict]:
        """导出病例数据（全量，不分页；含病例基础信息 + 填报 form_data）"""
        conditions = await self._build_conditions(
            hospital_id=hospital_id,
            doctor_id=doctor_id,
            case_no=case_no,
            patient_name=patient_name,
            doctor_name=doctor_name,
            status=status,
            start_time=start_time,
            end_time=end_time,
        )
        rows = (
            await self.db.execute(
                select(CaseRecordModel)
                .where(*conditions)
                .order_by(CaseRecordModel.create_time.desc(), CaseRecordModel.id.desc())
            )
        ).scalars().all()
        if not rows:
            return []

        form_map: dict[int, dict] = {}
        details = (
            await self.db.execute(
                select(CaseDetailModel).where(CaseDetailModel.case_id.in_([c.id for c in rows]))
            )
        ).scalars().all()
        for d in details:
            form_map[d.case_id] = d.form_data or {}

        return [
            {
                "case_no": c.case_no,
                "patient_name": c.patient_name,
                "gender": c.gender,
                "age": c.age,
                "phone": c.phone,
                "come_type": c.come_type,
                "diagnose_type": c.diagnose_type,
                "hospital_name": c.hospital.hospital_name if c.hospital else None,
                "doctor_name": c.doctor.real_name if c.doctor else None,
                "status": c.status,
                "create_time": c.create_time.strftime("%Y-%m-%d %H:%M:%S") if c.create_time else None,
                "form_data": form_map.get(c.id, {}),
            }
            for c in rows
        ]

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
        conditions = await self._build_conditions(
            hospital_id=hospital_id,
            doctor_id=doctor_id,
            case_no=case_no,
            patient_name=patient_name,
            doctor_name=doctor_name,
            status=status,
            start_time=start_time,
            end_time=end_time,
        )

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

        # 关联心电图诊断记录（图片 / AI 诊断 / 协同总结），供 Web 详情页展示
        ecg_records: list[dict] = []
        try:
            ecg_rows = (
                await self.db.execute(
                    select(EcgConsultModel)
                    .where(EcgConsultModel.case_id == id)
                    .order_by(EcgConsultModel.create_time.desc())
                )
            ).scalars().all()
            for r in ecg_rows:
                ecg_records.append(
                    {
                        "id": r.id,
                        "image_path": _cpx_abs_static_url(r.image_path),
                        "ai_diagnosis": r.ai_diagnosis,
                        "ai_summary": r.ai_summary,
                        "feedback": r.feedback,
                        "status": r.status,
                        "create_time": r.create_time.isoformat() if r.create_time else None,
                    }
                )
        except Exception:
            ecg_records = []

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
            "ecg_records": ecg_records,
        }

    async def timeline(self, *, id: int) -> dict:
        """救治时间轴：时间节点时间线 + 关键质控指标（管理员可查看任意病例）。"""
        case = await self.db.get(CaseRecordModel, id)
        if not case:
            raise CustomException(msg="病例不存在")
        detail = (
            await self.db.execute(select(CaseDetailModel).where(CaseDetailModel.case_id == id))
        ).scalars().first()
        form_data = detail.form_data or {} if detail else {}

        nodes = []
        for code, name in TIMELINE_NODES:
            raw = form_data.get(code)
            dt = _cpx_parse_time(raw)
            nodes.append({
                "code": code,
                "name": name,
                "value": raw,
                "time": dt.strftime("%Y-%m-%d %H:%M") if dt else None,
            })

        metrics = []
        for m in QUALITY_METRICS:
            start = _cpx_parse_time(form_data.get(m["start"]))
            end = _cpx_parse_time(form_data.get(m["end"]))
            diff = _cpx_diff_minutes(start, end)
            status = "n/a"
            if diff is not None:
                status = "pass" if (m["limit"] is None or diff <= m["limit"]) else "fail"
            metrics.append({
                "key": m["key"],
                "name": m["name"],
                "desc": m["desc"],
                "start": m["start"],
                "end": m["end"],
                "limit": m["limit"],
                "minutes": diff,
                "status": status,
            })

        return {
            "case_no": case.case_no,
            "patient_name": case.patient_name,
            "diagnose_type": case.diagnose_type,
            "nodes": nodes,
            "metrics": metrics,
        }

    async def analysis(self, *, id: int) -> dict:
        """单病例分析：对照质控指标逐项校验（达标/不达标/不适用）+ 必填缺失清单。"""
        case = await self.db.get(CaseRecordModel, id)
        if not case:
            raise CustomException(msg="病例不存在")
        detail = (
            await self.db.execute(select(CaseDetailModel).where(CaseDetailModel.case_id == id))
        ).scalars().first()
        form_data = detail.form_data or {} if detail else {}

        items = []
        for m in QUALITY_METRICS:
            start = _cpx_parse_time(form_data.get(m["start"]))
            end = _cpx_parse_time(form_data.get(m["end"]))
            diff = _cpx_diff_minutes(start, end)
            status = "n/a"
            if start is None or end is None:
                status = "n/a"
            elif m["limit"] is not None and diff is not None and diff <= m["limit"]:
                status = "pass"
            elif m["limit"] is None:
                status = "info"
            else:
                status = "fail"
            items.append({
                "key": m["key"],
                "name": m["name"],
                "desc": m["desc"],
                "limit": m["limit"],
                "minutes": diff,
                "status": status,
            })

        missing = []
        for f in FIELDS:
            if f.get("required") == 1:
                v = form_data.get(f["code"])
                if v in (None, ""):
                    missing.append({"field_code": f["code"], "field_name": f["name"], "tab": f.get("tab")})

        return {
            "case_no": case.case_no,
            "patient_name": case.patient_name,
            "diagnose_type": case.diagnose_type,
            "items": items,
            "missing_required": missing,
        }

    async def followup(self, *, id: int) -> dict:
        """病例随访记录详情（管理员可查看任意病例的随访，按随访计划月、应随访日期排序）。"""
        case = await self.db.get(CaseRecordModel, id)
        if not case:
            raise CustomException(msg="病例不存在")
        rows = (
            await self.db.execute(
                select(FollowUpModel, UserAccountModel.real_name)
                .outerjoin(UserAccountModel, UserAccountModel.id == FollowUpModel.doctor_id)
                .where(FollowUpModel.case_id == id)
                .order_by(FollowUpModel.plan_month, FollowUpModel.due_date)
            )
        ).all()
        items = []
        for fu, doctor_name in rows:
            # App 端完整随访表单（form_data JSON 展开；空/损坏 → None）
            ext_data = None
            raw_data = (fu.form_data or "").strip()
            if raw_data and raw_data != "{}":
                try:
                    parsed = json.loads(raw_data)
                    if isinstance(parsed, dict):
                        ext_data = parsed
                except (ValueError, TypeError):
                    ext_data = None
            if isinstance(ext_data, dict) and ext_data.get("ecg_image"):
                ext_data["ecg_image"] = _cpx_abs_static_url(str(ext_data["ecg_image"]))
            items.append({
                "id": fu.id,
                "case_id": fu.case_id,
                "patient_name": fu.patient_name,
                "doctor_id": fu.doctor_id,
                "doctor_name": doctor_name,
                "plan_month": fu.plan_month,
                "due_date": fu.due_date.isoformat() if fu.due_date else None,
                "status": fu.status,
                "follow_date": fu.follow_date.isoformat() if fu.follow_date else None,
                "follow_status": fu.follow_status,
                "survival_status": fu.survival_status,
                "risk_control": fu.risk_control,
                "medication": fu.medication,
                "remark": fu.remark,
                "create_time": fu.create_time.isoformat() if fu.create_time else None,
                "update_time": fu.update_time.isoformat() if fu.update_time else None,
                "form_data": ext_data,
            })
        return {
            "case_no": case.case_no,
            "patient_name": case.patient_name,
            "total": len(items),
            "items": items,
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
