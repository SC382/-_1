# -*- coding: utf-8 -*-
"""医院管理服务"""

from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import CustomException

from app.plugin.module_cpx.auth.dependencies import BizAuth
from app.plugin.module_cpx.hospital.schema import HospitalCreateSchema, HospitalUpdateSchema
from app.plugin.module_cpx.models import (
    AuditorInfoModel,
    CaseRecordModel,
    DoctorInfoModel,
    HospitalModel,
)


def _count_subquery(model: type, hospital_col: str) -> Any:
    """按医院统计数量的标量子查询。"""
    col = getattr(model, hospital_col)
    return (
        select(func.count())
        .select_from(model)
        .where(col == HospitalModel.id)
        .correlate(HospitalModel)
        .scalar_subquery()
    )


class HospitalService:
    """医院管理服务"""

    def __init__(self, auth: BizAuth, db: AsyncSession) -> None:
        self.auth = auth
        self.db = db

    async def page(self, *, page_no: int, page_size: int, search: dict[str, Any] | None = None) -> dict:
        """分页查询医院（附带医生/审核员/病例数量）。"""
        conditions = []
        search = search or {}
        if search.get("hospital_name"):
            conditions.append(HospitalModel.hospital_name.like(f"%{search['hospital_name']}%"))
        if search.get("hospital_level"):
            conditions.append(HospitalModel.hospital_level == search["hospital_level"])
        if search.get("province"):
            conditions.append(HospitalModel.province == search["province"])
        if search.get("status") is not None and search["status"] != "":
            conditions.append(HospitalModel.status == search["status"])

        total = await self.db.execute(
            select(func.count()).select_from(HospitalModel).where(*conditions)
        )
        total_count = total.scalar() or 0

        doctor_sub = _count_subquery(DoctorInfoModel, "hospital_id")
        auditor_sub = _count_subquery(AuditorInfoModel, "hospital_id")
        case_sub = _count_subquery(CaseRecordModel, "hospital_id")

        sql = (
            select(
                HospitalModel,
                doctor_sub.label("doctor_count"),
                auditor_sub.label("auditor_count"),
                case_sub.label("case_count"),
            )
            .where(*conditions)
            .order_by(HospitalModel.id.desc())
            .offset((page_no - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(sql)
        rows = result.all()

        items = [
            {
                "id": h.id,
                "hospital_name": h.hospital_name,
                "hospital_level": h.hospital_level,
                "province": h.province,
                "city": h.city,
                "address": h.address,
                "contact_name": h.contact_name,
                "contact_phone": h.contact_phone,
                "status": h.status,
                "doctor_count": d_count or 0,
                "auditor_count": a_count or 0,
                "case_count": c_count or 0,
                "create_time": h.create_time.isoformat() if h.create_time else None,
            }
            for h, d_count, a_count, c_count in rows
        ]

        return {
            "page_no": page_no,
            "page_size": page_size,
            "total": total_count,
            "has_next": page_no * page_size < total_count,
            "items": items,
        }

    async def detail(self, *, id: int) -> dict:
        """医院详情（含数量）。"""
        doctor_sub = _count_subquery(DoctorInfoModel, "hospital_id")
        auditor_sub = _count_subquery(AuditorInfoModel, "hospital_id")
        case_sub = _count_subquery(CaseRecordModel, "hospital_id")
        result = await self.db.execute(
            select(
                HospitalModel,
                doctor_sub.label("doctor_count"),
                auditor_sub.label("auditor_count"),
                case_sub.label("case_count"),
            ).where(HospitalModel.id == id)
        )
        row = result.first()
        if not row:
            raise CustomException(msg="医院不存在")
        h = row[0]
        return {
            "id": h.id,
            "hospital_name": h.hospital_name,
            "hospital_level": h.hospital_level,
            "province": h.province,
            "city": h.city,
            "address": h.address,
            "contact_name": h.contact_name,
            "contact_phone": h.contact_phone,
            "status": h.status,
            "doctor_count": row[1] or 0,
            "auditor_count": row[2] or 0,
            "case_count": row[3] or 0,
            "create_time": h.create_time.isoformat() if h.create_time else None,
            "update_time": h.update_time.isoformat() if h.update_time else None,
        }

    async def create(self, data: HospitalCreateSchema) -> dict:
        """新增医院。"""
        hospital = HospitalModel(
            hospital_name=data.hospital_name,
            hospital_level=data.hospital_level,
            province=data.province,
            city=data.city,
            address=data.address,
            contact_name=data.contact_name,
            contact_phone=data.contact_phone,
            status=data.status,
        )
        self.db.add(hospital)
        await self.db.flush()
        return {"id": hospital.id, "hospital_name": hospital.hospital_name}

    async def update(self, *, id: int, data: HospitalUpdateSchema) -> dict:
        """修改医院。"""
        hospital = await self.db.get(HospitalModel, id)
        if not hospital:
            raise CustomException(msg="医院不存在")
        payload = data.model_dump(exclude_unset=True, exclude_none=True)
        for key, value in payload.items():
            setattr(hospital, key, value)
        self.db.add(hospital)
        await self.db.flush()
        return {"id": hospital.id, "hospital_name": hospital.hospital_name}

    async def set_status(self, *, ids: list[int], status: int, ip_address: str | None = None) -> None:
        """批量启用/禁用医院。禁用后其医生/审核员无法登录。"""
        if not ids:
            return
        await self.db.execute(
            update(HospitalModel)
            .where(HospitalModel.id.in_(ids))
            .values(status=status)
        )
        await self.db.flush()
