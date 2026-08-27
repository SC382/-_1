# -*- coding: utf-8 -*-
"""动态模板管理服务：模板 + 字段"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import CustomException

from app.plugin.module_cpx.auth.dependencies import BizAuth
from app.plugin.module_cpx.models import CaseDetailModel, ReportTemplateModel, TemplateFieldModel
from app.plugin.module_cpx.template.schema import (
    TemplateCreateSchema,
    TemplateFieldCreateSchema,
    TemplateFieldUpdateSchema,
    TemplateUpdateSchema,
)


class TemplateService:
    """模板管理服务"""

    def __init__(self, auth: BizAuth, db: AsyncSession) -> None:
        self.auth = auth
        self.db = db

    # ── 模板 ────────────────────────────────────────────────

    async def page(self, *, page_no: int, page_size: int, keyword: str | None, status: int | None = None) -> dict:
        conditions = []
        if keyword:
            conditions.append(ReportTemplateModel.template_name.like(f"%{keyword}%"))
        if status is not None:
            conditions.append(ReportTemplateModel.status == status)

        total = await self.db.execute(
            select(func.count()).select_from(ReportTemplateModel).where(*conditions)
        )
        total_count = total.scalar() or 0

        sql = (
            select(ReportTemplateModel)
            .where(*conditions)
            .order_by(ReportTemplateModel.id.desc())
            .offset((page_no - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(sql)
        rows = result.scalars().all()

        items = [
            {
                "id": t.id,
                "template_name": t.template_name,
                "version": t.version,
                "status": t.status,
                "published": t.published,
                "creator_id": t.creator_id,
                "field_count": len(t.fields or []),
                "create_time": t.create_time.isoformat() if t.create_time else None,
            }
            for t in rows
        ]
        return {
            "page_no": page_no,
            "page_size": page_size,
            "total": total_count,
            "has_next": page_no * page_size < total_count,
            "items": items,
        }

    async def detail(self, *, id: int) -> dict:
        template = await self.db.get(ReportTemplateModel, id)
        if not template:
            raise CustomException(msg="模板不存在")
        fields = sorted(template.fields or [], key=lambda f: (f.tab_order or 0, f.sort_num or 0, f.id))
        return {
            "id": template.id,
            "template_name": template.template_name,
            "version": template.version,
            "status": template.status,
            "published": template.published,
            "creator_id": template.creator_id,
            "create_time": template.create_time.isoformat() if template.create_time else None,
            "fields": [
                {
                    "id": f.id,
                    "field_name": f.field_name,
                    "field_code": f.field_code,
                    "field_type": f.field_type,
                    "field_options": f.field_options,
                    "required_flag": f.required_flag,
                    "sort_num": f.sort_num,
                    "tab_name": f.tab_name,
                    "tab_order": f.tab_order,
                }
                for f in fields
            ],
        }

    async def create(self, data: TemplateCreateSchema) -> dict:
        template = ReportTemplateModel(
            template_name=data.template_name,
            version=data.version,
            status=data.status,
            published=0,  # 新建模板默认为未发布
            creator_id=self.auth.user.id,
        )
        self.db.add(template)
        await self.db.flush()
        return {"id": template.id, "template_name": template.template_name}

    async def update(self, *, id: int, data: TemplateUpdateSchema) -> dict:
        template = await self.db.get(ReportTemplateModel, id)
        if not template:
            raise CustomException(msg="模板不存在")
        payload = data.model_dump(exclude_unset=True, exclude_none=True)
        for key, value in payload.items():
            setattr(template, key, value)
        self.db.add(template)
        await self.db.flush()
        return {"id": template.id, "template_name": template.template_name}

    async def publish(self, *, id: int) -> dict:
        """发布模板：后台标记为正式可用（published=1），无 APP 推送行为。"""
        template = await self.db.get(ReportTemplateModel, id)
        if not template:
            raise CustomException(msg="模板不存在")
        if template.published == 1:
            raise CustomException(msg="该模板已发布，请勿重复发布")
        template.published = 1
        template.status = 1  # 发布后自动启用
        self.db.add(template)
        await self.db.flush()
        return {"id": template.id, "template_name": template.template_name}

    async def unpublish(self, *, id: int) -> dict:
        """取消发布（回退为草稿）：仅当模板未被任何病例使用时允许，防止老病例数据错乱。"""
        template = await self.db.get(ReportTemplateModel, id)
        if not template:
            raise CustomException(msg="模板不存在")
        if template.published != 1:
            raise CustomException(msg="该模板未发布，无需取消发布")
        used = (
            await self.db.execute(
                select(func.count()).select_from(CaseDetailModel).where(CaseDetailModel.template_id == id)
            )
        ).scalar() or 0
        if used > 0:
            raise CustomException(msg=f"该模板已被 {used} 份病例使用，禁止取消发布（防止数据错乱）；请新建模板版本")
        template.published = 0
        self.db.add(template)
        await self.db.flush()
        return {"id": template.id, "template_name": template.template_name, "unpublished": True}

    async def _ensure_editable(self, template_id: int) -> None:
        """已发布模板禁止修改字段（如需改动请新建版本）。"""
        template = await self.db.get(ReportTemplateModel, template_id)
        if not template:
            raise CustomException(msg="模板不存在")
        if template.published == 1:
            raise CustomException(msg="该模板已发布，禁止修改字段；如需改动请新建模板版本")

    async def all_active(self) -> list[dict]:
        """全部启用模板（供病例表单渲染 / 下拉选择）。"""
        result = await self.db.execute(
            select(ReportTemplateModel)
            .where(ReportTemplateModel.status == 1)
            .order_by(ReportTemplateModel.id.desc())
        )
        return [
            {"id": t.id, "template_name": t.template_name, "version": t.version} for t in result.scalars().all()
        ]

    # ── 字段 ────────────────────────────────────────────────

    async def add_field(self, data: TemplateFieldCreateSchema) -> dict:
        await self._ensure_editable(data.template_id)
        field = TemplateFieldModel(
            template_id=data.template_id,
            tab_name=data.tab_name,
            tab_order=data.tab_order or 0,
            field_name=data.field_name,
            field_code=data.field_code,
            field_type=data.field_type,
            field_options=data.field_options,
            required_flag=data.required_flag,
            sort_num=data.sort_num,
        )
        self.db.add(field)
        await self.db.flush()
        return {"id": field.id, "field_name": field.field_name}

    async def update_field(self, *, id: int, data: TemplateFieldUpdateSchema) -> dict:
        field = await self.db.get(TemplateFieldModel, id)
        if not field:
            raise CustomException(msg="字段不存在")
        await self._ensure_editable(field.template_id)
        payload = data.model_dump(exclude_unset=True)
        for key, value in payload.items():
            setattr(field, key, value)
        self.db.add(field)
        await self.db.flush()
        return {"id": field.id, "field_name": field.field_name}

    async def copy_standard(self, *, template_id: int) -> dict:
        """把 fields.py 的标准字段集（7 个分类 + ~60 字段）复制到指定模板。

        - 仅未发布模板可调用（已发布的不能再改）
        - 同 template_id 已有字段全部清空再写入
        - 选项统一为字符串数组（fields.py 中 {label,value} 列表仅保留 value）
        """
        from app.plugin.module_cpx.fields import FIELDS as STD_FIELDS, TABS as STD_TABS

        await self._ensure_editable(template_id)
        template = await self.db.get(ReportTemplateModel, template_id)
        if not template:
            raise CustomException(msg="模板不存在")

        # 已有字段清空
        existing = (
            await self.db.execute(
                select(TemplateFieldModel).where(TemplateFieldModel.template_id == template_id)
            )
        ).scalars().all()
        for f in existing:
            await self.db.delete(f)
        await self.db.flush()

        # 分类 key -> (name, order)
        tab_index = {t["key"]: (t["name"], idx) for idx, t in enumerate(STD_TABS)}

        for idx, f in enumerate(STD_FIELDS):
            tab_name, tab_order = tab_index.get(f.get("tab", ""), ("未分类", 999))
            # options 归一化为字符串数组（取 value 或字符串）
            raw_opts = f.get("options")
            opts = None
            if isinstance(raw_opts, list) and raw_opts:
                opts = [
                    (o.get("value") if isinstance(o, dict) else str(o))
                    for o in raw_opts
                ]
            self.db.add(
                TemplateFieldModel(
                    template_id=template_id,
                    tab_name=tab_name,
                    tab_order=tab_order,
                    field_name=f["name"],
                    field_code=f["code"],
                    field_type=f.get("type", "text"),
                    field_options=opts,
                    required_flag=f.get("required", 0) or 0,
                    sort_num=idx + 1,
                )
            )
        await self.db.flush()
        return {"id": template_id, "copied": len(STD_FIELDS), "tabs": len(STD_TABS)}

    async def delete_field(self, *, id: int) -> None:
        field = await self.db.get(TemplateFieldModel, id)
        if not field:
            raise CustomException(msg="字段不存在")
        await self._ensure_editable(field.template_id)
        await self.db.delete(field)
        await self.db.flush()

    async def delete(self, *, id: int) -> dict:
        """删除模板：未被任何病例使用时可删（级联删除模板字段）；被使用则禁止。"""
        template = await self.db.get(ReportTemplateModel, id)
        if not template:
            raise CustomException(msg="模板不存在")
        used = (
            await self.db.execute(
                select(func.count()).select_from(CaseDetailModel).where(CaseDetailModel.template_id == id)
            )
        ).scalar() or 0
        if used > 0:
            raise CustomException(msg=f"该模板已被 {used} 份病例使用，禁止删除；请新建模板版本")
        fields = (
            await self.db.execute(
                select(TemplateFieldModel).where(TemplateFieldModel.template_id == id)
            )
        ).scalars().all()
        for f in fields:
            await self.db.delete(f)
        await self.db.delete(template)
        await self.db.flush()
        return {"id": id, "template_name": template.template_name, "deleted_fields": len(fields)}

    async def rename_tab(self, *, template_id: int, old_name: str, new_name: str, tab_order: int | None = None) -> dict:
        """批量重命名模板内某分类（同步更新该分类下所有字段的 tab_name / tab_order）。"""
        await self._ensure_editable(template_id)
        if not new_name or not new_name.strip():
            raise CustomException(msg="新分类名不能为空")
        rows = (
            await self.db.execute(
                select(TemplateFieldModel).where(
                    TemplateFieldModel.template_id == template_id,
                    TemplateFieldModel.tab_name == old_name,
                )
            )
        ).scalars().all()
        for f in rows:
            f.tab_name = new_name.strip()
            if tab_order is not None:
                f.tab_order = tab_order
            self.db.add(f)
        await self.db.flush()
        return {"template_id": template_id, "old_name": old_name, "new_name": new_name, "count": len(rows)}

    async def delete_tab(self, *, template_id: int, tab_name: str) -> dict:
        """删除模板内某分类及其下所有字段。"""
        await self._ensure_editable(template_id)
        rows = (
            await self.db.execute(
                select(TemplateFieldModel).where(
                    TemplateFieldModel.template_id == template_id,
                    TemplateFieldModel.tab_name == tab_name,
                )
            )
        ).scalars().all()
        for f in rows:
            await self.db.delete(f)
        await self.db.flush()
        return {"template_id": template_id, "tab_name": tab_name, "deleted": len(rows)}
