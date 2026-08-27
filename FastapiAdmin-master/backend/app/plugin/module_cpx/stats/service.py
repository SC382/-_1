# -*- coding: utf-8 -*-
"""数据统计服务：驾驶舱聚合 + 统计分析。"""

from datetime import datetime, timedelta

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.plugin.module_cpx.auth.dependencies import BizAuth
from app.plugin.module_cpx.audit.service import AuditService
from app.plugin.module_cpx.models import (
    AuditRecordModel,
    CaseDetailModel,
    CaseRecordModel,
    CpxRoleModel,
    DoctorInfoModel,
    HospitalModel,
    TemplateFieldModel,
    UserAccountModel,
)


class StatsService:
    """数据统计服务"""

    def __init__(self, auth: BizAuth, db: AsyncSession) -> None:
        self.auth = auth
        self.db = db

    async def _role_id(self, role_name: str) -> int | None:
        result = await self.db.execute(select(CpxRoleModel).where(CpxRoleModel.role_name == role_name))
        role = result.scalars().first()
        return role.id if role else None

    async def _count(self, model, *conditions) -> int:
        result = await self.db.execute(select(func.count()).select_from(model).where(*conditions))
        return result.scalar() or 0

    # ── 数据驾驶舱 ──────────────────────────────────────────

    async def dashboard(self) -> dict:
        doctor_role = await self._role_id("医生")
        auditor_role = await self._role_id("审核员")

        # 医院统计
        total_hospital = await self._count(HospitalModel)
        active_hospital = await self._count(HospitalModel, HospitalModel.status == 1)
        disabled_hospital = await self._count(HospitalModel, HospitalModel.status == 0)

        # 用户统计
        doctor_count = (
            await self._count(UserAccountModel, UserAccountModel.role_id == doctor_role)
            if doctor_role
            else 0
        )
        auditor_count = (
            await self._count(UserAccountModel, UserAccountModel.role_id == auditor_role)
            if auditor_role
            else 0
        )

        # 病例统计
        today_start = datetime.combine(datetime.now().date(), datetime.min.time())
        total_case = await self._count(CaseRecordModel)
        today_case = await self._count(CaseRecordModel, CaseRecordModel.create_time >= today_start)
        pending_case = await self._count(CaseRecordModel, CaseRecordModel.status == "submitted")
        approved_case = await self._count(CaseRecordModel, CaseRecordModel.status == "approved")
        rejected_case = await self._count(CaseRecordModel, CaseRecordModel.status == "rejected")
        completed_case = approved_case + rejected_case  # 已完成病例 = 通过 + 驳回

        # 审核统计
        audit_total = await self._count(AuditRecordModel)
        audit_pass = await self._count(AuditRecordModel, AuditRecordModel.audit_result == "pass")
        audit_reject = await self._count(AuditRecordModel, AuditRecordModel.audit_result == "reject")
        pass_rate = round(audit_pass / audit_total * 100, 1) if audit_total else 0
        reject_rate = round(audit_reject / audit_total * 100, 1) if audit_total else 0

        # 病例趋势（近 30 天 / 近 12 个月）
        trend = await self._case_trend(days=30)
        trend_monthly = await self._case_trend_monthly(months=12)

        # 医院病例排行（Top 10）
        ranking = await self._hospital_ranking(limit=10)

        return {
            "hospital_stats": {
                "total": total_hospital,
                "active": active_hospital,
                "disabled": disabled_hospital,
            },
            "user_stats": {"doctor": doctor_count, "auditor": auditor_count},
            "case_stats": {
                "total": total_case,
                "today": today_case,
                "pending": pending_case,
                "approved": approved_case,
                "rejected": rejected_case,
                "completed": completed_case,
            },
            "audit_stats": {
                "total": audit_total,
                "pass": audit_pass,
                "reject": audit_reject,
                "pass_rate": pass_rate,
                "reject_rate": reject_rate,
            },
            "case_trend": trend,
            "case_trend_monthly": trend_monthly,
            "hospital_ranking": ranking,
        }

    async def _case_trend(self, days: int = 30) -> dict:
        """近 N 天每日病例数。"""
        start = datetime.combine((datetime.now() - timedelta(days=days - 1)).date(), datetime.min.time())
        rows = await self.db.execute(
            select(func.date(CaseRecordModel.create_time), func.count())
            .where(CaseRecordModel.create_time >= start)
            .group_by(func.date(CaseRecordModel.create_time))
        )
        count_map = {str(r[0]): r[1] for r in rows.all()}

        dates: list[str] = []
        counts: list[int] = []
        for i in range(days):
            d = (datetime.now() - timedelta(days=days - 1 - i)).date()
            key = str(d)
            dates.append(key[5:])  # MM-DD
            counts.append(count_map.get(key, 0))
        return {"xAxis": dates, "data": counts}

    async def _case_trend_monthly(self, months: int = 12) -> dict:
        """近 N 个月每月病例数。"""
        now = datetime.now()
        start = datetime(now.year, now.month, 1) - timedelta(days=1)  # 回溯到 months-1 个月前的 1 号
        for _ in range(months - 1):
            start = datetime(start.year, start.month - 1, 1) if start.month > 1 else datetime(start.year - 1, 12, 1)
        rows = await self.db.execute(
            select(func.date_format(CaseRecordModel.create_time, "%Y-%m"), func.count())
            .where(CaseRecordModel.create_time >= start)
            .group_by(func.date_format(CaseRecordModel.create_time, "%Y-%m"))
        )
        count_map = {str(r[0]): r[1] for r in rows.all()}

        labels: list[str] = []
        counts: list[int] = []
        y, m = now.year, now.month
        for i in range(months - 1, -1, -1):
            month = m - i
            yy, mm = y, month
            while mm <= 0:
                yy -= 1
                mm += 12
            key = f"{yy:04d}-{mm:02d}"
            labels.append(f"{yy}-{mm:02d}")
            counts.append(count_map.get(key, 0))
        return {"xAxis": labels, "data": counts}

    async def _hospital_ranking(self, limit: int = 10) -> list[dict]:
        """各医院病例数量排行。"""
        rows = await self.db.execute(
            select(HospitalModel.hospital_name, func.count(CaseRecordModel.id))
            .join(CaseRecordModel, CaseRecordModel.hospital_id == HospitalModel.id)
            .group_by(HospitalModel.id, HospitalModel.hospital_name)
            .order_by(func.count(CaseRecordModel.id).desc())
            .limit(limit)
        )
        return [{"name": r[0], "value": r[1]} for r in rows.all()]

    # ── 统计分析 ────────────────────────────────────────────

    async def analysis(self) -> dict:
        doctor_role = await self._role_id("医生")
        auditor_role = await self._role_id("审核员")

        # 病例统计
        now = datetime.now()
        month_start = datetime(now.year, now.month, 1)
        year_start = datetime(now.year, 1, 1)
        total_case = await self._count(CaseRecordModel)
        month_case = await self._count(CaseRecordModel, CaseRecordModel.create_time >= month_start)
        year_case = await self._count(CaseRecordModel, CaseRecordModel.create_time >= year_start)

        # 医院数据量（含医生/审核员数）
        hospitals = await self.db.execute(
            select(HospitalModel).order_by(HospitalModel.id.asc())
        )
        hospital_rows = hospitals.scalars().all()
        hospital_stats = []
        for h in hospital_rows:
            case_count = await self._count(CaseRecordModel, CaseRecordModel.hospital_id == h.id)
            doctor_count = (
                await self._count(
                    UserAccountModel,
                    UserAccountModel.hospital_id == h.id,
                    UserAccountModel.role_id == doctor_role,
                )
                if doctor_role
                else 0
            )
            auditor_count = (
                await self._count(
                    UserAccountModel,
                    UserAccountModel.hospital_id == h.id,
                    UserAccountModel.role_id == auditor_role,
                )
                if auditor_role
                else 0
            )
            hospital_stats.append(
                {
                    "id": h.id,
                    "hospital_name": h.hospital_name,
                    "status": h.status,
                    "case_count": case_count,
                    "doctor_count": doctor_count,
                    "auditor_count": auditor_count,
                }
            )

        # 审核统计
        audit_total = await self._count(AuditRecordModel)
        audit_pass = await self._count(AuditRecordModel, AuditRecordModel.audit_result == "pass")
        audit_reject = await self._count(AuditRecordModel, AuditRecordModel.audit_result == "reject")
        pass_rate = round(audit_pass / audit_total * 100, 1) if audit_total else 0
        reject_rate = round(audit_reject / audit_total * 100, 1) if audit_total else 0

        # 质量统计：数据完整率 / 缺失字段数 / 异常数据数
        quality = await self._quality_stats()

        return {
            "case_stats": {
                "total": total_case,
                "month": month_case,
                "year": year_case,
            },
            "hospital_stats": hospital_stats,
            "audit_stats": {
                "total": audit_total,
                "pass": audit_pass,
                "reject": audit_reject,
                "pass_rate": pass_rate,
                "reject_rate": reject_rate,
            },
            "quality": quality,
        }

    async def _quality_stats(self) -> dict:
        """数据质量：检查已提交/已通过病例的必填字段完整性与时间逻辑。"""
        rows = await self.db.execute(
            select(CaseRecordModel)
            .where(CaseRecordModel.status.in_(["submitted", "approved", "rejected"]))
            .order_by(CaseRecordModel.id.asc())
        )
        cases = rows.scalars().all()

        # 预取模板必填字段
        fields_rows = await self.db.execute(
            select(TemplateFieldModel).where(TemplateFieldModel.required_flag == 1)
        )
        required_by_template: dict[int, list] = {}
        for f in fields_rows.scalars().all():
            required_by_template.setdefault(f.template_id, []).append(
                {
                    "field_name": f.field_name,
                    "field_code": f.field_code,
                    "required_flag": f.required_flag,
                }
            )

        total_checks = 0
        missing_count = 0
        abnormal_cases = 0
        complete_cases = 0

        for case in cases:
            detail = (
                await self.db.execute(select(CaseDetailModel).where(CaseDetailModel.case_id == case.id))
            ).scalars().first()
            form_data = detail.form_data or {} if detail else {}
            required = required_by_template.get(detail.template_id if detail else 0, [])

            case_complete = True
            for f in required:
                total_checks += 1
                value = form_data.get(f["field_code"])
                if value is None or (isinstance(value, str) and not value.strip()):
                    missing_count += 1
                    case_complete = False
            if case_complete:
                complete_cases += 1

            # 时间逻辑异常（复用审核校验）
            checks = AuditService(self.auth, self.db)._validate(form_data, required)
            if not checks["time_ok"]:
                abnormal_cases += 1

        completeness_rate = round(complete_cases / len(cases) * 100, 1) if cases else 0

        return {
            "total_cases": len(cases),
            "complete_cases": complete_cases,
            "completeness_rate": completeness_rate,
            "total_required_checks": total_checks,
            "missing_field_count": missing_count,
            "abnormal_cases": abnormal_cases,
        }
