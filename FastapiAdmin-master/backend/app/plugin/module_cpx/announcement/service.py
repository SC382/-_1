# -*- coding: utf-8 -*-
"""公告管理服务：分页查询、详情、增改、发布/下线"""

from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import CustomException

from app.plugin.module_cpx.announcement.schema import AnnouncementCreateSchema, AnnouncementUpdateSchema
from app.plugin.module_cpx.auth.dependencies import BizAuth
from app.plugin.module_cpx.models import AnnouncementModel


def _serialize(a: AnnouncementModel, *, full: bool = False) -> dict[str, Any]:
    """序列化单条公告；full=True 时包含 content/remark 等大字段"""
    base = {
        "id": a.id,
        "title": a.title,
        "subtitle": a.subtitle,
        "cover": a.cover,
        "type": a.type,
        "sort_order": a.sort_order or 0,
        "status": a.status,
        "published_at": a.published_at.isoformat() if a.published_at else None,
        "expires_at": a.expires_at.isoformat() if a.expires_at else None,
        "creator_id": a.creator_id,
        "create_time": a.create_time.isoformat() if a.create_time else None,
        "update_time": a.update_time.isoformat() if a.update_time else None,
    }
    if full:
        base["content"] = a.content
        base["remark"] = a.remark
    return base


class AnnouncementService:
    """公告管理服务"""

    def __init__(self, auth: BizAuth, db: AsyncSession) -> None:
        self.auth = auth
        self.db = db

    async def page(self, *, page_no: int, page_size: int, keyword: str | None, status: str | None, type_: str | None) -> dict:
        conditions = []
        if keyword:
            conditions.append(AnnouncementModel.title.like(f"%{keyword}%"))
        if status:
            conditions.append(AnnouncementModel.status == status)
        if type_:
            conditions.append(AnnouncementModel.type == type_)

        total = (
            await self.db.execute(select(func.count()).select_from(AnnouncementModel).where(*conditions))
        ).scalar() or 0

        sql = (
            select(AnnouncementModel)
            .where(*conditions)
            .order_by(AnnouncementModel.sort_order.desc(), AnnouncementModel.id.desc())
            .offset((page_no - 1) * page_size)
            .limit(page_size)
        )
        rows = (await self.db.execute(sql)).scalars().all()

        return {
            "page_no": page_no,
            "page_size": page_size,
            "total": total,
            "has_next": page_no * page_size < total,
            "items": [_serialize(a) for a in rows],
        }

    async def detail(self, *, id: int) -> dict:
        a = await self.db.get(AnnouncementModel, id)
        if not a:
            raise CustomException(msg="公告不存在")
        return _serialize(a, full=True)

    async def create(self, data: AnnouncementCreateSchema) -> dict:
        a = AnnouncementModel(
            title=data.title,
            subtitle=data.subtitle,
            content=data.content,
            cover=data.cover,
            type=data.type,
            sort_order=data.sort_order,
            status="draft",
            expires_at=data.expires_at,
            creator_id=self.auth.user.id,
            remark=data.remark,
        )
        self.db.add(a)
        await self.db.flush()
        return {"id": a.id, "title": a.title}

    async def update(self, *, id: int, data: AnnouncementUpdateSchema) -> dict:
        a = await self.db.get(AnnouncementModel, id)
        if not a:
            raise CustomException(msg="公告不存在")
        payload = data.model_dump(exclude_unset=True, exclude_none=True)
        for k, v in payload.items():
            setattr(a, k, v)
        self.db.add(a)
        await self.db.flush()
        return {"id": a.id, "title": a.title}

    async def publish(self, *, id: int) -> dict:
        a = await self.db.get(AnnouncementModel, id)
        if not a:
            raise CustomException(msg="公告不存在")
        if a.status == "published":
            raise CustomException(msg="该公告已发布，请勿重复发布")
        a.status = "published"
        a.published_at = datetime.now()
        self.db.add(a)
        await self.db.flush()
        return {"id": a.id, "title": a.title}

    async def offline(self, *, id: int) -> dict:
        a = await self.db.get(AnnouncementModel, id)
        if not a:
            raise CustomException(msg="公告不存在")
        if a.status != "published":
            raise CustomException(msg="仅已发布的公告可下线")
        a.status = "offline"
        self.db.add(a)
        await self.db.flush()
        return {"id": a.id, "title": a.title}

    async def delete(self, *, id: int) -> dict:
        a = await self.db.get(AnnouncementModel, id)
        if not a:
            raise CustomException(msg="公告不存在")
        title = a.title
        await self.db.delete(a)
        await self.db.flush()
        return {"id": id, "title": title}

    # ── App 端公开接口 ────────────────────────────────────────

    async def active_list(self, *, limit: int = 10) -> list[dict]:
        """App 端拉取当前生效中的公告列表（按 sort_order 倒序 + id 倒序）。

        过滤规则：status=published 且未到 expires_at（expires_at 为空或晚于当前时间）。
        """
        now = datetime.now()
        rows = (
            await self.db.execute(
                select(AnnouncementModel)
                .where(
                    AnnouncementModel.status == "published",
                )
                .order_by(AnnouncementModel.sort_order.desc(), AnnouncementModel.id.desc())
                .limit(limit)
            )
        ).scalars().all()
        # 在内存里过滤过期（数据量小，足够）
        return [_serialize(a) for a in rows if not a.expires_at or a.expires_at > now]

    async def active_detail(self, *, id: int) -> dict:
        """App 端拉取公告详情（仅已发布且未过期）。"""
        a = await self.db.get(AnnouncementModel, id)
        if not a or a.status != "published":
            raise CustomException(msg="公告不存在或已下线")
        if a.expires_at and a.expires_at < datetime.now():
            raise CustomException(msg="公告已过期")
        return _serialize(a, full=True)