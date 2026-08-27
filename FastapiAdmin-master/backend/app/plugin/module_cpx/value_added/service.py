# -*- coding: utf-8 -*-
"""增值服务管理服务：分页查询、详情、增改、上线/下线"""

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import CustomException

from app.plugin.module_cpx.auth.dependencies import BizAuth
from app.plugin.module_cpx.models import ValueAddedServiceModel
from app.plugin.module_cpx.value_added.schema import ValueAddedCreateSchema, ValueAddedUpdateSchema


def _serialize(v: ValueAddedServiceModel, *, full: bool = False) -> dict[str, Any]:
    base = {
        "id": v.id,
        "name": v.name,
        "subtitle": v.subtitle,
        "icon": v.icon,
        "cover": v.cover,
        "link_type": v.link_type,
        "link_url": v.link_url,
        "sort_order": v.sort_order or 0,
        "status": v.status,
        "creator_id": v.creator_id,
        "create_time": v.create_time.isoformat() if v.create_time else None,
        "update_time": v.update_time.isoformat() if v.update_time else None,
    }
    if full:
        base["remark"] = v.remark
    return base


class ValueAddedService:
    """增值服务管理服务"""

    def __init__(self, auth: BizAuth, db: AsyncSession) -> None:
        self.auth = auth
        self.db = db

    async def page(self, *, page_no: int, page_size: int, keyword: str | None, status: str | None) -> dict:
        conditions = []
        if keyword:
            conditions.append(ValueAddedServiceModel.name.like(f"%{keyword}%"))
        if status:
            conditions.append(ValueAddedServiceModel.status == status)

        total = (
            await self.db.execute(
                select(func.count()).select_from(ValueAddedServiceModel).where(*conditions)
            )
        ).scalar() or 0

        sql = (
            select(ValueAddedServiceModel)
            .where(*conditions)
            .order_by(ValueAddedServiceModel.sort_order.desc(), ValueAddedServiceModel.id.desc())
            .offset((page_no - 1) * page_size)
            .limit(page_size)
        )
        rows = (await self.db.execute(sql)).scalars().all()

        return {
            "page_no": page_no,
            "page_size": page_size,
            "total": total,
            "has_next": page_no * page_size < total,
            "items": [_serialize(v) for v in rows],
        }

    async def detail(self, *, id: int) -> dict:
        v = await self.db.get(ValueAddedServiceModel, id)
        if not v:
            raise CustomException(msg="增值服务不存在")
        return _serialize(v, full=True)

    async def create(self, data: ValueAddedCreateSchema) -> dict:
        v = ValueAddedServiceModel(
            name=data.name,
            subtitle=data.subtitle,
            icon=data.icon,
            cover=data.cover,
            link_type=data.link_type,
            link_url=data.link_url,
            sort_order=data.sort_order,
            status="draft",
            creator_id=self.auth.user.id,
            remark=data.remark,
        )
        self.db.add(v)
        await self.db.flush()
        return {"id": v.id, "name": v.name}

    async def update(self, *, id: int, data: ValueAddedUpdateSchema) -> dict:
        v = await self.db.get(ValueAddedServiceModel, id)
        if not v:
            raise CustomException(msg="增值服务不存在")
        payload = data.model_dump(exclude_unset=True, exclude_none=True)
        for k, val in payload.items():
            setattr(v, k, val)
        self.db.add(v)
        await self.db.flush()
        return {"id": v.id, "name": v.name}

    async def online(self, *, id: int) -> dict:
        v = await self.db.get(ValueAddedServiceModel, id)
        if not v:
            raise CustomException(msg="增值服务不存在")
        if v.status == "online":
            raise CustomException(msg="该服务已上线，请勿重复上线")
        v.status = "online"
        self.db.add(v)
        await self.db.flush()
        return {"id": v.id, "name": v.name}

    async def offline(self, *, id: int) -> dict:
        v = await self.db.get(ValueAddedServiceModel, id)
        if not v:
            raise CustomException(msg="增值服务不存在")
        if v.status != "online":
            raise CustomException(msg="仅已上线的服务可下线")
        v.status = "offline"
        self.db.add(v)
        await self.db.flush()
        return {"id": v.id, "name": v.name}

    async def delete(self, *, id: int) -> dict:
        v = await self.db.get(ValueAddedServiceModel, id)
        if not v:
            raise CustomException(msg="增值服务不存在")
        name = v.name
        await self.db.delete(v)
        await self.db.flush()
        return {"id": id, "name": name}

    # ── App 端公开接口 ────────────────────────────────────────

    async def active_list(self, *, limit: int = 20) -> list[dict]:
        """App 端拉取已上线服务列表（按 sort_order 倒序 + id 倒序）。"""
        rows = (
            await self.db.execute(
                select(ValueAddedServiceModel)
                .where(ValueAddedServiceModel.status == "online")
                .order_by(ValueAddedServiceModel.sort_order.desc(), ValueAddedServiceModel.id.desc())
                .limit(limit)
            )
        ).scalars().all()
        return [_serialize(v) for v in rows]