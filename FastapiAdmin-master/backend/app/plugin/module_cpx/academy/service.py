# -*- coding: utf-8 -*-
"""胸痛学院服务：管理端 CRUD / 发布 / 上传；医生端只读列表 / 详情。"""

import uuid
from datetime import datetime
from pathlib import Path as _Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.path_conf import STATIC_DIR
from app.config.setting import settings
from app.core.signed_url import sign_static_url
from app.core.exceptions import CustomException

from app.plugin.module_cpx.academy.schema import AcademyCreateSchema, AcademyUpdateSchema
from app.plugin.module_cpx.auth.dependencies import BizAuth
from app.plugin.module_cpx.models import AcademyContentModel

# 文件类型 → 允许的后缀
TYPE_SUFFIX: dict[str, set[str]] = {
    "video": {".mp4", ".mov", ".m4v", ".webm", ".avi"},
    "ppt": {".ppt", ".pptx"},
    "doc": {".doc", ".docx"},
    "pdf": {".pdf"},
    "other": {".xls", ".xlsx", ".txt", ".md", ".zip", ".png", ".jpg", ".jpeg", ".gif", ".webp"},
}
ALL_SUFFIX = {s for ss in TYPE_SUFFIX.values() for s in ss}


def detect_type(suffix: str) -> str:
    """按后缀识别内容类型。"""
    for t, ss in TYPE_SUFFIX.items():
        if suffix in ss:
            return t
    return "other"


def _to_public_url(rel_path: str) -> str:
    """static 相对路径 → 可访问 URL（/api/v1/static/...）。"""
    return sign_static_url(f"{settings.ROOT_PATH}{settings.STATIC_URL}/{rel_path.lstrip('/')}")


def _serialize(item: AcademyContentModel) -> dict:
    return {
        "id": item.id,
        "title": item.title,
        "content_type": item.content_type,
        "category": item.category,
        "summary": item.summary,
        "file_path": _to_public_url(item.file_path),
        "file_name": item.file_name,
        "file_size": item.file_size,
        "cover_path": _to_public_url(item.cover_path) if item.cover_path else None,
        "published": item.published or 0,
        "sort_num": item.sort_num or 0,
        "view_count": item.view_count or 0,
        "download_count": item.download_count or 0,
        "create_time": item.create_time.isoformat() if item.create_time else None,
    }


