# -*- coding: utf-8 -*-
"""病例审核服务：工作台统计 / 待审核列表 / 审核详情与校验 / 通过 / 驳回 / 审核记录。

校验规则：
- 数据完整性：模板必填字段（required_flag=1）在 form_data 中必须非空。
- 时间逻辑：按救治流程顺序比较 TIMELINE_CORE_CODES（发病 → 到达大门 → 首份心电图 → 球囊开通）。
  字段不存在时跳过对应比较；存在但空字符串时跳过。**校验结果仅作提示，不阻断审核通过。**
"""

from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import CustomException

from app.plugin.module_cpx.auth.dependencies import BizAuth
from app.plugin.module_cpx.fields import TIMELINE_CORE_CODES, timeline_label
from app.plugin.module_cpx.models import (
    AuditRecordModel,
    CaseDetailModel,
    CaseRecordModel,
    FollowUpModel,
    TemplateFieldModel,
)

# 救治时间线约定的字段编码（单一权威源见 fields.TIMELINE_CORE_CODES，缺失则跳过逻辑校验）
TIMELINE_FIELDS = TIMELINE_CORE_CODES


class AuditService:
    """病例审核服务"""

    def __init__(self, auth: BizAuth, db: AsyncSession) -> None:
        self.auth = auth
        self.db = db

    def _hospital_condition(self):
        """审核员医院数据隔离。"""
        return CaseRecordModel.hospital_id == self.auth.user.hospital_id

    # ── 工作台统计 ──────────────────────────────────────────

    async def workbench(self) -> dict:
        hospital_id = self.auth.user.hospital_id
        pending = await self.db.execute(
            select(func.count())
            .select_from(CaseRecordModel)
            .where(self._hospital_condition(), CaseRecordModel.status == "submitted")
        )
        pending_count = pending.scalar() or 0

        today = datetime.now().date()
        today_start = datetime.combine(today, datetime.min.time())
        today_end = today_start + timedelta(days=1)
        today_audit = await self.db.execute(
            select(func.count())
            .select_from(AuditRecordModel)
            .join(CaseRecordModel, CaseRecordModel.id == AuditRecordModel.case_id)
            .where(
                self._hospital_condition(),
                AuditRecordModel.audit_time >= today_start,
                AuditRecordModel.audit_time < today_end,
            )
        )
        today_audit_count = today_audit.scalar() or 0

        pass_count = await self._count_audit_result("pass")
        reject_count = await self._count_audit_result("reject")

        return {
            "pending_count": pending_count,
            "today_audit_count": today_audit_count,
            "pass_count": pass_count,
            "reject_count": reject_count,
        }

    async def _count_audit_result(self, result: str) -> int:
        count = await self.db.execute(
            select(func.count())
            .select_from(AuditRecordModel)
            .join(CaseRecordModel, CaseRecordModel.id == AuditRecordModel.case_id)
            .where(self._hospital_condition(), AuditRecordModel.audit_result == result)
        )
        return count.scalar() or 0

    # ── 待审核列表 ──────────────────────────────────────────

    async def pending(
        self, *, page_no: int, page_size: int, keyword: str | None, case_no: str | None
    ) -> dict:
        conditions = [self._hospital_condition(), CaseRecordModel.status == "submitted"]
        if keyword:
            conditions.append(CaseRecordModel.patient_name.like(f"%{keyword}%"))
        if case_no:
            conditions.append(CaseRecordModel.case_no.like(f"%{case_no}%"))

        total = await self.db.execute(
            select(func.count()).select_from(CaseRecordModel).where(*conditions)
        )
        total_count = total.scalar() or 0

        sql = (
            select(CaseRecordModel)
            .where(*conditions)
            .order_by(CaseRecordModel.create_time.asc())
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

    # ── 审核详情与校验 ──────────────────────────────────────

    async def detail(self, *, case_id: int) -> dict:
        case = await self._get_hospital_case(case_id)

        detail = (
            await self.db.execute(select(CaseDetailModel).where(CaseDetailModel.case_id == case_id))
        ).scalars().first()

        fields = []
        if detail:
            result = await self.db.execute(
                select(TemplateFieldModel)
                .where(TemplateFieldModel.template_id == detail.template_id)
                .order_by(TemplateFieldModel.sort_num.asc(), TemplateFieldModel.id.asc())
            )
            fields = [
                {
                    "id": f.id,
                    "field_name": f.field_name,
                    "field_code": f.field_code,
                    "field_type": f.field_type,
                    "field_options": f.field_options,
                    "required_flag": f.required_flag,
                    "sort_num": f.sort_num,
                }
                for f in result.scalars().all()
            ]

        form_data = detail.form_data or {} if detail else {}
        checks = self._validate(form_data, fields)

        audits = (
            await self.db.execute(
                select(AuditRecordModel)
                .where(AuditRecordModel.case_id == case_id)
                .order_by(AuditRecordModel.audit_time.desc())
            )
        ).scalars().all()

        return {
            "id": case.id,
            "case_no": case.case_no,
            "patient_name": case.patient_name,
            "gender": case.gender,
            "age": case.age,
            "phone": case.phone,
            "hospital_name": case.hospital.hospital_name if case.hospital else None,
            "doctor_name": case.doctor.real_name if case.doctor else None,
            "status": case.status,
            "create_time": case.create_time.isoformat() if case.create_time else None,
            "template_id": detail.template_id if detail else None,
            "template_name": detail.template.template_name if detail and detail.template else None,
            "fields": fields,
            "form_data": form_data,
            "checks": checks,
            "audit_records": [
                {
                    "id": a.id,
                    "auditor_name": a.auditor.real_name if a.auditor else None,
                    "auditor_hospital_name": (
                        a.auditor.hospital.hospital_name if a.auditor and a.auditor.hospital else None
                    ),
                    "audit_result": a.audit_result,
                    "audit_comment": a.audit_comment,
                    "audit_time": a.audit_time.isoformat() if a.audit_time else None,
                }
                for a in audits
            ],
        }

    def _validate(self, form_data: dict, fields: list[dict]) -> dict:
        """返回完整性检查与时间逻辑检查结果。"""
        form_data = form_data or {}
        missing_required = []
        for f in fields:
            if f["required_flag"] == 1:
                value = form_data.get(f["field_code"])
                if value is None or (isinstance(value, str) and not value.strip()):
                    missing_required.append({"field_name": f["field_name"], "field_code": f["field_code"]})

        time_issues = []
        times: list[tuple[str, str, object]] = []
        for code in TIMELINE_FIELDS:
            value = form_data.get(code)
            if value not in (None, ""):
                times.append((code, self._label(code), value))

        for i in range(len(times) - 1):
            cur_code, cur_label, cur_val = times[i]
            nxt_code, nxt_label, nxt_val = times[i + 1]
            cur_t = self._parse_time(cur_val)
            nxt_t = self._parse_time(nxt_val)
            if cur_t and nxt_t and cur_t > nxt_t:
                time_issues.append(f"{cur_label}（{cur_val}）晚于 {nxt_label}（{nxt_val}）")

        return {
            "complete": len(missing_required) == 0,
            "missing_required": missing_required,
            "time_ok": len(time_issues) == 0,
            "time_issues": time_issues,
        }

    @staticmethod
    def _label(code: str) -> str:
        # 统一从 fields.TIMELINE_NODES 取名，避免各处硬编码中文导致提示与实际字段不符
        return timeline_label(code)

    @staticmethod
    def _parse_time(value) -> datetime | None:
        """宽容解析时间字符串。"""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        text = str(value).strip().replace("T", " ")
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d", "%Y/%m/%d %H:%M:%S", "%Y/%m/%d"):
            try:
                return datetime.strptime(text, fmt)
            except ValueError:
                continue
        return None

    # ── 审核操作 ────────────────────────────────────────────

    async def approve(self, *, case_id: int, audit_comment: str | None) -> dict:
        case = await self._get_hospital_case(case_id)
        if case.status != "submitted":
            raise CustomException(msg="该病例不在待审核状态，无法通过")
        case.status = "approved"
        self.db.add(case)
        record = AuditRecordModel(
            case_id=case_id,
            auditor_id=self.auth.user.id,
            audit_result="pass",
            audit_comment=audit_comment,
            audit_time=datetime.now(),
        )
        self.db.add(record)

        # 审核通过 → 自动将病例填入随访档案，生成 1/3/6/12 月随访计划（幂等：已有随访则跳过）
        await self._ensure_followups(case)

        await self.db.flush()
        return {"id": case.id, "status": case.status}

    async def reject(self, *, case_id: int, audit_comment: str) -> dict:
        case = await self._get_hospital_case(case_id)
        if case.status != "submitted":
            raise CustomException(msg="该病例不在待审核状态，无法驳回")
        case.status = "rejected"
        self.db.add(case)
        record = AuditRecordModel(
            case_id=case_id,
            auditor_id=self.auth.user.id,
            audit_result="reject",
            audit_comment=audit_comment,
            audit_time=datetime.now(),
        )
        self.db.add(record)
        await self.db.flush()
        return {"id": case.id, "status": case.status}

    # ── 审核记录 ────────────────────────────────────────────

    async def history(self, *, page_no: int, page_size: int, case_no: str | None) -> dict:
        """当前审核员所在医院的审核记录。"""
        conditions = [
            AuditRecordModel.case_id.in_(
                select(CaseRecordModel.id).where(self._hospital_condition())
            )
        ]
        if case_no:
            conditions.append(CaseRecordModel.case_no.like(f"%{case_no}%"))
        total = await self.db.execute(
            select(func.count()).select_from(AuditRecordModel).where(*conditions)
        )
        total_count = total.scalar() or 0

        sql = (
            select(AuditRecordModel, CaseRecordModel)
            .join(CaseRecordModel, CaseRecordModel.id == AuditRecordModel.case_id)
            .where(*conditions)
            .order_by(AuditRecordModel.audit_time.desc())
            .offset((page_no - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(sql)
        rows = result.all()

        items = [
            {
                "id": a.id,
                "case_id": a.case_id,
                "case_no": c.case_no,
                "patient_name": c.patient_name,
                "auditor_name": a.auditor.real_name if a.auditor else None,
                "audit_result": a.audit_result,
                "audit_comment": a.audit_comment,
                "audit_time": a.audit_time.isoformat() if a.audit_time else None,
            }
            for a, c in rows
        ]
        return {
            "page_no": page_no,
            "page_size": page_size,
            "total": total_count,
            "has_next": page_no * page_size < total_count,
            "items": items,
        }

    async def update_record(self, *, record_id: int, audit_result: str, audit_comment: str | None) -> dict:
        """修改一条审核记录（结果+意见），并同步病例审核状态。"""
        if audit_result not in ("pass", "reject"):
            raise CustomException(msg="审核结果不合法")
        record = await self.db.get(AuditRecordModel, record_id)
        if not record:
            raise CustomException(msg="审核记录不存在")
        case = await self._get_hospital_case(record.case_id)
        if case.status == "submitted":
            raise CustomException(msg="病例仍处于待审核状态，请直接在待审核列表中处理")

        record.audit_result = audit_result
        record.audit_comment = audit_comment
        record.audit_time = datetime.now()
        self.db.add(record)

        case.status = "approved" if audit_result == "pass" else "rejected"
        self.db.add(case)
        # 改为通过后同样补建随访计划（幂等）；驳回时不生成
        if case.status == "approved":
            await self._ensure_followups(case)
        await self.db.flush()
        return {"id": record.id, "case_id": case.id, "status": case.status, "audit_result": audit_result}

    # ── 辅助 ────────────────────────────────────────────────

    async def _followup_base_date(self, case: CaseRecordModel):
        """随访起算日：优先取出院日期（form_data.discharge_date），取不到时退回病例时间。

        说明：原先直接用 case.update_time 作基准，而该字段会随病例任意修改而变动，
        导致随访到期日漂移（历史数据里出现过 1 月随访到期日早于出院日期的情况）。
        """
        res = await self.db.execute(
            select(CaseDetailModel).where(CaseDetailModel.case_id == case.id)
        )
        detail = res.scalars().first()
        form_data = detail.form_data or {} if detail else {}
        raw = form_data.get("discharge_date") or form_data.get("出院日期")
        if raw:
            try:
                return datetime.strptime(str(raw)[:10], "%Y-%m-%d")
            except ValueError:
                pass
        return case.update_time or case.create_time or datetime.now()

    async def _ensure_followups(self, case: CaseRecordModel) -> None:
        """审核通过后确保该病例存在 1/3/6/12 月随访计划（幂等：已有随访则跳过）。"""
        exists = await self.db.execute(
            select(FollowUpModel.id).where(FollowUpModel.case_id == case.id)
        )
        if exists.scalars().first():
            return
        base = await self._followup_base_date(case)
        for month in (1, 3, 6, 12):
            self.db.add(
                FollowUpModel(
                    case_id=case.id,
                    patient_name=case.patient_name,
                    hospital_id=case.hospital_id,
                    doctor_id=case.doctor_id,
                    plan_month=month,
                    due_date=base + timedelta(days=month * 30),
                    status="pending",
                )
            )

    async def _get_hospital_case(self, case_id: int) -> CaseRecordModel:
        case = await self.db.get(CaseRecordModel, case_id)
        if not case:
            raise CustomException(msg="病例不存在")
        if case.hospital_id != self.auth.user.hospital_id:
            raise CustomException(msg="无权限操作该病例", code=10403, status_code=403)
        return case
