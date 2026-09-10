# -*- coding: utf-8 -*-
"""医生端服务：工作台统计 / 模板下发 / 建档 / 动态表单保存 / 提交审核 / 我的病例 / 详情。

数据隔离：医生仅能访问本人创建（doctor_id == 当前用户）且属于本院的病例。
状态流转：draft(草稿) → submitted(待审核) → approved(通过) / rejected(驳回) → (驳回后) draft 或直接重提。
"""

import json
import random
from datetime import date, datetime, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.setting import settings
from app.core.exceptions import CustomException
from app.core.signed_url import sign_static_url
from app.utils.password_util import PwdUtil

from app.plugin.module_cpx.auth.dependencies import BizAuth
from app.plugin.module_cpx.fields import (
    COME_TYPES,
    DIAGNOSE_TYPES,
    FIELDS,
    FIELDS_BY_CODE,
    QUALITY_METRICS,
    TABS,
    TIMELINE_NODES,
)
from app.plugin.module_cpx.models import (
    AuditRecordModel,
    CaseDetailModel,
    CaseRecordModel,
    EcgConsultModel,
    FollowUpModel,
    HospitalModel,
    MeetingRecordModel,
    ReportTemplateModel,
    TemplateFieldModel,
    TreatmentUnitModel,
    UserAccountModel,
)

# 救治时间线约定的字段编码（按救治流程顺序，缺失则跳过逻辑校验）
TIMELINE_FIELDS = ["onset_time", "arrive_gate_time", "first_ecg_time", "balloon_time"]

EDITABLE_STATUS = ("draft", "rejected")  # 仅草稿/驳回状态允许修改与重提