class AcademyService:
    """胸痛学院服务"""

    def __init__(self, auth: BizAuth, db: AsyncSession) -> None:
        self.auth = auth
        self.db = db

    # ── 管理端 ──────────────────────────────────────────

    async def page(self, *, page_no: int, page_size: int, keyword: str | None, content_type: str | None, category: str | None, published: int | None) -> dict:
        conditions = []
        if keyword:
            conditions.append(AcademyContentModel.title.like(f"%{keyword}%"))
        if content_type:
            conditions.append(AcademyContentModel.content_type == content_type)
        if category:
            conditions.append(AcademyContentModel.category == category)
        if published is not None:
            conditions.append(AcademyContentModel.published == published)

        total = (
            await self.db.execute(select(func.count()).select_from(AcademyContentModel).where(*conditions))
        ).scalar() or 0
        rows = (
            await self.db.execute(
                select(AcademyContentModel)
                .where(*conditions)
                .order_by(AcademyContentModel.sort_num.asc(), AcademyContentModel.id.desc())
                .offset((page_no - 1) * page_size)
                .limit(page_size)
            )
        ).scalars().all()
        return {
            "page_no": page_no,
            "page_size": page_size,
            "total": total,
            "has_next": page_no * page_size < total,
            "items": [_serialize(r) for r in rows],
        }

    async def detail(self, *, id: int) -> dict:
        item = await self.db.get(AcademyContentModel, id)
        if not item:
            raise CustomException(msg="内容不存在")
        return _serialize(item)

    async def create(self, data: AcademyCreateSchema) -> dict:
        item = AcademyContentModel(
            title=data.title,
            content_type=data.content_type,
            category=data.category,
            summary=data.summary,
            file_path=data.file_path,
            file_name=data.file_name,
            file_size=data.file_size,
            cover_path=data.cover_path,
            published=data.published,
            sort_num=data.sort_num,
            creator_id=self.auth.user.id,
        )
        self.db.add(item)
        await self.db.flush()
        return {"id": item.id, "title": item.title}

    async def update(self, *, id: int, data: AcademyUpdateSchema) -> dict:
        item = await self.db.get(AcademyContentModel, id)
        if not item:
            raise CustomException(msg="内容不存在")
        payload = data.model_dump(exclude_unset=True, exclude_none=True)
        for key, value in payload.items():
            setattr(item, key, value)
        item.update_time = datetime.now()
        self.db.add(item)
        await self.db.flush()
        return {"id": item.id, "title": item.title}

    async def delete(self, *, id: int) -> dict:
        item = await self.db.get(AcademyContentModel, id)
        if not item:
            raise CustomException(msg="内容不存在")
        result = {"id": item.id, "title": item.title}
        await self.db.delete(item)
        await self.db.flush()
        # 尝试删除静态文件（失败不影响记录删除）
        try:
            rel = item.file_path.lstrip("/")
            (STATIC_DIR / rel).unlink(missing_ok=True)
        except Exception:
            pass
        return result

    async def toggle_publish(self, *, id: int) -> dict:
        item = await self.db.get(AcademyContentModel, id)
        if not item:
            raise CustomException(msg="内容不存在")
        item.published = 0 if (item.published or 0) == 1 else 1
        self.db.add(item)
        await self.db.flush()
        return {"id": item.id, "title": item.title, "published": item.published}

    async def upload(self, file) -> dict:
        """上传学习资源文件到 static/academy/，返回 URL 与元信息。"""
        suffix = _Path(file.filename or "").suffix.lower()
        if suffix not in ALL_SUFFIX:
            raise CustomException(msg=f"不支持的文件类型 {suffix or '（无后缀）'}；支持：视频/PPT/Word/PDF/Excel/图片/文本")
        content = await file.read()
        # 视频放宽到 300MB，其余 60MB
        limit = 300 * 1024 * 1024 if suffix in TYPE_SUFFIX["video"] else 60 * 1024 * 1024
        if len(content) > limit:
            raise CustomException(msg="文件过大（视频 ≤300MB，其他 ≤60MB）")

        sub = datetime.now().strftime("%Y%m%d")
        upload_dir = STATIC_DIR / "academy" / sub
        upload_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{uuid.uuid4().hex}{suffix}"
        target = upload_dir / filename
        target.write_bytes(content)

        rel = f"academy/{sub}/{filename}"
        return {
            "url": _to_public_url(rel),
            "file_path": rel,
            "file_name": file.filename,
            "file_size": len(content),
            "content_type": detect_type(suffix),
        }

    # ── 医生端（只读） ──────────────────────────────────

    async def doctor_list(self, *, page_no: int, page_size: int, content_type: str | None, category: str | None) -> dict:
        conditions = [AcademyContentModel.published == 1]
        if content_type:
            conditions.append(AcademyContentModel.content_type == content_type)
        if category:
            conditions.append(AcademyContentModel.category == category)
        total = (
            await self.db.execute(select(func.count()).select_from(AcademyContentModel).where(*conditions))
        ).scalar() or 0
        rows = (
            await self.db.execute(
                select(AcademyContentModel)
                .where(*conditions)
                .order_by(AcademyContentModel.sort_num.asc(), AcademyContentModel.id.desc())
                .offset((page_no - 1) * page_size)
                .limit(page_size)
            )
        ).scalars().all()
        return {
            "page_no": page_no,
            "page_size": page_size,
            "total": total,
            "has_next": page_no * page_size < total,
            "items": [_serialize(r) for r in rows],
        }

    async def doctor_detail(self, *, id: int) -> dict:
        item = await self.db.get(AcademyContentModel, id)
        if not item or (item.published or 0) != 1:
            raise CustomException(msg="内容不存在或未发布")
        item.view_count = (item.view_count or 0) + 1
        item.update_time = datetime.now()
        self.db.add(item)
        await self.db.flush()
        return _serialize(item)