class DoctorService:
    """医生端服务"""

    def __init__(self, auth: BizAuth, db: AsyncSession) -> None:
        self.auth = auth
        self.db = db

    # ── 数据隔离 ──────────────────────────────────────────

    def _own_condition(self):
        """医生仅本人病例。"""
        return CaseRecordModel.doctor_id == self.auth.user.id

    async def _get_own_case(self, case_id: int) -> CaseRecordModel:
        case = await self.db.get(CaseRecordModel, case_id)
        if not case:
            raise CustomException(msg="病例不存在")
        if case.doctor_id != self.auth.user.id:
            raise CustomException(msg="无权访问该病例", code=10403, status_code=403)
        return case

    # ── 工作台统计 ────────────────────────────────────────

    async def stats(self) -> dict:
        """今日新增 / 草稿 / 待审核 / 已通过 / 驳回。"""
        today_start = datetime.combine(datetime.now().date(), datetime.min.time())

        async def count(*conds) -> int:
            res = await self.db.execute(
                select(func.count()).select_from(CaseRecordModel).where(self._own_condition(), *conds)
            )
            return res.scalar() or 0

        return {
            "today_new": await count(CaseRecordModel.create_time >= today_start),
            "draft": await count(CaseRecordModel.status == "draft"),
            "pending": await count(CaseRecordModel.status == "submitted"),
            "approved": await count(CaseRecordModel.status == "approved"),
            "rejected": await count(CaseRecordModel.status == "rejected"),
        }

    # ── 模板下发 ──────────────────────────────────────────

    async def templates(self) -> list[dict]:
        """已发布且启用的模板（含字段定义，供动态表单渲染）。"""
        sql = (
            select(ReportTemplateModel)
            .where(ReportTemplateModel.published == 1, ReportTemplateModel.status == 1)
            .order_by(ReportTemplateModel.id.desc())
        )
        result = await self.db.execute(sql)
        templates = result.scalars().all()

        items = []
        for t in templates:
            fields = sorted(t.fields or [], key=lambda f: (f.sort_num or 0, f.id))
            items.append(
                {
                    "id": t.id,
                    "template_name": t.template_name,
                    "version": t.version,
                    "fields": [
                        {
                            "id": f.id,
                            "field_name": f.field_name,
                            "field_code": f.field_code,
                            "field_type": f.field_type,
                            "field_options": f.field_options,
                            "required_flag": f.required_flag,
                            "sort_num": f.sort_num,
                        }
                        for f in fields
                    ],
                }
            )
        return items

    # ── 建档 ──────────────────────────────────────────────

    async def create(self, data) -> dict:
        """患者快速建档：生成病例编号，创建草稿病例。"""
        template = await self.db.get(ReportTemplateModel, data.template_id)
        if not template or template.published != 1 or template.status != 1:
            raise CustomException(msg="模板不存在或未发布")

        # 解析日期字段
        first_contact = None
        if getattr(data, "first_contact_time", None):
            try:
                first_contact = datetime.strptime(data.first_contact_time, "%Y-%m-%d %H:%M")
            except ValueError:
                first_contact = datetime.strptime(data.first_contact_time, "%Y-%m-%d %H:%M:%S")

        birth = None
        if getattr(data, "birth_date", None):
            birth = datetime.strptime(data.birth_date, "%Y-%m-%d")

        case_no = await self._gen_case_no()
        case = CaseRecordModel(
            case_no=case_no,
            hospital_id=self.auth.user.hospital_id,
            doctor_id=self.auth.user.id,
            patient_name=data.patient_name,
            gender=data.gender,
            age=data.age,
            phone=data.phone,
            first_contact_time=first_contact,
            id_type=getattr(data, "id_type", None),
            id_number=getattr(data, "id_number", None),
            birth_date=birth,
            onset_address=getattr(data, "onset_address", None),
            detail_address=getattr(data, "detail_address", None),
            insurance_type=getattr(data, "insurance_type", None),
            insurance_no=getattr(data, "insurance_no", None),
            come_type=getattr(data, "come_type", None),
            diagnose_type=getattr(data, "diagnose_type", None),
            status="draft",
        )
        self.db.add(case)
        await self.db.flush()

        detail = CaseDetailModel(
            case_id=case.id,
            template_id=data.template_id,
            form_data={},
        )
        self.db.add(detail)
        await self.db.flush()

        return {"id": case.id, "case_no": case.case_no}

    async def _gen_case_no(self) -> str:
        """生成唯一病例编号：CASE + yyyymmdd + 4位序号（同日内递增，冲突随机重试）。"""
        now = datetime.now()
        prefix = f"CASE{now.strftime('%Y%m%d')}"

        res = await self.db.execute(
            select(func.count()).select_from(CaseRecordModel).where(
                CaseRecordModel.case_no.like(f"{prefix}%")
            )
        )
        seq = (res.scalar() or 0) + 1

        for _ in range(5):
            candidate = f"{prefix}{seq:04d}"
            exists = await self.db.execute(
                select(CaseRecordModel.id).where(CaseRecordModel.case_no == candidate)
            )
            if not exists.scalars().first():
                return candidate
            seq += random.randint(1, 7)
        raise CustomException(msg="病例编号生成失败，请重试")

    # ── 基础信息修改 ──────────────────────────────────────

    async def update(self, *, id: int, data) -> dict:
        case = await self._get_own_case(id)
        if case.status not in EDITABLE_STATUS:
            raise CustomException(msg="当前状态不可修改基础信息", status_code=400)
        payload = data.model_dump(exclude_unset=True)
        for key, value in payload.items():
            setattr(case, key, value)
        self.db.add(case)
        await self.db.flush()
        return {"id": case.id, "case_no": case.case_no, "status": case.status}

    # ── 动态表单保存（草稿）────────────────────────────────

    async def save_form(self, *, id: int, template_id: int, form_data: dict) -> dict:
        case = await self._get_own_case(id)
        if case.status not in EDITABLE_STATUS:
            raise CustomException(msg="当前状态不可编辑，仅草稿/驳回可修改", status_code=400)
        detail = (
            await self.db.execute(select(CaseDetailModel).where(CaseDetailModel.case_id == id))
        ).scalars().first()
        if not detail:
            detail = CaseDetailModel(case_id=id, template_id=template_id, form_data={})
            self.db.add(detail)
        else:
            detail.template_id = template_id
            detail.form_data = form_data
            detail.update_time = datetime.now()
        self.db.add(detail)
        await self.db.flush()
        return {"id": case.id, "case_no": case.case_no, "status": case.status}

    # ── 提交审核 ──────────────────────────────────────────

    async def submit(self, *, id: int) -> dict:
        """提交审核：按该病例所用模板的必填字段做完整性校验 + 救治时间逻辑校验。"""
        case = await self._get_own_case(id)
        if case.status not in EDITABLE_STATUS:
            raise CustomException(msg="当前状态不可提交审核", status_code=400)

        detail = (
            await self.db.execute(select(CaseDetailModel).where(CaseDetailModel.case_id == id))
        ).scalars().first()
        if not detail:
            raise CustomException(msg="请先填写病例表单")

        # 模板驱动校验：按该病例模板的 required_flag=1 字段校验
        tpl_fields = await self._template_fields(detail.template_id)
        validate_fields = [
            {
                "field_name": f["field_name"],
                "field_code": f["field_code"],
                "required_flag": 1,
            }
            for f in tpl_fields
            if f["required_flag"] == 1
        ]
        # 若模板无可校验必填字段，回退到胸痛标准字典
        if not validate_fields:
            validate_fields = [
                {"field_name": f["name"], "field_code": f["code"], "required_flag": 1}
                for f in FIELDS
                if f.get("required") == 1
            ]

        checks = self._validate(detail.form_data or {}, validate_fields)
        if not checks["complete"] or not checks["time_ok"]:
            problems = [f"必填「{m['field_name']}」未填写" for m in checks["missing_required"]]
            problems += checks["time_issues"]
            raise CustomException(msg="数据校验未通过：" + "；".join(problems))

        case.status = "submitted"
        self.db.add(case)
        await self.db.flush()
        return {"id": case.id, "case_no": case.case_no, "status": case.status}

    async def _template_fields(self, template_id: int) -> list[dict]:
        res = await self.db.execute(
            select(TemplateFieldModel)
            .where(TemplateFieldModel.template_id == template_id)
            .order_by(TemplateFieldModel.tab_order.asc(), TemplateFieldModel.sort_num.asc(), TemplateFieldModel.id.asc())
        )
        return [
            {
                "id": f.id,
                "field_name": f.field_name,
                "field_code": f.field_code,
                "field_type": f.field_type,
                "field_options": f.field_options,
                "required_flag": f.required_flag or 0,
                "sort_num": f.sort_num or 0,
                "tab_name": f.tab_name,
                "tab_order": f.tab_order or 0,
            }
            for f in res.scalars().all()
        ]

    def _validate(self, form_data: dict, fields: list[dict]) -> dict:
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
        return {
            "onset_time": "发病时间",
            "arrive_gate_time": "到达大门时间",
            "first_ecg_time": "首份心电图时间",
            "balloon_time": "球囊开通时间",
        }.get(code, code)

    @staticmethod
    def _parse_time(value) -> datetime | None:
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

    # ── 我的病例列表 ──────────────────────────────────────

    async def my_list(
        self,
        *,
        page_no: int,
        page_size: int,
        status: str | None,
        keyword: str | None,
        start_time: str | None,
        end_time: str | None,
        diagnose_type: str | None,
        come_type: str | None,
    ) -> dict:
        conditions = [self._own_condition()]
        if status:
            conditions.append(CaseRecordModel.status == status)
        if diagnose_type:
            conditions.append(CaseRecordModel.diagnose_type == diagnose_type)
        if come_type:
            conditions.append(CaseRecordModel.come_type == come_type)
        if keyword:
            kw = f"%{keyword}%"
            from sqlalchemy import or_
            conditions.append(
                or_(
                    CaseRecordModel.patient_name.like(kw),
                    CaseRecordModel.case_no.like(kw),
                )
            )
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
            .order_by(CaseRecordModel.update_time.desc(), CaseRecordModel.id.desc())
            .offset((page_no - 1) * page_size)
            .limit(page_size)
        )
        rows = (await self.db.execute(sql)).scalars().all()

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
                "status": c.status,
                "create_time": c.create_time.isoformat() if c.create_time else None,
                "update_time": c.update_time.isoformat() if c.update_time else None,
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

    # ── 病例详情（含审核反馈）──────────────────────────────

    async def detail(self, *, id: int) -> dict:
        case = await self._get_own_case(id)
        detail = (
            await self.db.execute(select(CaseDetailModel).where(CaseDetailModel.case_id == id))
        ).scalars().first()

        fields = await self._template_fields(detail.template_id) if detail else []
        audits = (
            await self.db.execute(
                select(AuditRecordModel)
                .where(AuditRecordModel.case_id == id)
                .order_by(AuditRecordModel.audit_time.desc())
            )
        ).scalars().all()

        ecg_rows = (
            await self.db.execute(
                select(EcgConsultModel)
                .where(EcgConsultModel.case_id == id)
                .order_by(EcgConsultModel.create_time.desc())
            )
        ).scalars().all()
        ecg_records = [
            {
                "id": e.id,
                "case_id": e.case_id,
                "image_path": e.image_path,
                "status": e.status,
                "ai_diagnosis": e.ai_diagnosis,
                "ai_summary": e.ai_summary,
                "feedback": e.feedback,
                "create_time": e.create_time.isoformat() if e.create_time else None,
            }
            for e in ecg_rows
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
            "id_type": case.id_type,
            "id_number": case.id_number,
            "birth_date": case.birth_date.strftime("%Y-%m-%d") if case.birth_date else None,
            "onset_address": case.onset_address,
            "detail_address": case.detail_address,
            "insurance_type": case.insurance_type,
            "insurance_no": case.insurance_no,
            "first_contact_time": case.first_contact_time.strftime("%Y-%m-%d %H:%M") if case.first_contact_time else None,
            "hospital_name": case.hospital.hospital_name if case.hospital else None,
            "status": case.status,
            "create_time": case.create_time.isoformat() if case.create_time else None,
            "update_time": case.update_time.isoformat() if case.update_time else None,
            "template_id": detail.template_id if detail else None,
            "template_name": detail.template.template_name if detail and detail.template else None,
            "fields": fields,
            "form_data": detail.form_data or {} if detail else {},
            "checks": self._validate(detail.form_data or {} if detail else {}, fields),
            "audit_records": [
                {
                    "id": a.id,
                    "auditor_name": a.auditor.real_name if a.auditor else None,
                    "audit_result": a.audit_result,
                    "audit_comment": a.audit_comment,
                    "audit_time": a.audit_time.isoformat() if a.audit_time else None,
                }
                for a in audits
            ],
            "ecg_records": ecg_records,
        }

    # ── 修改密码 ──────────────────────────────────────────

    async def delete_case(self, *, id: int) -> dict:
        """删除本人病例：级联删除 详情/审核记录/随访/心电；三会记录保留（case_id 置空）。"""
        case = await self._get_own_case(id)
        deleted = 0
        for model in (CaseDetailModel, AuditRecordModel, FollowUpModel, EcgConsultModel):
            rows = (
                await self.db.execute(select(model).where(model.case_id == id))
            ).scalars().all()
            for r in rows:
                await self.db.delete(r)
            deleted += len(rows)
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

    async def change_password(self, *, old_password: str, new_password: str) -> None:
        """修改本人登录密码（校验旧密码）。"""
        user = await self.db.get(UserAccountModel, self.auth.user.id)
        if not user:
            raise CustomException(msg="用户不存在")
        if not PwdUtil.verify_password(old_password, user.password):
            raise CustomException(msg="原密码错误")
        if len(new_password) < 6:
            raise CustomException(msg="新密码长度至少 6 位")
        user.password = PwdUtil.hash_password(new_password)
        self.db.add(user)
        await self.db.flush()

    # ── 字段字典 ──────────────────────────────────────────

    async def field_dict(self) -> dict:
        """返回胸痛标准字段字典（前端动态渲染表单/时间轴/分析）。"""
        return {
            "tabs": TABS,
            "fields": FIELDS,
            "diagnose_types": DIAGNOSE_TYPES,
            "come_types": COME_TYPES,
            "timeline_nodes": [{"code": c, "name": n} for c, n in TIMELINE_NODES],
            "quality_metrics": QUALITY_METRICS,
        }

    # ── 时间轴 / 单病例分析 ────────────────────────────────

    async def _case_form_data(self, case_id: int) -> dict:
        detail = (
            await self.db.execute(select(CaseDetailModel).where(CaseDetailModel.case_id == case_id))
        ).scalars().first()
        return detail.form_data or {} if detail else {}

    @staticmethod
    def _diff_minutes(t1: datetime | None, t2: datetime | None) -> int | None:
        if t1 and t2:
            return int((t2 - t1).total_seconds() // 60)
        return None

    async def timeline(self, *, id: int) -> dict:
        """救治时间轴：时间节点 + 关键指标计算。"""
        case = await self._get_own_case(id)
        form_data = await self._case_form_data(id)

        nodes = []
        for code, name in TIMELINE_NODES:
            raw = form_data.get(code)
            nodes.append({
                "code": code,
                "name": name,
                "value": raw,
                "time": self._parse_time(raw).strftime("%Y-%m-%d %H:%M") if self._parse_time(raw) else None,
            })

        def get_dt(code: str) -> datetime | None:
            return self._parse_time(form_data.get(code))

        metrics = []
        for m in QUALITY_METRICS:
            start = get_dt(m["start"])
            end = get_dt(m["end"])
            diff = self._diff_minutes(start, end)
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
        """单病例分析：对照质控指标逐项校验（达标/不达标/不适用）。"""
        case = await self._get_own_case(id)
        form_data = await self._case_form_data(id)

        def get_dt(code: str) -> datetime | None:
            return self._parse_time(form_data.get(code))

        items = []
        for m in QUALITY_METRICS:
            start = get_dt(m["start"])
            end = get_dt(m["end"])
            diff = self._diff_minutes(start, end)
            # 不适用：起止时间任一缺失
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

        # 必填字段缺失清单
        missing = []
        for f in FIELDS:
            if f.get("required") == 1:
                v = form_data.get(f["code"])
                if v in (None, ""):
                    missing.append({"field_code": f["code"], "field_name": f["name"], "tab": f["tab"]})

        return {
            "case_no": case.case_no,
            "patient_name": case.patient_name,
            "diagnose_type": case.diagnose_type,
            "items": items,
            "missing_required": missing,
        }

    # ── 随访管理 ──────────────────────────────────────────

    async def followup_generate(self) -> dict:
        """为已通过(approved)且未生成过随访计划的病例生成 1/3/6/12 月随访任务。"""
        cases = (
            await self.db.execute(
                select(CaseRecordModel).where(
                    self._own_condition(),
                    CaseRecordModel.status == "approved",
                )
            )
        ).scalars().all()

        generated = 0
        for c in cases:
            # 该病例是否已有随访计划
            exists = await self.db.execute(
                select(FollowUpModel.id).where(FollowUpModel.case_id == c.id)
            )
            if exists.scalars().first():
                continue
            base = c.update_time or c.create_time
            for month in (1, 3, 6, 12):
                self.db.add(
                    FollowUpModel(
                        case_id=c.id,
                        patient_name=c.patient_name,
                        hospital_id=c.hospital_id,
                        doctor_id=c.doctor_id,
                        plan_month=month,
                        due_date=base + timedelta(days=month * 30),
                        status="pending",
                    )
                )
                generated += 1
        await self.db.flush()
        return {"generated": generated}

    async def followup_list(self, *, page_no: int, page_size: int, status: str | None) -> dict:
        conditions = [FollowUpModel.doctor_id == self.auth.user.id]
        if status:
            conditions.append(FollowUpModel.status == status)

        total = await self.db.execute(
            select(func.count()).select_from(FollowUpModel).where(*conditions)
        )
        total_count = total.scalar() or 0

        sql = (
            select(FollowUpModel)
            .where(*conditions)
            .order_by(FollowUpModel.due_date.asc(), FollowUpModel.id.desc())
            .offset((page_no - 1) * page_size)
            .limit(page_size)
        )
        rows = (await self.db.execute(sql)).scalars().all()

        items = [
            {
                "id": f.id,
                "case_id": f.case_id,
                "case_no": f.case.case_no if f.case else None,
                "patient_name": f.patient_name,
                "plan_month": f.plan_month,
                "due_date": f.due_date.strftime("%Y-%m-%d") if f.due_date else None,
                "status": f.status,
                "follow_date": f.follow_date.strftime("%Y-%m-%d") if f.follow_date else None,
                "follow_status": f.follow_status,
                "survival_status": f.survival_status,
                "risk_control": f.risk_control,
                "medication": f.medication,
                "remark": f.remark,
            }
            for f in rows
        ]
        return {
            "page_no": page_no,
            "page_size": page_size,
            "total": total_count,
            "has_next": page_no * page_size < total_count,
            "items": items,
        }

    async def followup_groups(self, *, status: str | None) -> dict:
        """按患者（病例）聚合随访任务，每个患者一条分组（含 1/3/6/12 月随访子项及病例详情）。"""
        rows = (
            await self.db.execute(
                select(FollowUpModel)
                .where(FollowUpModel.doctor_id == self.auth.user.id)
                .order_by(FollowUpModel.case_id.asc(), FollowUpModel.plan_month.asc())
            )
        ).scalars().all()

        groups_map: dict[int, dict] = {}
        for f in rows:
            case = f.case
            if f.case_id not in groups_map:
                groups_map[f.case_id] = {
                    "case_id": f.case_id,
                    "patient_name": f.patient_name,
                    "case_no": case.case_no if case else None,
                    "hospital_id": f.hospital_id,
                    "come_type": case.come_type if case else None,
                    "diagnose_type": case.diagnose_type if case else None,
                    "gender": case.gender if case else None,
                    "age": case.age if case else None,
                    "phone": case.phone if case else None,
                    "doctor_name": case.doctor.real_name if case and case.doctor else None,
                    "followups": [],
                }
            groups_map[f.case_id]["followups"].append(
                {
                    "id": f.id,
                    "plan_month": f.plan_month,
                    "due_date": f.due_date.strftime("%Y-%m-%d") if f.due_date else None,
                    "status": f.status,
                    "follow_date": f.follow_date.strftime("%Y-%m-%d") if f.follow_date else None,
                    "follow_status": f.follow_status,
                    "survival_status": f.survival_status,
                }
            )

        groups = list(groups_map.values())

        # 状态筛选：保留含有目标任务状态的组
        if status:
            groups = [g for g in groups if any(t["status"] == status for t in g["followups"])]

        # 按最早应随访日期升序
        def _min_due(g: dict) -> str:
            ds = [t["due_date"] or "" for t in g["followups"]]
            return min(ds) if ds else "9999-99-99"

        groups.sort(key=_min_due)

        # ── 按参考截图补充病例详情与时间轴状态 ──
        today = date.today()
        case_ids = [g["case_id"] for g in groups]
        case_map: dict[int, CaseRecordModel] = {}
        detail_map: dict[int, CaseDetailModel] = {}
        if case_ids:
            case_rows = (await self.db.execute(select(CaseRecordModel).where(CaseRecordModel.id.in_(case_ids)))).scalars().all()
            case_map = {c.id: c for c in case_rows}
            detail_rows = (await self.db.execute(select(CaseDetailModel).where(CaseDetailModel.case_id.in_(case_ids)))).scalars().all()
            detail_map = {d.case_id: d for d in detail_rows}

        def _display_status(task_status: str, due_date_str: str | None) -> str:
            if task_status == "submitted":
                return "已随访"
            if due_date_str:
                try:
                    due = datetime.strptime(due_date_str, "%Y-%m-%d").date()
                    if due < today:
                        return "已过期"
                    if due <= today + timedelta(days=7):
                        return "需随访"
                    return "未开始"
                except ValueError:
                    pass
            return "未随访"

        for g in groups:
            c = case_map.get(g["case_id"])
            d = detail_map.get(g["case_id"])
            form_data = d.form_data or {} if d else {}

            discharge_date = form_data.get("discharge_date") or form_data.get("出院日期") or None
            inpatient_no = form_data.get("inpatient_no") or form_data.get("住院号") or None

            g["patient_name"] = c.patient_name if c else g.get("patient_name")
            g["gender"] = c.gender if c else None
            g["age"] = c.age if c else None
            g["phone"] = c.phone if c else None
            g["come_type"] = c.come_type if c else None
            g["diagnose_type"] = c.diagnose_type if c else None
            g["case_no"] = c.case_no if c else g.get("case_no")
            g["discharge_date"] = discharge_date
            g["inpatient_no"] = inpatient_no

            # 随访有效期：出院日期 ~ 12 月随访；无出院日期则取最早~最晚随访日期
            due_dates = [datetime.strptime(t["due_date"], "%Y-%m-%d").date() for t in g["followups"] if t.get("due_date")]
            if discharge_date:
                try:
                    valid_start = datetime.strptime(str(discharge_date), "%Y-%m-%d").date()
                except ValueError:
                    valid_start = min(due_dates) if due_dates else today
            else:
                valid_start = min(due_dates) if due_dates else today
            valid_end = max(due_dates) if due_dates else today
            g["valid_start"] = valid_start.isoformat()
            g["valid_end"] = valid_end.isoformat()

            for t in g["followups"]:
                t["display_status"] = _display_status(t["status"], t.get("due_date"))

        return {"total": len(groups), "items": groups}

    async def followup_detail(self, *, id: int) -> dict:
        """随访单条详情：随访全部字段（含扩展 form_data）+ 患者/病例上下文。"""
        follow = await self.db.get(FollowUpModel, id)
        if not follow:
            raise CustomException(msg="随访任务不存在")
        if follow.doctor_id != self.auth.user.id:
            raise CustomException(msg="无权查看该随访", code=10403, status_code=403)

        case = follow.case
        form_data: dict = {}
        if case:
            d = (
                await self.db.execute(
                    select(CaseDetailModel).where(CaseDetailModel.case_id == case.id)
                )
            ).scalars().first()
            form_data = d.form_data or {} if d else {}

        # 扩展字段（新 35 字段分组表单）
        ext: dict = {}
        if follow.form_data:
            try:
                ext = json.loads(follow.form_data)
            except (TypeError, ValueError):
                ext = {}

        base = {
            "id": follow.id,
            "case_id": follow.case_id,
            "case_no": case.case_no if case else None,
            "patient_name": follow.patient_name or (case.patient_name if case else None),
            "gender": case.gender if case else None,
            "age": case.age if case else None,
            "phone": case.phone if case else None,
            "come_type": case.come_type if case else None,
            "diagnose_type": case.diagnose_type if case else None,
            "inpatient_no": form_data.get("inpatient_no") or form_data.get("住院号") or None,
            "discharge_date": form_data.get("discharge_date") or form_data.get("出院日期") or None,
            "plan_month": follow.plan_month,
            "due_date": follow.due_date.strftime("%Y-%m-%d") if follow.due_date else None,
            "status": follow.status,
            "follow_date": follow.follow_date.strftime("%Y-%m-%d") if follow.follow_date else None,
            "follow_status": follow.follow_status,
            "survival_status": follow.survival_status,
            "risk_control": follow.risk_control,
            "medication": follow.medication,
            "remark": follow.remark,
            "create_time": follow.create_time.strftime("%Y-%m-%d %H:%M:%S") if follow.create_time else None,
            "update_time": follow.update_time.strftime("%Y-%m-%d %H:%M:%S") if follow.update_time else None,
        }
        # 扩展字段合并（基础字段优先，避免覆盖）
        return {**ext, **base}

    async def me(self) -> dict:
        """当前医生基本信息（用于顶部标题栏等）。"""
        return {
            "real_name": self.auth.user.real_name,
            "username": self.auth.user.username,
            "hospital_id": self.auth.user.hospital_id,
            "hospital_name": self.auth.user.hospital_name,
        }

    async def followup_submit(self, *, id: int, data) -> dict:
        follow = await self.db.get(FollowUpModel, id)
        if not follow:
            raise CustomException(msg="随访任务不存在")
        if follow.doctor_id != self.auth.user.id:
            raise CustomException(msg="无权操作该随访", code=10403, status_code=403)
        if follow.status == "submitted":
            raise CustomException(msg="该随访已提交")

        payload = data.model_dump(exclude_unset=True)

        # 必填校验（仅已随访；未随访走失访分支只填备注）
        if payload.get("follow_status") == "followed":
            for required, label in (
                ("info_channel", "信息获取途径"),
                ("survival_status", "随访状态"),
                ("current_condition", "目前状况"),
                ("cardiac_rehab", "加入心脏康复计划"),
                ("mace", "出院后主要心血管不良事件"),
            ):
                if not str(payload.get(required) or "").strip():
                    raise CustomException(msg=f"请填写{label}")

        # 扩展字段（除旧列外）→ form_data JSON
        legacy_cols = {"follow_date", "follow_status", "survival_status",
                       "risk_control", "medication", "remark"}
        ext = {k: v for k, v in payload.items()
               if k not in legacy_cols and v not in (None, "")}
        if ext:
            follow.form_data = json.dumps(ext, ensure_ascii=False)

        # 兼容写入旧列
        if payload.get("follow_date"):
            try:
                follow.follow_date = datetime.strptime(str(payload["follow_date"])[:10], "%Y-%m-%d")
            except ValueError:
                pass
        if "follow_status" in payload:
            follow.follow_status = payload["follow_status"]
        if "survival_status" in payload:
            follow.survival_status = payload["survival_status"]
        if "risk_control" in payload:
            follow.risk_control = payload["risk_control"]
        if "medication" in payload:
            follow.medication = payload["medication"]
        if "remark" in payload:
            follow.remark = payload["remark"]

        follow.status = "submitted"
        self.db.add(follow)
        await self.db.flush()
        return {"id": follow.id, "status": follow.status}

    # ── 数据分析 ──────────────────────────────────────────

    async def stats_overview(self, *, months: int = 6) -> dict:
        """数据概览（详细版）：累计/昨日/今日/本周/本月 + 诊断分布 + 状态分布 + 趋势
        + 随访统计 + 转诊统计 + 月度质控指标达标率。"""
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)

        async def count(*conds) -> int:
            res = await self.db.execute(
                select(func.count()).select_from(CaseRecordModel).where(self._own_condition(), *conds)
            )
            return res.scalar() or 0

        overview = {
            "total": await count(),
            "today_new": await count(CaseRecordModel.create_time >= today),
            "yesterday_new": await count(
                CaseRecordModel.create_time >= yesterday,
                CaseRecordModel.create_time < today,
            ),
            "week_new": await count(CaseRecordModel.create_time >= week_start),
            "month_new": await count(CaseRecordModel.create_time >= month_start),
        }

        # 诊断分布
        diag_rows = await self.db.execute(
            select(CaseRecordModel.diagnose_type, func.count())
            .where(self._own_condition(), CaseRecordModel.diagnose_type.is_not(None))
            .group_by(CaseRecordModel.diagnose_type)
        )
        diagnose_dist = [{"type": r[0], "count": r[1]} for r in diag_rows.all()]

        # 状态分布
        status_rows = await self.db.execute(
            select(CaseRecordModel.status, func.count())
            .where(self._own_condition())
            .group_by(CaseRecordModel.status)
        )
        status_dist = {r[0]: r[1] for r in status_rows.all()}

        # 近 30 天趋势（按天计数）
        trend = []
        start = today - timedelta(days=29)
        rows = await self.db.execute(
            select(func.date(CaseRecordModel.create_time), func.count())
            .where(self._own_condition(), CaseRecordModel.create_time >= start)
            .group_by(func.date(CaseRecordModel.create_time))
        )
        by_day = {str(r[0]): r[1] for r in rows.all()}
        for i in range(30):
            day = (start + timedelta(days=i)).strftime("%Y-%m-%d")
            trend.append({"date": day, "count": by_day.get(day, 0)})

        # 随访统计（1/3/6/12 月随访完成率）
        followup_stats = []
        for month in (1, 3, 6, 12):
            total = (
                await self.db.execute(
                    select(func.count()).select_from(FollowUpModel).where(
                        FollowUpModel.doctor_id == self.auth.user.id,
                        FollowUpModel.plan_month == month,
                    )
                )
            ).scalar() or 0
            done = (
                await self.db.execute(
                    select(func.count()).select_from(FollowUpModel).where(
                        FollowUpModel.doctor_id == self.auth.user.id,
                        FollowUpModel.plan_month == month,
                        FollowUpModel.status == "submitted",
                    )
                )
            ).scalar() or 0
            followup_stats.append({
                "month": f"{month}月",
                "total": total,
                "done": done,
                "rate": round(done / total * 100, 1) if total else None,
            })

        # 转诊统计（网络医院转诊）
        transfer_total = await count(CaseRecordModel.come_type == "转诊")
        transfer_cases = (
            await self.db.execute(
                select(CaseRecordModel)
                .where(self._own_condition(), CaseRecordModel.come_type == "转诊")
                .order_by(CaseRecordModel.create_time.desc())
                .limit(20)
            )
        ).scalars().all()
        transfer_list = [
            {
                "case_no": c.case_no,
                "patient_name": c.patient_name,
                "diagnose_type": c.diagnose_type,
                "status": c.status,
                "create_time": c.create_time.strftime("%Y-%m-%d") if c.create_time else None,
            }
            for c in transfer_cases
        ]

        # 月度质控指标达标率（近 N 月，按病例创建月份统计 D2W / FMC2ECG）
        metrics_monthly = []
        # 计算近 months 个月的月初列表（最新在前）
        month_starts = []
        cur = today.replace(day=1)
        for _ in range(months):
            month_starts.append(cur)
            cur = (cur - timedelta(days=1)).replace(day=1)
        month_starts.reverse()

        for m_start in month_starts:
            nxt = (m_start + timedelta(days=32)).replace(day=1)
            label = m_start.strftime("%Y-%m")
            month_cases = (
                await self.db.execute(
                    select(CaseRecordModel).where(
                        self._own_condition(),
                        CaseRecordModel.create_time >= m_start,
                        CaseRecordModel.create_time < nxt,
                    )
                )
            ).scalars().all()

            row: dict = {"month": label, "cases": len(month_cases)}
            for m in QUALITY_METRICS:
                if m["key"] not in ("D2W", "FMC2ECG"):
                    continue
                t = p = 0
                for c in month_cases:
                    form_data = await self._case_form_data(c.id)
                    s = self._parse_time(form_data.get(m["start"]))
                    e = self._parse_time(form_data.get(m["end"]))
                    diff = self._diff_minutes(s, e)
                    if diff is None:
                        continue
                    t += 1
                    if m["limit"] is not None and diff <= m["limit"]:
                        p += 1
                row[m["key"]] = round(p / t * 100, 1) if t else None
            metrics_monthly.append(row)

        return {
            "overview": overview,
            "diagnose_dist": diagnose_dist,
            "status_dist": status_dist,
            "trend": trend,
            "followup_stats": followup_stats,
            "transfer": {"total": transfer_total, "list": transfer_list},
            "metrics_monthly": metrics_monthly,
        }

    # ── 救治医院 ──────────────────────────────────────────

    async def units(self) -> list[dict]:
        """区域胸痛中心网络：所有启用医院及其是否开通智慧胸痛（以医院启用状态 hospital.status 为准）。"""
        hospitals = (
            await self.db.execute(
                select(HospitalModel).where(HospitalModel.status == 1).order_by(HospitalModel.id.asc())
            )
        ).scalars().all()

        # 已启用的救治单元 → 按医院计数（仅用于展示 unit_count，不参与开通判定）
        open_units = (
            await self.db.execute(
                select(TreatmentUnitModel.hospital_id, func.count(TreatmentUnitModel.id))
                .where(TreatmentUnitModel.status == 1)
                .group_by(TreatmentUnitModel.hospital_id)
            )
        ).all()
        open_map = {hid: cnt for hid, cnt in open_units}

        # 转诊病例数按医院聚合
        transfer_cases = (
            await self.db.execute(
                select(CaseRecordModel.hospital_id, func.count(CaseRecordModel.id))
                .where(CaseRecordModel.come_type == "转诊")
                .group_by(CaseRecordModel.hospital_id)
            )
        ).all()
        case_map = {hid: cnt for hid, cnt in transfer_cases}

        items = []
        for h in hospitals:
            opened = h.status == 1  # 以医院启用状态为准：web 启用哪家，app 即显示哪家已开通
            items.append(
                {
                    "hospital_id": h.id,
                    "hospital_name": h.hospital_name,
                    "hospital_level": h.hospital_level,
                    "city": h.city,
                    "opened": opened,
                    "unit_count": open_map.get(h.id, 0),
                    "case_count": case_map.get(h.id, 0),
                }
            )
        return items

    # ── 远程心电 AI 诊断与会诊 ─────────────────────────────

    @staticmethod
    def _abs_static_url(path: str | None) -> str | None:
        """统一后端存的图片/文件路径为可访问的 URL。

        后端 upload 接口返回的路径已带 /api/v1 前缀（如 /api/v1/static/uploads/...）；
        若再拼 ROOT_PATH+STATIC_URL 会变成 /api/v1/static/api/v1/static/... 重复前缀 → 404。
        - 空 → None
        - 已是 /api/v1/... 或 http(s):// → 原样返回
        - 其他相对路径 → 拼 ROOT_PATH + STATIC_URL 前缀
        """
        if not path:
            return None
        p = path.lstrip("/")
        if p.startswith("api/v1/") or p.startswith("http://") or p.startswith("https://"):
            return "/" + p
        return f"{settings.ROOT_PATH}{settings.STATIC_URL}/{p}"

    @staticmethod
    def _fallback_mock_diagnose(case: CaseRecordModel | None, form_data: dict | None) -> tuple[str, str]:
        """本地兜底诊断（真实 AI 接口不可用时使用）。返回 (diagnosis, summary)。"""
        info = []
        # 诊断类型优先从已填的 form_data 中取（医生填报表单时已选），回退到建档字段
        diag = (
            (form_data or {}).get("diagnose_type")
            or (case.diagnose_type if case else None)
            or "未分类"
        )
        age = case.age if case else None
        gender = case.gender if case else None
        come = case.come_type if case else None
        if gender and age is not None:
            info.append(f"{gender}，{age}岁")
        info.append(f"诊断：{diag}")
        if come:
            info.append(f"来院：{come}")
        onset = (form_data or {}).get("onset_time")
        if onset:
            info.append(f"发病：{onset}")

        # 诊断基调
        if "STEMI" in (diag or ""):
            tone = "提示急性 ST 段抬高型心肌梗死可能，请结合临床症状、肌钙蛋白与冠脉造影尽快明确诊断并启动再灌注治疗。"
            summary = "心电图呈急性 STEMI 样改变，建议立即启动院内绿色通道，监测生命体征并准备 PCI。"
        elif "NSTEMI" in (diag or ""):
            tone = "提示急性非 ST 段抬高型心肌梗死可能，需结合肌钙蛋白动态演变与 GRACE 评分综合评估。"
            summary = "心电图呈 NSTEMI 样改变，建议尽早完善高敏肌钙蛋白、危险分层与冠脉 CTA / 造影。"
        elif "UA" in (diag or "") or "不稳定心绞痛" in (diag or ""):
            tone = "提示不稳定型心绞痛可能，建议动态复查心电图与心肌损伤标志物。"
            summary = "心电图提示心肌缺血样改变，建议尽快完善心肌酶、肌钙蛋白与冠脉评估。"
        else:
            tone = "未见明显急性缺血改变；建议结合临床症状与其他检查综合判断。"
            summary = "心电图整体节律较稳定，建议持续监测并结合症状综合评估。"

        age_tip = ""
        if isinstance(age, int) and age >= 65:
            age_tip = "老年患者需注意合并症与药物耐受。"
        elif isinstance(age, int) and age < 45:
            age_tip = "年轻患者需排查家族史与危险因素。"

        diagnosis = "心电图AI辅助诊断结果（本地兜底）：\n" + "；".join(info) + "。" + tone + (age_tip or "")
        return diagnosis, summary

    @staticmethod
    async def _ecg_vision_findings(image_path: str | None) -> str | None:
        """用智谱视觉(glm-4v-flash)识别心电图图片，返回关键所见文本；无 Key 或失败返回 None。"""
        import base64 as _b64
        import mimetypes
        from pathlib import Path as _Path
        from urllib.parse import urlparse

        from app.config.path_conf import STATIC_DIR

        if not image_path or not settings.ZHIPU_API_KEY or settings.ZHIPU_API_KEY.startswith("sk-placeholder"):
            return None
        try:
            if image_path.startswith("data:"):
                data_uri = image_path
            else:
                path = image_path
                if "://" in path:
                    parsed = urlparse(path)
                    host = (parsed.hostname or "").lower()
                    if host in ("127.0.0.1", "localhost", "0.0.0.0", "::1") or host.startswith("192.168.") or host.startswith("10.") or host.startswith("172."):
                        path = parsed.path
                    else:
                        return None
                # 剥离静态文件签名等查询串（?exp=&sign=）与锚点，否则磁盘路径带 ? 会找不到文件
                path = path.split("?", 1)[0].split("#", 1)[0]
                if "/api/v1/static/" in path:
                    path = path.split("/api/v1/static/", 1)[1]
                elif "/static/" in path:
                    path = path.split("/static/", 1)[1]
                else:
                    return None
                fp = _Path(str(STATIC_DIR)) / path
                if not fp.exists():
                    return None
                mime = mimetypes.guess_type(str(fp))[0] or "image/jpeg"
                b64 = _b64.b64encode(fp.read_bytes()).decode()
                data_uri = f"data:{mime};base64,{b64}"
            prompt = (
                "你是心电图判读助手。请描述这张心电图的关键所见：节律、心率、ST段、T波、"
                "有无异常偏移或梗死样改变。只输出中文要点，不超过150字，不要解释。"
            )
            model = settings.ZHIPU_VISION_MODEL or "glm-4v-flash"
            import httpx
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    settings.ZHIPU_BASE_URL.rstrip("/") + "/chat/completions",
                    headers={"Authorization": f"Bearer {settings.ZHIPU_API_KEY}", "Content-Type": "application/json"},
                    json={
                        "model": model,
                        "messages": [{"role": "user", "content": [
                            {"type": "image_url", "image_url": {"url": data_uri, "detail": "high"}},
                            {"type": "text", "text": prompt},
                        ]}],
                        "max_tokens": 400,
                        "temperature": 0.1,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
            msg = ((data.get("choices") or [{}])[0].get("message") or {})
            text = (msg.get("content") or "").strip()
            if not text:
                text = (msg.get("reasoning_content") or "").strip()
            return text or None
        except Exception:
            return None

    @staticmethod
    async def _ai_diagnose(case: CaseRecordModel | None, form_data: dict | None, image_findings: str | None = None) -> tuple[str, str]:
        """调用 DeepSeek V4 Flash 生成心电图 AI 诊断意见 + 协同总结；接口异常时回退本地兜底。

        返回 (diagnosis, summary)。
        """
        import json as _json
        import re as _re

        # 未配置真实 Key → 直接用本地兜底
        if not settings.DEEPSEEK_API_KEY or settings.DEEPSEEK_API_KEY.startswith("sk-placeholder"):
            return DoctorService._fallback_mock_diagnose(case, form_data)

        info = []
        diag = (
            (form_data or {}).get("diagnose_type")
            or (case.diagnose_type if case else None)
            or "未分类"
        )
        age = case.age if case else None
        gender = case.gender if case else None
        come = case.come_type if case else None
        if gender and age is not None:
            info.append(f"{gender}，{age}岁")
        info.append(f"拟诊断：{diag}")
        if come:
            info.append(f"来院方式：{come}")
        onset = (form_data or {}).get("onset_time")
        if onset:
            info.append(f"发病时间：{onset}")
        patient_text = "；".join(info) if info else "未提供"

        ecg_part = f"\n心电图影像（智谱视觉识别）所见：{image_findings}\n" if image_findings else ""
        prompt = (
            "你是心血管内科心电图AI辅助诊断助手。请根据以下患者信息与心电图检查场景，"
            "给出专业、简洁的中文心电图AI辅助诊断意见（diagnosis）和供接收医院会诊医生参考的协同总结（summary）。\n"
            f"患者信息：{patient_text}{ecg_part}\n"
            "要求：诊断意见覆盖节律、ST段改变、可能诊断与建议；协同总结面向接收医院的会诊医生，"
            "给出明确的进一步检查/处置建议，100字以内。\n"
            "请严格只输出如下 JSON，不要输出任何其他内容：\n"
            '{"diagnosis": "心电图AI辅助诊断意见...", "summary": "协同总结（给接收医院）..."}'
        )
        try:
            import httpx

            _url = settings.DEEPSEEK_BASE_URL.rstrip("/") + "/chat/completions"
            _headers = {
                "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}",
                "Content-Type": "application/json",
            }
            # 关闭思考：推理模型（deepseek-v4-flash）的思考草稿会挤占 max_tokens，
            # 一旦被截断 content 会为空并静默回退到兜底诊断，故统一关闭；
            # 网关不认该参数（400）时去掉重试一次
            _body = {
                "model": settings.DEEPSEEK_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 4000,
                "temperature": 0.3,
                "thinking": {"type": "disabled"},
            }
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(_url, headers=_headers, json=_body)
                if resp.status_code == 400:
                    _body.pop("thinking", None)
                    resp = await client.post(_url, headers=_headers, json=_body)
                resp.raise_for_status()
                data = resp.json()
            msg = ((data.get("choices") or [{}])[0].get("message") or {})
            content = (msg.get("content") or "").strip()
            if not content:  # 推理型模型可能把正文放在 reasoning_content
                content = (msg.get("reasoning_content") or "").strip()
            if not content:
                return DoctorService._fallback_mock_diagnose(case, form_data)

            # 剥掉 ```json 代码块
            text = content.strip()
            if text.startswith("```"):
                text = _re.sub(r"^```(?:json)?\s*", "", text)
                text = _re.sub(r"\s*```$", "", text)
            obj = None
            try:
                obj = _json.loads(text)
            except Exception:
                # 从文本中提取 JSON 对象（推理过程可能混有思考内容）
                m = _re.search(r"\{.*\}", text, _re.S)
                if m:
                    try:
                        obj = _json.loads(m.group(0))
                    except Exception:
                        obj = None
            if isinstance(obj, dict) and (obj.get("diagnosis") or obj.get("summary")):
                diagnosis = str(obj.get("diagnosis") or "").strip()
                summary = str(obj.get("summary") or "").strip()
                if not diagnosis:
                    diagnosis = summary
                return diagnosis or "心电图AI辅助诊断结果：未见异常描述。", summary
            # 提取不到结构化结论 → 本地兜底，避免把推理过程当诊断结论
            return DoctorService._fallback_mock_diagnose(case, form_data)
        except Exception:
            return DoctorService._fallback_mock_diagnose(case, form_data)

    async def ecg_upload(self, *, case_id: int | None, image_path: str | None) -> dict:
        """上传心电图 → 自动生成 AI 诊断与协同总结 → 创建记录（status=uploaded）。"""
        case = None
        form_data: dict | None = None
        if case_id:
            case = await self.db.get(CaseRecordModel, case_id)
            if case and case.doctor_id != self.auth.user.id:
                raise CustomException(msg="仅可为自己创建的病例上传心电图")
            detail = (
                await self.db.execute(select(CaseDetailModel).where(CaseDetailModel.case_id == case_id))
            ).scalars().first()
            if detail:
                form_data = detail.form_data or {}
        image_findings = await DoctorService._ecg_vision_findings(image_path)
        diagnosis, summary = await self._ai_diagnose(case, form_data, image_findings=image_findings)
        info_snapshot = (
            {"patient_name": case.patient_name, "gender": case.gender, "age": case.age,
             "come_type": case.come_type, "diagnose_type": case.diagnose_type, "form_data": form_data}
            if case else {}
        )
        import json as _json
        record = EcgConsultModel(
            case_id=case_id,
            hospital_id=self.auth.user.hospital_id,
            doctor_id=self.auth.user.id,
            image_path=image_path,
            patient_info_json=_json.dumps(info_snapshot, ensure_ascii=False, default=str),
            ai_diagnosis=diagnosis,
            ai_summary=summary,
            status="uploaded",
        )
        self.db.add(record)
        await self.db.flush()
        return {
            "id": record.id,
            "diagnosis": diagnosis,
            "ai_summary": summary,
            "status": "uploaded",
        }

    async def ecg_list(self) -> dict:
        """我的所有相关心电记录（发起 + 接收），按 status 分组。"""
        conditions = or_(
            EcgConsultModel.hospital_id == self.auth.user.hospital_id,
            EcgConsultModel.target_hospital_id == self.auth.user.hospital_id,
        )
        rows = (
            await self.db.execute(
                select(EcgConsultModel)
                .where(conditions)
                .order_by(EcgConsultModel.update_time.desc(), EcgConsultModel.create_time.desc())
                .limit(100)
            )
        ).scalars().all()
        items: list[dict] = []
        for r in rows:
            is_initiator = r.hospital_id == self.auth.user.hospital_id
            items.append(
                {
                    "id": r.id,
                    "case_id": r.case_id,
                    "case_no": r.case.case_no if r.case else None,
                    "patient_name": r.case.patient_name if r.case else None,
                    "image_path": self._abs_static_url(r.image_path),
                    "status": r.status,
                    "is_initiator": is_initiator,
                    "ai_summary": r.ai_summary,
                    "feedback": r.feedback,
                    "target_hospital_name": (await self.db.get(HospitalModel, r.target_hospital_id)).hospital_name if r.target_hospital_id else None,
                    "create_time": r.create_time.isoformat() if r.create_time else None,
                    "feedback_time": r.feedback_time.isoformat() if r.feedback_time else None,
                }
            )
        return {"items": items}

    async def ecg_list_by_case(self, *, case_id: int) -> dict:
        """某病例的全部心电记录（供随访页「心电图」联动下拉）。"""
        rows = (
            await self.db.execute(
                select(EcgConsultModel)
                .where(EcgConsultModel.case_id == case_id)
                .order_by(EcgConsultModel.create_time.desc())
            )
        ).scalars().all()
        items = [
            {
                "id": r.id,
                "image_path": self._abs_static_url(r.image_path),
                "status": r.status,
                "ai_summary": r.ai_summary,
                "create_time": r.create_time.strftime("%Y-%m-%d %H:%M:%S") if r.create_time else None,
            }
            for r in rows
        ]
        return {"items": items}

    async def ecg_detail(self, *, id: int) -> dict:
        record = await self.db.get(EcgConsultModel, id)
        if not record:
            raise CustomException(msg="记录不存在")
        if record.hospital_id != self.auth.user.hospital_id and (
            not record.target_hospital_id or record.target_hospital_id != self.auth.user.hospital_id
        ):
            raise CustomException(msg="无权查看该记录")
        return {
            "id": record.id,
            "case_id": record.case_id,
            "case_no": record.case.case_no if record.case else None,
            "patient_name": record.case.patient_name if record.case else None,
            "image_path": self._abs_static_url(record.image_path),
            "patient_info_json": record.patient_info_json,
            "ai_diagnosis": record.ai_diagnosis,
            "ai_summary": record.ai_summary,
            "feedback": record.feedback,
            "feedback_time": record.feedback_time.isoformat() if record.feedback_time else None,
            "status": record.status,
            "is_initiator": record.hospital_id == self.auth.user.hospital_id,
            "target_hospital_id": record.target_hospital_id,
            "create_time": record.create_time.isoformat() if record.create_time else None,
        }

    async def ecg_send_consult(self, *, id: int, target_hospital_id: int) -> dict:
        """申请协同：选接收医院，发发会诊（status=consult_sent）。"""
        record = await self.db.get(EcgConsultModel, id)
        if not record:
            raise CustomException(msg="记录不存在")
        if record.hospital_id != self.auth.user.hospital_id:
            raise CustomException(msg="仅发起方医生可申请协同")
        if record.status not in ("uploaded", "consult_sent"):
            raise CustomException(msg=f"当前状态「{record.status}」不可发起会诊")
        if not target_hospital_id or target_hospital_id == record.hospital_id:
            raise CustomException(msg="接收医院不能与发起医院相同")
        record.target_hospital_id = target_hospital_id
        record.status = "consult_sent"
        record.update_time = datetime.now()
        self.db.add(record)
        await self.db.flush()
        return {"id": record.id, "status": "consult_sent", "target_hospital_id": target_hospital_id}

    async def ecg_feedback(self, *, id: int, feedback: str) -> dict:
        """接收方医院医生写反馈（status=closed）。"""
        record = await self.db.get(EcgConsultModel, id)
        if not record:
            raise CustomException(msg="记录不存在")
        if record.target_hospital_id != self.auth.user.hospital_id:
            raise CustomException(msg="仅接收方医院医生可写反馈")
        if record.status not in ("consult_sent", "received"):
            raise CustomException(msg=f"当前状态「{record.status}」不可写反馈")
        record.feedback = feedback
        record.feedback_doctor_id = self.auth.user.id
        record.feedback_time = datetime.now()
        record.status = "closed"
        record.update_time = datetime.now()
        self.db.add(record)
        await self.db.flush()
        return {"id": record.id, "status": "closed"}

    # ── AI 模拟再认证自评 ─────────────────────────────────

    async def selfcheck(self, *, start: str | None, end: str | None) -> dict:
        """按质控指标统计区间内病例达标率，输出模拟评分与逐条指标结论。"""
        conditions = [self._own_condition()]
        if start:
            conditions.append(CaseRecordModel.create_time >= start)
        if end:
            conditions.append(CaseRecordModel.create_time <= f"{end} 23:59:59")

        cases = (
            await self.db.execute(select(CaseRecordModel).where(*conditions))
        ).scalars().all()

        # 统计各指标达标情况（复用时间轴计算）
        metrics_total: dict[str, int] = {}
        metrics_pass: dict[str, int] = {}
        for m in QUALITY_METRICS:
            metrics_total[m["key"]] = 0
            metrics_pass[m["key"]] = 0

        for c in cases:
            form_data = await self._case_form_data(c.id)

            def get_dt(code: str):
                return self._parse_time(form_data.get(code))

            for m in QUALITY_METRICS:
                start_dt = get_dt(m["start"])
                end_dt = get_dt(m["end"])
                diff = self._diff_minutes(start_dt, end_dt)
                if diff is None:
                    continue
                metrics_total[m["key"]] += 1
                if m["limit"] is None or diff <= m["limit"]:
                    metrics_pass[m["key"]] += 1

        items = []
        total_count = 0
        pass_count = 0
        for m in QUALITY_METRICS:
            t = metrics_total[m["key"]]
            p = metrics_pass[m["key"]]
            total_count += t
            pass_count += p
            rate = round(p / t * 100, 1) if t else None
            items.append(
                {
                    "key": m["key"],
                    "name": m["name"],
                    "desc": m["desc"],
                    "limit": m["limit"],
                    "total": t,
                    "pass": p,
                    "rate": rate,
                    "ok": rate is not None and rate >= 80,
                }
            )

        score = round(pass_count / total_count * 100, 1) if total_count else 0
        suggestions = []
        if score >= 90:
            suggestions.append("各项时间指标表现优秀，继续保持")
        elif score >= 80:
            suggestions.append("整体达标，建议针对不达标指标专项改进")
        else:
            suggestions.append("多项时间指标未达标，建议：①加强院前急救与院内衔接培训；②优化导管室激活流程；③建立时间节点填报质控机制")
        for it in items:
            if it["rate"] is not None and not it["ok"]:
                suggestions.append(f"「{it['name']}」达标率 {it['rate']}%，需重点改进")

        return {
            "case_count": len(cases),
            "score": score,
            "items": items,
            "suggestions": suggestions,
        }

    # ── 三会模板（PPT 生成） ──────────────────────────────

    MEETING_TYPES = {
        "quality": {"name": "质量分析会", "desc": "月度质量指标分析与问题病例"},
        "joint": {"name": "联合例会", "desc": "多科室协同与流程改进例会"},
        "case": {"name": "典型病例讨论会", "desc": "典型病例回顾与经验总结"},
    }

    async def _meeting_stat(self, start: str | None, end: str | None) -> dict:
        """统计区间内数据（本院指标 + 时间指标 + 问题病历 + 改进意见）。"""
        conditions = [self._own_condition()]
        if start:
            conditions.append(CaseRecordModel.create_time >= start)
        if end:
            conditions.append(CaseRecordModel.create_time <= f"{end} 23:59:59")

        cases = (await self.db.execute(select(CaseRecordModel).where(*conditions))).scalars().all()

        total = len(cases)
        status_dist = {"draft": 0, "submitted": 0, "approved": 0, "rejected": 0}
        diagnose_dist: dict[str, int] = {}
        come_dist: dict[str, int] = {}
        transfers: list[dict] = []
        for c in cases:
            status_dist[c.status] = status_dist.get(c.status, 0) + 1
            if c.diagnose_type:
                diagnose_dist[c.diagnose_type] = diagnose_dist.get(c.diagnose_type, 0) + 1
            if c.come_type:
                come_dist[c.come_type] = come_dist.get(c.come_type, 0) + 1
            if c.come_type == "转诊" and len(transfers) < 15:
                transfers.append(
                    {
                        "case_no": c.case_no,
                        "patient_name": c.patient_name,
                        "diagnose_type": c.diagnose_type,
                        "status": c.status,
                        "create_time": c.create_time.strftime("%Y-%m-%d") if c.create_time else None,
                    }
                )

        # 时间指标达标率（复用 selfcheck 逻辑）
        metrics = []
        for m in QUALITY_METRICS:
            t = p = 0
            for c in cases:
                form_data = await self._case_form_data(c.id)
                s = self._parse_time(form_data.get(m["start"]))
                e = self._parse_time(form_data.get(m["end"]))
                diff = self._diff_minutes(s, e)
                if diff is None:
                    continue
                t += 1
                if m["limit"] is None or diff <= m["limit"]:
                    p += 1
            metrics.append({
                "key": m["key"],
                "name": m["name"],
                "limit": m["limit"],
                "total": t,
                "pass": p,
                "rate": round(p / t * 100, 1) if t else None,
            })

        # 问题病历：驳回/不达标
        problems = [
            {
                "case_no": c.case_no,
                "patient_name": c.patient_name,
                "diagnose_type": c.diagnose_type,
                "status": c.status,
            }
            for c in cases
            if c.status in ("rejected", "submitted")
        ][:15]

        # 改进意见
        suggestions = []
        for it in metrics:
            if it["rate"] is not None and it["rate"] < 80:
                suggestions.append(f"「{it['name']}」达标率 {it['rate']}%，需优化流程与时间节点管理")
        if not suggestions:
            suggestions.append("各时间指标整体良好，继续保持并完善数据填报完整率")

        return {
            "total": total,
            "status_dist": status_dist,
            "diagnose_dist": diagnose_dist,
            "come_dist": come_dist,
            "transfers": transfers,
            "metrics": metrics,
            "problems": problems,
            "suggestions": suggestions,
        }

    async def meeting_generate(self, *, meeting_type: str, start: str | None, end: str | None, case_id: int | None = None) -> dict:
        """生成三会 PPT 文件并保存记录。典型病例讨论会(case)需指定 case_id，汇总该病例详细数据。"""
        info = self.MEETING_TYPES.get(meeting_type)
        if not info:
            raise CustomException(msg="不支持的会议类型")

        from app.plugin.module_cpx.models import HospitalModel
        hospital = await self.db.get(HospitalModel, self.auth.user.hospital_id)
        hospital_name = hospital.hospital_name if hospital else "本院"

        # 典型病例讨论会：选择病例 → 汇总该病例详细数据生成 PPT
        if meeting_type == "case":
            if not case_id:
                raise CustomException(msg="典型病例讨论会请先选择病例")
            return await self._generate_case_discussion_ppt(case_id=case_id, hospital_name=hospital_name)

        stat = await self._meeting_stat(start, end)

        # ── 生成正式 PPT（自定义排版：封面 / 目录 / 数据表格 / 封底）──
        from pathlib import Path as _Path

        from pptx import Presentation
        from pptx.dml.color import RGBColor
        from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
        from pptx.util import Inches, Pt

        from app.config.path_conf import STATIC_DIR
        from app.config.setting import settings

        # 医疗主题配色
        C_DARK = RGBColor(0x1E, 0x3A, 0x8A)      # 深蓝
        C_PRIMARY = RGBColor(0x25, 0x63, 0xEB)   # 主蓝
        C_TEAL = RGBColor(0x0E, 0xA5, 0xE9)      # 天蓝
        C_GREEN = RGBColor(0x05, 0x96, 0x69)     # 翠绿
        C_WHITE = RGBColor(0xFF, 0xFF, 0xFF)
        C_DARKTXT = RGBColor(0x1F, 0x29, 0x37)   # 正文深灰
        C_GRAY = RGBColor(0x6B, 0x72, 0x80)
        C_LIGHT = RGBColor(0xF3, 0xF4, 0xF6)     # 浅灰底
        C_RED = RGBColor(0xEF, 0x44, 0x44)

        ppt = Presentation()
        ppt.slide_width = Inches(13.333)
        ppt.slide_height = Inches(7.5)
        BLANK = ppt.slide_layouts[6]

        def add_slide():
            return ppt.slides.add_slide(BLANK)

        def add_rect(slide, x, y, w, h, color, line=False):
            shape = slide.shapes.add_shape(1, Inches(x), Inches(y), Inches(w), Inches(h))
            shape.fill.solid()
            shape.fill.fore_color.rgb = color
            if line:
                shape.line.fill.background()
            else:
                shape.line.fill.background()
            return shape

        def add_text(slide, x, y, w, h, text, size=18, color=C_DARKTXT, bold=False, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, line_spacing=1.0):
            box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
            tf = box.text_frame
            tf.word_wrap = True
            tf.vertical_anchor = anchor
            lines = text.split("\n")
            for i, line in enumerate(lines):
                p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
                p.text = line
                p.alignment = align
                p.line_spacing = line_spacing
                for run in p.runs:
                    run.font.size = Pt(size)
                    run.font.bold = bold
                    run.font.color.rgb = color
                    run.font.name = "微软雅黑"
            return box

        def add_table(slide, x, y, w, headers, rows, col_widths=None):
            n_rows = len(rows) + 1
            table_shape = slide.shapes.add_table(n_rows, len(headers), Inches(x), Inches(y), Inches(w), Inches(0.4 * n_rows))
            table = table_shape.table
            if col_widths:
                total = sum(col_widths)
                for i, cw in enumerate(col_widths):
                    table.columns[i].width = Inches(w * cw / total)
            # 表头
            for j, h in enumerate(headers):
                cell = table.cell(0, j)
                cell.text = h
                cell.fill.solid()
                cell.fill.fore_color.rgb = C_PRIMARY
                cell.vertical_anchor = MSO_ANCHOR.MIDDLE
                for p in cell.text_frame.paragraphs:
                    p.alignment = PP_ALIGN.CENTER
                    for run in p.runs:
                        run.font.size = Pt(14)
                        run.font.bold = True
                        run.font.color.rgb = C_WHITE
                        run.font.name = "微软雅黑"
            # 数据行
            for i, row in enumerate(rows):
                for j, val in enumerate(row):
                    cell = table.cell(i + 1, j)
                    cell.text = str(val)
                    cell.fill.solid()
                    cell.fill.fore_color.rgb = C_LIGHT if i % 2 == 0 else C_WHITE
                    cell.vertical_anchor = MSO_ANCHOR.MIDDLE
                    for p in cell.text_frame.paragraphs:
                        p.alignment = PP_ALIGN.CENTER
                        for run in p.runs:
                            run.font.size = Pt(13)
                            run.font.color.rgb = C_DARKTXT
                            run.font.name = "微软雅黑"
            return table

        def add_content_header(slide, no, title):
            """内容页顶部标题栏。"""
            add_rect(slide, 0, 0, 13.333, 1.0, C_PRIMARY)
            add_rect(slide, 0, 1.0, 13.333, 0.08, C_TEAL)
            add_text(slide, 0.8, 0.18, 11.0, 0.7, f"{no}  {title}", size=26, color=C_WHITE, bold=True, anchor=MSO_ANCHOR.MIDDLE)
            add_text(slide, 0.8, 7.05, 11.7, 0.35, f"智慧胸痛中心 · {hospital_name}", size=11, color=C_GRAY, align=PP_ALIGN.RIGHT)

        range_text = f"{start or '全部'} 至 {end or '至今'}"
        now_text = datetime.now().strftime("%Y年%m月%d日")

        # ── 封面页 ──
        slide = add_slide()
        add_rect(slide, 0, 0, 13.333, 7.5, C_DARK)
        add_rect(slide, 0, 0, 13.333, 0.25, C_TEAL)
        add_rect(slide, 0, 7.25, 13.333, 0.25, C_GREEN)
        add_rect(slide, 0.9, 2.05, 1.2, 0.09, C_TEAL)
        add_text(slide, 0.9, 1.15, 11.5, 0.6, "智慧胸痛中心 · 持续质量改进会议", size=18, color=C_TEAL, bold=True)
        add_text(slide, 0.9, 2.35, 11.5, 1.4, f"{hospital_name}\n{info['name']}", size=44, color=C_WHITE, bold=True, line_spacing=1.15)
        add_rect(slide, 0.9, 4.35, 8.0, 0.03, RGBColor(0x3B, 0x5B, 0x9F))
        add_text(slide, 0.9, 4.65, 11.5, 0.5, f"统计区间：{range_text}", size=18, color=RGBColor(0xBF, 0xD3, 0xF2))
        add_text(slide, 0.9, 5.15, 11.5, 0.5, f"生成时间：{now_text}", size=16, color=RGBColor(0xBF, 0xD3, 0xF2))

        is_quality = meeting_type == "quality"

        # ── 目录页 ──
        slide = add_slide()
        add_rect(slide, 0, 0, 13.333, 1.0, C_PRIMARY)
        add_rect(slide, 0, 1.0, 13.333, 0.08, C_TEAL)
        add_text(slide, 0.8, 0.18, 8.0, 0.7, "目录", size=26, color=C_WHITE, bold=True, anchor=MSO_ANCHOR.MIDDLE)
        toc = (
            ["一、本院指标", "二、质控时间指标", "三、问题病历", "四、改进意见"]
            if is_quality
            else ["一、病例概况", "二、来院方式与转诊", "三、质控时间指标", "四、协同改进"]
        )
        for i, item in enumerate(toc):
            y = 1.7 + i * 1.25
            add_rect(slide, 1.2, y, 0.75, 0.75, C_PRIMARY if i % 2 == 0 else C_TEAL)
            add_text(slide, 1.2, y, 0.75, 0.75, str(i + 1), size=28, color=C_WHITE, bold=True, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
            add_text(slide, 2.3, y + 0.12, 9.0, 0.6, item, size=22, color=C_DARKTXT, bold=True, anchor=MSO_ANCHOR.MIDDLE)

        # ── 一、本院指标（quality）/ 病例概况（joint）──
        slide = add_slide()
        add_content_header(slide, "一", "本院指标" if is_quality else "病例概况")
        add_text(slide, 0.8, 1.4, 11.7, 0.6, f"统计病例总数：{stat['total']} 例", size=20, color=C_PRIMARY, bold=True)
        add_table(
            slide, 0.8, 2.3, 5.6,
            ["病例状态", "数量"],
            [
                ["填报中", stat["status_dist"].get("draft", 0)],
                ["待审核", stat["status_dist"].get("submitted", 0)],
                ["已通过", stat["status_dist"].get("approved", 0)],
                ["驳回", stat["status_dist"].get("rejected", 0)],
            ],
            [0.6, 0.4],
        )
        add_text(slide, 6.9, 2.15, 5.5, 0.5, "诊断分布", size=16, color=C_DARKTXT, bold=True)
        diag_rows = [[k, v] for k, v in stat["diagnose_dist"].items()] or [["暂无", "0"]]
        add_table(slide, 6.9, 2.75, 5.6, ["诊断类型", "数量"], diag_rows, [0.6, 0.4])
        # joint 补充：来院方式分布（体现院前/转诊协同）
        if not is_quality:
            add_text(slide, 6.9, 4.6, 5.5, 0.5, "来院方式分布", size=16, color=C_DARKTXT, bold=True)
            come_rows = [[{"120": "120 急救", "自行": "自行来院", "转诊": "网络转诊"}.get(k, k), v] for k, v in stat["come_dist"].items()] or [["暂无", "0"]]
            add_table(slide, 6.9, 5.2, 5.6, ["来院方式", "数量"], come_rows, [0.6, 0.4])

        # ── 二、质控时间指标（quality）/ 来院方式与转诊（joint）──
        if is_quality:
            slide = add_slide()
            add_content_header(slide, "二", "质控时间指标")
            metric_rows = [
                [m["name"], f"{m['pass']}/{m['total']}", f"{m['rate']}%" if m["rate"] is not None else "无数据"]
                for m in stat["metrics"]
            ]
            if not metric_rows:
                metric_rows = [["暂无时间数据", "-", "-"]]
            add_table(slide, 0.8, 1.6, 11.7, ["指标", "达标例数/总数", "达标率"], metric_rows, [0.55, 0.25, 0.2])
            add_text(slide, 0.8, 6.0, 11.7, 0.6, "标准：FMC2ECG ≤10min ｜ D2W ≤90min ｜ FMC2W ≤120min ｜ D2N ≤20min", size=13, color=C_GRAY)
        else:
            slide = add_slide()
            add_content_header(slide, "二", "来院方式与转诊")
            add_text(slide, 0.8, 1.4, 11.7, 0.6, "来院方式构成（院前-院内协同入口）", size=18, color=C_PRIMARY, bold=True)
            come_rows = [[{"120": "120 急救", "自行": "自行来院", "转诊": "网络转诊"}.get(k, k), v] for k, v in stat["come_dist"].items()] or [["暂无", "0"]]
            add_table(slide, 0.8, 2.1, 5.6, ["来院方式", "数量"], come_rows, [0.6, 0.4])
            add_text(slide, 0.8, 4.4, 11.7, 0.5, "转诊互通病例", size=16, color=C_DARKTXT, bold=True)
            trans_rows = [
                [t["case_no"] or "-", t["patient_name"] or "-", t.get("diagnose_type") or "-", t.get("create_time") or "-"]
                for t in stat["transfers"]
            ]
            if not trans_rows:
                add_text(slide, 0.8, 5.1, 11.7, 0.8, "✅ 区间内无转诊病例，区域协同以院内流程为主", size=18, color=C_GREEN)
            else:
                add_table(slide, 0.8, 5.0, 11.7, ["病例编号", "患者姓名", "诊断类型", "转诊日期"], trans_rows, [0.35, 0.2, 0.25, 0.2])

        # ── 三、问题病历（quality）/ 质控时间指标（joint）──
        if is_quality:
            slide = add_slide()
            add_content_header(slide, "三", "问题病历")
            prob_rows = [
                [p["case_no"] or "-", p["patient_name"] or "-", p.get("diagnose_type") or "-", "驳回" if p["status"] == "rejected" else "待审核"]
                for p in stat["problems"]
            ]
            if not prob_rows:
                add_text(slide, 0.8, 2.6, 11.7, 1.0, "✅ 区间内无问题病历，质量管控良好", size=24, color=C_GREEN, bold=True)
            else:
                add_table(slide, 0.8, 1.6, 11.7, ["病例编号", "患者姓名", "诊断类型", "状态"], prob_rows, [0.35, 0.2, 0.25, 0.2])
        else:
            slide = add_slide()
            add_content_header(slide, "三", "质控时间指标")
            metric_rows = [
                [m["name"], f"{m['pass']}/{m['total']}", f"{m['rate']}%" if m["rate"] is not None else "无数据"]
                for m in stat["metrics"]
            ]
            if not metric_rows:
                metric_rows = [["暂无时间数据", "-", "-"]]
            add_table(slide, 0.8, 1.6, 11.7, ["指标", "达标例数/总数", "达标率"], metric_rows, [0.55, 0.25, 0.2])
            add_text(slide, 0.8, 6.0, 11.7, 0.6, "标准：FMC2ECG ≤10min ｜ D2W ≤90min ｜ FMC2W ≤120min ｜ D2N ≤20min", size=13, color=C_GRAY)

        # ── 四、改进意见（quality）/ 协同改进（joint）──
        if is_quality:
            slide = add_slide()
            add_content_header(slide, "四", "改进意见")
            y = 1.7
            for i, s in enumerate(stat["suggestions"]):
                add_rect(slide, 0.9, y + 0.08, 0.35, 0.35, C_GREEN if "良好" in s else C_RED)
                add_text(slide, 1.5, y - 0.05, 10.8, 0.9, f"{i + 1}. {s}", size=17, color=C_DARKTXT, anchor=MSO_ANCHOR.TOP)
                y += 0.95
        else:
            slide = add_slide()
            add_content_header(slide, "四", "协同改进")
            joint_suggestions = []
            if stat["transfers"]:
                joint_suggestions.append(f"区间内转诊互通病例 {len(stat['transfers'])} 例，需强化院前预警-院内响应衔接与转诊交接记录")
            for it in stat["metrics"]:
                if it["rate"] is not None and it["rate"] < 80:
                    joint_suggestions.append(f"「{it['name']}」达标率 {it['rate']}%，多科室联动流程需优化（急诊-导管室-病房交接）")
            if stat["problems"]:
                joint_suggestions.append(f"区间内 {len(stat['problems'])} 份问题病历（驳回/待审核），需规范填报与审核闭环")
            if not joint_suggestions:
                joint_suggestions.append("多科室协同与流程整体良好，继续完善交接班与数据填报完整率")
            y = 1.7
            for i, s in enumerate(joint_suggestions):
                add_rect(slide, 0.9, y + 0.08, 0.35, 0.35, C_GREEN if "良好" in s else C_RED)
                add_text(slide, 1.5, y - 0.05, 10.8, 0.9, f"{i + 1}. {s}", size=17, color=C_DARKTXT, anchor=MSO_ANCHOR.TOP)
                y += 0.95
            add_text(slide, 0.9, y + 0.3, 11.5, 0.6, "协同机制：胸痛中心-急诊科-导管室-心内科-院前急救 多科室联合响应", size=14, color=C_GRAY)

        # ── 封底 ──
        slide = add_slide()
        add_rect(slide, 0, 0, 13.333, 7.5, C_DARK)
        add_rect(slide, 0, 0, 13.333, 0.25, C_TEAL)
        add_text(slide, 0.9, 3.0, 11.5, 1.0, "持续改进 · 服务患者", size=32, color=C_WHITE, bold=True, align=PP_ALIGN.CENTER)
        add_text(slide, 0.9, 4.2, 11.5, 0.5, f"智慧胸痛中心 · {hospital_name} · {now_text}", size=16, color=RGBColor(0xBF, 0xD3, 0xF2), align=PP_ALIGN.CENTER)

        # 保存文件
        meeting_dir = STATIC_DIR / "meeting"
        meeting_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{meeting_type}_{self.auth.user.hospital_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pptx"
        file_path = meeting_dir / filename
        ppt.save(str(file_path))
        file_size = file_path.stat().st_size

        record = MeetingRecordModel(
            meeting_type=meeting_type,
            title=f"{hospital_name} {info['name']}",
            hospital_id=self.auth.user.hospital_id,
            doctor_id=self.auth.user.id,
            start_date=start,
            end_date=end,
            file_path=f"{settings.ROOT_PATH}{settings.STATIC_URL}/meeting/{filename}",
            file_size=file_size,
        )
        self.db.add(record)
        await self.db.flush()

        return {
            "id": record.id,
            "title": record.title,
            "file_url": record.file_path,
            "file_size": file_size,
            "stat": stat,
        }

    async def meeting_list(self) -> list[dict]:
        """本医院生成记录。"""
        rows = (
            await self.db.execute(
                select(MeetingRecordModel)
                .where(MeetingRecordModel.hospital_id == self.auth.user.hospital_id)
                .order_by(MeetingRecordModel.create_time.desc())
                .limit(50)
            )
        ).scalars().all()
        return [
            {
                "id": r.id,
                "meeting_type": r.meeting_type,
                "title": r.title,
                "start_date": r.start_date.strftime("%Y-%m-%d") if r.start_date else None,
                "end_date": r.end_date.strftime("%Y-%m-%d") if r.end_date else None,
                "file_url": r.file_path,
                "file_size": r.file_size,
                "create_time": r.create_time.isoformat() if r.create_time else None,
            }
            for r in rows
        ]

    async def meeting_preview(self, *, id: int) -> dict:
        """预览会议内容（结构化数据）。"""
        record = await self.db.get(MeetingRecordModel, id)
        if not record:
            raise CustomException(msg="记录不存在")
        stat = await self._meeting_stat(
            record.start_date.strftime("%Y-%m-%d") if record.start_date else None,
            record.end_date.strftime("%Y-%m-%d") if record.end_date else None,
        )
        return {
            "id": record.id,
            "title": record.title,
            "meeting_type": record.meeting_type,
            "start_date": record.start_date.strftime("%Y-%m-%d") if record.start_date else None,
            "end_date": record.end_date.strftime("%Y-%m-%d") if record.end_date else None,
            "file_url": record.file_path,
            "create_time": record.create_time.isoformat() if record.create_time else None,
            "stat": stat,
        }

    async def meeting_delete(self, *, id: int) -> None:
        """删除生成记录（含物理文件）。"""
        from pathlib import Path as _Path

        from app.config.path_conf import STATIC_DIR
        from app.config.setting import settings

        record = await self.db.get(MeetingRecordModel, id)
        if not record:
            raise CustomException(msg="记录不存在")
        if record.hospital_id != self.auth.user.hospital_id:
            raise CustomException(msg="无权删除该记录", code=10403, status_code=403)

        # 物理删除 PPT 文件
        if record.file_path:
            import os

            rel = str(record.file_path).replace(f"{settings.ROOT_PATH}{settings.STATIC_URL}/", "").replace("\\", "/")
            target = _Path(str(STATIC_DIR)) / rel
            try:
                if target.exists():
                    os.remove(str(target))
            except OSError as exc:  # 文件被占用/沙箱策略等场景：记录但不阻断删除记录
                import logging
                logging.getLogger(__name__).warning("meeting file delete failed: %s (%s)", target, exc)

        await self.db.delete(record)
        await self.db.flush()

    async def _generate_case_discussion_ppt(self, *, case_id: int, hospital_name: str) -> dict:
        """典型病例讨论会 PPT：选择病例 → 汇总该病例详细数据（基本信息/时间轴/质控/填报/改进）。"""
        case = await self.db.get(CaseRecordModel, case_id)
        if not case or case.doctor_id != self.auth.user.id:
            raise CustomException(msg="病例不存在或无权访问")
        form_data = await self._case_form_data(case_id)

        from pptx import Presentation
        from pptx.dml.color import RGBColor
        from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
        from pptx.util import Inches, Pt

        from app.config.path_conf import STATIC_DIR
        from app.config.setting import settings

        C_DARK = RGBColor(0x1E, 0x3A, 0x8A)
        C_PRIMARY = RGBColor(0x25, 0x63, 0xEB)
        C_TEAL = RGBColor(0x0E, 0xA5, 0xE9)
        C_GREEN = RGBColor(0x05, 0x96, 0x69)
        C_RED = RGBColor(0xDC, 0x26, 0x26)
        C_WHITE = RGBColor(0xFF, 0xFF, 0xFF)
        C_DARKTXT = RGBColor(0x1F, 0x29, 0x37)
        C_GRAY = RGBColor(0x6B, 0x72, 0x80)
        C_LIGHT = RGBColor(0xF3, 0xF4, 0xF6)

        ppt = Presentation()
        ppt.slide_width = Inches(13.333)
        ppt.slide_height = Inches(7.5)
        blank = ppt.slide_layouts[6]

        def add_slide():
            return ppt.slides.add_slide(blank)

        def add_rect(slide, x, y, w, h, color):
            from pptx.enum.shapes import MSO_SHAPE
            shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
            shape.fill.solid()
            shape.fill.fore_color.rgb = color
            shape.line.fill.background()
            shape.shadow.inherit = False
            return shape

        def add_text(slide, x, y, w, h, text, size=16, color=C_DARKTXT, bold=False, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, line_spacing=1.0):
            box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
            tf = box.text_frame
            tf.word_wrap = True
            tf.vertical_anchor = anchor
            lines = str(text).split("\n")
            for i, line in enumerate(lines):
                p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
                p.alignment = align
                p.line_spacing = line_spacing
                run = p.add_run()
                run.text = line
                run.font.size = Pt(size)
                run.font.bold = bold
                run.font.color.rgb = color
                run.font.name = "微软雅黑"
            return box

        def add_table(slide, x, y, w, headers, rows, col_widths, cell_colors=None, font_colors=None, header_fill=C_PRIMARY):
            n_rows = len(rows)
            cell_colors = cell_colors or {}
            font_colors = font_colors or {}
            table_shape = slide.shapes.add_table(n_rows + 1, len(headers), Inches(x), Inches(y), Inches(w), Inches(0.42 * (n_rows + 1)))
            table = table_shape.table
            table.first_row = False
            table.horz_banding = False
            for j, h in enumerate(headers):
                cell = table.cell(0, j)
                cell.text = str(h)
                cell.fill.solid()
                cell.fill.fore_color.rgb = header_fill
                cell.vertical_anchor = MSO_ANCHOR.MIDDLE
                cell.margin_top = Inches(0.02)
                cell.margin_bottom = Inches(0.02)
                for p in cell.text_frame.paragraphs:
                    p.alignment = PP_ALIGN.CENTER
                    for run in p.runs:
                        run.font.size = Pt(13)
                        run.font.bold = True
                        run.font.color.rgb = C_WHITE
                        run.font.name = "微软雅黑"
            for i, row in enumerate(rows):
                for j, val in enumerate(row):
                    cell = table.cell(i + 1, j)
                    cell.text = str(val)
                    cell.fill.solid()
                    cell.fill.fore_color.rgb = cell_colors.get((i, j), C_LIGHT if i % 2 == 0 else C_WHITE)
                    cell.vertical_anchor = MSO_ANCHOR.MIDDLE
                    cell.margin_top = Inches(0.02)
                    cell.margin_bottom = Inches(0.02)
                    cell.margin_left = Inches(0.06)
                    cell.margin_right = Inches(0.06)
                    cell.text_frame.word_wrap = True
                    for p in cell.text_frame.paragraphs:
                        p.alignment = PP_ALIGN.CENTER if j > 0 else PP_ALIGN.LEFT
                        for run in p.runs:
                            run.font.size = Pt(12)
                            run.font.color.rgb = font_colors.get((i, j), C_DARKTXT)
                            run.font.name = "微软雅黑"
            for j, cw in enumerate(col_widths):
                table.columns[j].width = Inches(cw)
            return table

        def add_rounded_rect(slide, x, y, w, h, color, line_color=None):
            from pptx.enum.shapes import MSO_SHAPE
            shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
            shape.fill.solid()
            shape.fill.fore_color.rgb = color
            if line_color:
                shape.line.color.rgb = line_color
                shape.line.width = Pt(1)
            else:
                shape.line.fill.background()
            shape.shadow.inherit = False
            return shape

        def add_badge(slide, x, y, w, h, text, fill, font_color=C_WHITE, size=12, bold=True):
            shape = add_rounded_rect(slide, x, y, w, h, fill)
            tf = shape.text_frame
            tf.word_wrap = True
            tf.margin_left = Inches(0.06)
            tf.margin_right = Inches(0.06)
            tf.margin_top = Inches(0.01)
            tf.margin_bottom = Inches(0.01)
            p = tf.paragraphs[0]
            p.alignment = PP_ALIGN.CENTER
            run = p.add_run()
            run.text = text
            run.font.size = Pt(size)
            run.font.bold = bold
            run.font.color.rgb = font_color
            run.font.name = "微软雅黑"
            return shape

        def add_timeline(slide, nodes):
            """竖向时间轴：圆点 + 连线 + 名称/时间 + 相邻节点间隔标注。nodes: [{name,time,has,interval}]"""
            from pptx.enum.shapes import MSO_SHAPE

            line_x = 1.35
            start_y = 1.55
            dy = 0.52
            n = len(nodes)
            add_rect(slide, line_x - 0.015, start_y, 0.03, dy * (n - 1) + 0.26, C_LIGHT)
            for i, nd in enumerate(nodes):
                y = start_y + i * dy
                dot = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(line_x - 0.13), Inches(y - 0.13), Inches(0.26), Inches(0.26))
                dot.fill.solid()
                dot.fill.fore_color.rgb = C_GREEN if nd["has"] else C_GRAY
                dot.line.fill.background()
                dot.shadow.inherit = False
                add_text(slide, line_x + 0.3, y - 0.2, 4.6, 0.4, nd["name"], size=14, color=C_DARKTXT, bold=True, anchor=MSO_ANCHOR.MIDDLE)
                add_text(slide, 6.2, y - 0.2, 4.2, 0.4, nd["time"], size=13, color=C_GRAY, anchor=MSO_ANCHOR.MIDDLE)
                if nd.get("interval") is not None and i > 0:
                    mins = nd["interval"]
                    col = C_GREEN if mins <= 30 else (C_PRIMARY if mins <= 90 else C_RED)
                    add_badge(slide, 0.2, y - 0.16, 0.95, 0.32, f"Δ{mins}′", col, size=11)

        def add_content_header(slide, no, title):
            add_rect(slide, 0, 0, 13.333, 1.0, C_PRIMARY)
            add_rect(slide, 0, 1.0, 13.333, 0.08, C_TEAL)
            add_text(slide, 0.8, 0.18, 11.0, 0.7, f"{no}  {title}", size=26, color=C_WHITE, bold=True, anchor=MSO_ANCHOR.MIDDLE)
            add_text(slide, 0.8, 7.05, 11.7, 0.35, f"智慧胸痛中心 · {hospital_name}", size=11, color=C_GRAY, align=PP_ALIGN.RIGHT)

        now_text = datetime.now().strftime("%Y年%m月%d日")
        patient = case.patient_name or "未知患者"
        case_title = f"{hospital_name} 典型病例讨论会"
        record_title = f"{hospital_name} {patient} 典型病例讨论会"

        # ── 先算救治时间轴与质控指标（多页复用）──
        tl_nodes = []
        _prev = None
        for code, name in TIMELINE_NODES:
            raw = form_data.get(code)
            dt = self._parse_time(raw)
            tstr = dt.strftime("%Y-%m-%d %H:%M") if dt else (str(raw) if raw not in (None, "") else "—")
            interval = None
            if dt and _prev:
                interval = int((dt - _prev).total_seconds() // 60)
            tl_nodes.append({"name": name, "time": tstr, "has": dt is not None, "interval": interval})
            if dt:
                _prev = dt

        suggestions: list[str] = []
        metrics_calc: list[dict] = []
        for m in QUALITY_METRICS:
            s = self._parse_time(form_data.get(m["start"]))
            e = self._parse_time(form_data.get(m["end"]))
            diff = self._diff_minutes(s, e)
            if diff is None:
                status = "na"
            else:
                status = "pass" if (m["limit"] is None or diff <= m["limit"]) else "fail"
                if m["limit"] is not None and diff > m["limit"]:
                    suggestions.append(f"「{m['name']}」耗时 {diff} 分钟，超出标准 {m['limit']} 分钟，需优化相关环节")
            metrics_calc.append({"name": m["name"], "diff": diff, "limit": m["limit"], "status": status})
        pass_cnt = sum(1 for x in metrics_calc if x["status"] == "pass")
        judge_cnt = sum(1 for x in metrics_calc if x["status"] in ("pass", "fail"))
        summary_line = (f"核心指标达标 {pass_cnt}/{judge_cnt}" if judge_cnt else "时间数据不足，无法评估核心指标") \
            + ("，建议作为典型病例分享" if not suggestions else "，存在待优化环节")

        # ── 封面 ──
        slide = add_slide()
        add_rect(slide, 0, 0, 13.333, 7.5, C_DARK)
        add_rect(slide, 0, 0, 13.333, 0.25, C_TEAL)
        add_rect(slide, 0, 7.25, 13.333, 0.25, C_GREEN)
        add_text(slide, 0.9, 1.0, 11.5, 0.5, "智慧胸痛中心 · 典型病例讨论会", size=18, color=C_TEAL, bold=True)
        add_rect(slide, 0.9, 1.7, 1.2, 0.09, C_TEAL)
        add_text(slide, 0.9, 2.0, 11.5, 1.4, f"{patient}", size=54, color=C_WHITE, bold=True)
        add_text(slide, 0.9, 3.5, 11.5, 0.6, f"病例编号：{case.case_no or '-'}   ｜   诊断：{case.diagnose_type or '-'}   ｜   来院方式：{case.come_type or '-'}", size=17, color=RGBColor(0xBF, 0xD3, 0xF2))
        add_rect(slide, 0.9, 4.3, 11.5, 0.02, RGBColor(0x3B, 0x5B, 0x9F))
        add_rounded_rect(slide, 0.9, 4.6, 11.5, 0.95, RGBColor(0x16, 0x2B, 0x5E))
        add_text(slide, 1.2, 4.72, 11.0, 0.7, summary_line, size=18, color=C_WHITE, bold=True, anchor=MSO_ANCHOR.MIDDLE)
        add_text(slide, 0.9, 5.9, 11.5, 0.5, f"{hospital_name}   ｜   {now_text}", size=16, color=RGBColor(0xBF, 0xD3, 0xF2))

        # ── 目录 ──
        slide = add_slide()
        add_rect(slide, 0, 0, 13.333, 1.0, C_PRIMARY)
        add_rect(slide, 0, 1.0, 13.333, 0.08, C_TEAL)
        add_text(slide, 0.8, 0.18, 11.0, 0.7, "目录", size=26, color=C_WHITE, bold=True, anchor=MSO_ANCHOR.MIDDLE)
        toc = [
            ("一", "病例基本信息", "患者画像与关键摘要"),
            ("二", "救治时间轴", "全流程关键时间节点与间隔"),
            ("三", "质控时间指标", "核心再灌注时间达标分析"),
            ("四", "详细填报数据", "各阶段表单填报明细"),
            ("五", "问题与改进", "缺失项与流程优化建议"),
        ]
        ty = 1.5
        for idx, (no, t, sub) in enumerate(toc):
            add_rounded_rect(slide, 0.9, ty, 0.85, 0.85, C_PRIMARY if idx % 2 == 0 else C_TEAL)
            add_text(slide, 0.9, ty, 0.85, 0.85, no, size=30, color=C_WHITE, bold=True, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
            add_text(slide, 2.0, ty + 0.05, 10.0, 0.5, t, size=22, color=C_DARKTXT, bold=True, anchor=MSO_ANCHOR.MIDDLE)
            add_text(slide, 2.0, ty + 0.5, 10.0, 0.35, sub, size=14, color=C_GRAY)
            ty += 1.05

        # ── 一、病例基本信息 ──
        slide = add_slide()
        add_content_header(slide, "一", "病例基本信息")
        basic_rows = [
            ["患者姓名", case.patient_name or "-"],
            ["性别", case.gender or "-"],
            ["年龄", f"{case.age} 岁" if case.age is not None else "-"],
            ["联系电话", case.phone or "-"],
            ["来院方式", case.come_type or "-"],
            ["诊断类型", case.diagnose_type or "-"],
            ["病例编号", case.case_no or "-"],
            ["病例状态", {"draft": "草稿", "submitted": "待审核", "approved": "已通过", "rejected": "驳回"}.get(case.status, case.status or "-")],
            ["提交医生", case.doctor.real_name if case.doctor else "-"],
        ]
        add_table(slide, 0.8, 1.5, 7.0, ["项目", "内容"], basic_rows, [0.3, 0.4])

        # 右侧：关键摘要面板
        add_rounded_rect(slide, 8.2, 1.5, 4.4, 5.1, C_LIGHT)
        add_text(slide, 8.45, 1.62, 4.0, 0.5, "关键摘要", size=18, color=C_PRIMARY, bold=True)
        ky = 2.25
        for mc in metrics_calc:
            if mc["status"] == "na":
                continue
            label = mc["name"].split("(")[0]
            val = f"{mc['diff']} 分钟" if mc["diff"] is not None else "无数据"
            std = f"/ 标准 {mc['limit']}min" if mc["limit"] else ""
            col = C_GREEN if mc["status"] == "pass" else C_RED
            add_text(slide, 8.45, ky, 3.9, 0.3, label, size=13, color=C_DARKTXT, bold=True)
            add_text(slide, 8.45, ky + 0.28, 3.0, 0.3, val + std, size=12, color=C_GRAY)
            add_badge(slide, 11.55, ky + 0.02, 0.85, 0.42, "达标" if mc["status"] == "pass" else "超时", col, size=12)
            ky += 0.72
        cy = ky + 0.05
        add_rect(slide, 8.45, cy, 3.9, 0.02, RGBColor(0xD1, 0xD5, 0xDB))
        add_text(slide, 8.45, cy + 0.12, 3.9, 0.9, f"出院转归：{form_data.get('outcome') or '-'}\n出院诊断：{form_data.get('discharge_diag') or '-'}", size=12, color=C_DARKTXT, line_spacing=1.2)

        # ── 二、救治时间轴 ──
        slide = add_slide()
        add_content_header(slide, "二", "救治时间轴")
        add_timeline(slide, tl_nodes)
        add_text(slide, 0.2, 6.55, 11.5, 0.4, "注：绿色圆点=已填报时间节点，灰色=缺失；Δ 为相邻节点间隔（分钟，绿≤30 / 蓝≤90 / 红>90）", size=11, color=C_GRAY)

        # ── 三、质控时间指标 ──
        slide = add_slide()
        add_content_header(slide, "三", "质控时间指标")
        metric_rows = []
        cell_colors: dict[tuple[int, int], object] = {}
        font_colors: dict[tuple[int, int], object] = {}
        for i, mc in enumerate(metrics_calc):
            if mc["status"] == "na":
                metric_rows.append([mc["name"], "无数据", "-", "无数据"])
                cell_colors[(i, 3)] = C_GRAY
                font_colors[(i, 3)] = C_WHITE
            else:
                status_txt = "达标" if mc["status"] == "pass" else "超时"
                metric_rows.append([mc["name"], f"{mc['diff']} 分钟", f"{mc['limit']}min" if mc["limit"] else "记录", status_txt])
                col = C_GREEN if mc["status"] == "pass" else C_RED
                cell_colors[(i, 3)] = col
                font_colors[(i, 3)] = C_WHITE
        add_table(slide, 0.8, 1.5, 11.7, ["指标", "耗时", "标准", "判定"], metric_rows, [0.42, 0.18, 0.18, 0.15], cell_colors=cell_colors, font_colors=font_colors)
        add_text(slide, 0.8, 6.0, 11.7, 0.4, f"核心指标达标率：{pass_cnt}/{judge_cnt}　｜　标准：FMC2ECG ≤10min ｜ D2W ≤90min ｜ FMC2W ≤120min ｜ D2N ≤20min", size=13, color=C_GRAY)

        # ── 四、详细填报数据（按 Tab 分组） ──
        field_by_tab: dict[str, list[tuple[str, str]]] = {}
        for f in FIELDS:
            v = form_data.get(f["code"])
            if v in (None, ""):
                continue
            field_by_tab.setdefault(f["tab"], []).append((f["name"], str(v)))
        if not field_by_tab:
            slide = add_slide()
            add_content_header(slide, "四", "详细填报数据")
            add_text(slide, 0.8, 3.0, 11.7, 1.0, "该病例暂无填报数据", size=24, color=C_GRAY)
        else:
            for tab in TABS:
                tab_key = tab["key"]
                tab_name = tab["name"]
                items = field_by_tab.get(tab_key)
                if not items:
                    continue
                slide = add_slide()
                add_content_header(slide, "四", f"详细填报数据 · {tab_name}")
                add_text(slide, 0.8, 1.25, 11.7, 0.4, f"本阶段共 {len(items)} 项填报内容", size=13, color=C_GRAY)
                rows = [[name, val] for name, val in items]
                add_table(slide, 0.8, 1.75, 11.7, ["项目", "内容"], rows, [0.28, 0.6])

        # ── 五、问题与改进 ──
        slide = add_slide()
        add_content_header(slide, "五", "问题与改进")
        missing = [f["name"] for f in FIELDS if f.get("required") == 1 and form_data.get(f["code"]) in (None, "")]
        y = 1.45
        add_text(slide, 0.9, y, 11.5, 0.4, f"一、缺失必填字段（{len(missing)} 项）", size=16, color=C_DARKTXT, bold=True)
        y += 0.55
        if missing:
            cx = 0.9
            cy = y
            for name in missing:
                w = max(1.4, 0.35 + 0.17 * len(name))
                if cx + w > 12.4:
                    cx = 0.9
                    cy += 0.62
                add_badge(slide, cx, cy, w, 0.5, name, C_RED, size=13)
                cx += w + 0.2
            y = cy + 0.85
        else:
            add_badge(slide, 0.9, y, 3.2, 0.5, "✓ 无缺失必填项", C_GREEN, size=14)
            y += 0.85
        y += 0.1
        add_text(slide, 0.9, y, 11.5, 0.4, "二、流程优化建议", size=16, color=C_DARKTXT, bold=True)
        y += 0.55
        if suggestions:
            for i, s in enumerate(suggestions[:6]):
                add_rounded_rect(slide, 0.9, y, 11.5, 0.72, C_LIGHT)
                add_rect(slide, 0.9, y, 0.08, 0.72, C_TEAL)
                add_text(slide, 1.2, y, 11.0, 0.72, f"{i + 1}. {s}", size=14, color=C_DARKTXT, anchor=MSO_ANCHOR.MIDDLE)
                y += 0.86
        else:
            add_text(slide, 1.1, y, 11.0, 0.5, "✅ 各项时间指标均达标，建议作为典型病例在讨论会中分享经验", size=15, color=C_GREEN, bold=True)
            y += 0.7
        add_text(slide, 0.9, 6.25, 11.5, 0.5, "讨论要点：再灌注策略选择 · 时间节点管理 · 双抗/抗凝/他汀规范化 · 出院随访依从性", size=13, color=C_GRAY)

        # ── 封底 ──
        slide = add_slide()
        add_rect(slide, 0, 0, 13.333, 7.5, C_DARK)
        add_rect(slide, 0, 0, 13.333, 0.25, C_TEAL)
        add_text(slide, 0.9, 3.0, 11.5, 1.0, "持续改进 · 服务患者", size=32, color=C_WHITE, bold=True, align=PP_ALIGN.CENTER)
        add_text(slide, 0.9, 4.2, 11.5, 0.5, f"智慧胸痛中心 · {hospital_name} · {now_text}", size=16, color=RGBColor(0xBF, 0xD3, 0xF2), align=PP_ALIGN.CENTER)

        # 保存
        meeting_dir = STATIC_DIR / "meeting"
        meeting_dir.mkdir(parents=True, exist_ok=True)
        filename = f"case_{case_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pptx"
        file_path = meeting_dir / filename
        ppt.save(str(file_path))
        file_size = file_path.stat().st_size

        record = MeetingRecordModel(
            meeting_type="case",
            title=record_title,
            hospital_id=self.auth.user.hospital_id,
            doctor_id=self.auth.user.id,
            start_date=None,
            end_date=None,
            case_id=case_id,
            file_path=f"{settings.ROOT_PATH}{settings.STATIC_URL}/meeting/{filename}",
            file_size=file_size,
        )
        self.db.add(record)
        await self.db.flush()

        return {
            "id": record.id,
            "title": record.title,
            "file_url": record.file_path,
            "file_size": file_size,
            "case_id": case_id,
            "patient_name": patient,
            "stat": {
                "case_id": case_id,
                "patient_name": patient,
                "case_no": case.case_no,
                "diagnose_type": case.diagnose_type,
                "total": 1,
                "status_dist": {case.status: 1},
                "diagnose_dist": {case.diagnose_type: 1} if case.diagnose_type else {},
                "metrics": [],
                "problems": [],
                "suggestions": suggestions,
            },
        }

    # ── 图片上传（病历/心电图等） ──────────────────────────

    async def upload_image(self, file) -> str:
        """保存图片到 static/uploads/doctor/，返回可访问 URL。"""
        import uuid
        from pathlib import Path as _Path

        from app.config.path_conf import STATIC_DIR
        from app.config.setting import settings

        allowed = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}
        suffix = _Path(file.filename or "").suffix.lower()
        if suffix not in allowed:
            raise CustomException(msg="仅支持图片文件（png/jpg/jpeg/gif/webp/bmp）")

        # 大小限制 50MB
        content = await file.read()
        if len(content) > 50 * 1024 * 1024:
            raise CustomException(msg="图片大小不能超过 50MB")

        sub = datetime.now().strftime("%Y%m%d")
        upload_dir = STATIC_DIR / "uploads" / "doctor" / sub
        upload_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{uuid.uuid4().hex}{suffix}"
        target = upload_dir / filename
        target.write_bytes(content)

        return sign_static_url(f"{settings.ROOT_PATH}{settings.STATIC_URL}/uploads/doctor/{sub}/{filename}")
