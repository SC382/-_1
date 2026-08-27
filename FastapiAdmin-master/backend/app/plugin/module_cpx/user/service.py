# -*- coding: utf-8 -*-
"""医院用户管理服务：医生（user_account + doctor_info）/ 审核员（user_account + auditor_info）"""

from typing import Any

from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import CustomException
from app.utils.password_util import PwdUtil

from app.plugin.module_cpx.auth.dependencies import (
    ROLE_NAME_AUDITOR,
    ROLE_NAME_DOCTOR,
    BizAuth,
)
from app.plugin.module_cpx.models import (
    AuditorInfoModel,
    CpxRoleModel,
    DoctorInfoModel,
    UserAccountModel,
)
from app.plugin.module_cpx.user.schema import (
    AuditorCreateSchema,
    AuditorUpdateSchema,
    DoctorCreateSchema,
    DoctorUpdateSchema,
)


class UserService:
    """医院用户管理服务"""

    def __init__(self, auth: BizAuth, db: AsyncSession) -> None:
        self.auth = auth
        self.db = db

    # ── 角色ID ──────────────────────────────────────────────

    async def _role_id(self, role_name: str) -> int:
        result = await self.db.execute(select(CpxRoleModel).where(CpxRoleModel.role_name == role_name))
        role = result.scalars().first()
        if not role:
            raise CustomException(msg=f"角色「{role_name}」未初始化，请先执行种子数据")
        return role.id

    async def _doctor_role_id(self) -> int:
        return await self._role_id(ROLE_NAME_DOCTOR)

    async def _auditor_role_id(self) -> int:
        return await self._role_id(ROLE_NAME_AUDITOR)

    # ── 列表 ────────────────────────────────────────────────

    async def list_doctors(
        self,
        *,
        page_no: int,
        page_size: int,
        hospital_id: int | None,
        keyword: str | None,
        phone: str | None = None,
        department: str | None = None,
        title: str | None = None,
        status: int | None = None,
    ) -> dict:
        role_id = await self._doctor_role_id()
        conditions = [UserAccountModel.role_id == role_id]
        if hospital_id:
            conditions.append(UserAccountModel.hospital_id == hospital_id)
        if keyword:
            kw = f"%{keyword}%"
            conditions.append(
                or_(
                    UserAccountModel.real_name.like(kw),
                    UserAccountModel.username.like(kw),
                    DoctorInfoModel.doctor_no.like(kw),
                )
            )
        if phone:
            conditions.append(UserAccountModel.phone.like(f"%{phone}%"))
        if department:
            conditions.append(DoctorInfoModel.department.like(f"%{department}%"))
        if title:
            conditions.append(DoctorInfoModel.title.like(f"%{title}%"))
        if status is not None:
            conditions.append(UserAccountModel.status == status)

        total = await self.db.execute(
            select(func.count())
            .select_from(UserAccountModel)
            .join(DoctorInfoModel, DoctorInfoModel.user_id == UserAccountModel.id)
            .where(*conditions)
        )
        total_count = total.scalar() or 0

        sql = (
            select(UserAccountModel, DoctorInfoModel)
            .join(DoctorInfoModel, DoctorInfoModel.user_id == UserAccountModel.id)
            .where(*conditions)
            .order_by(UserAccountModel.id.desc())
            .offset((page_no - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(sql)
        rows = result.all()

        items = [
            {
                "id": u.id,
                "username": u.username,
                "real_name": u.real_name,
                "phone": u.phone,
                "hospital_id": u.hospital_id,
                "hospital_name": u.hospital.hospital_name if u.hospital else None,
                "doctor_no": d.doctor_no,
                "department": d.department,
                "title": d.title,
                "status": u.status,
                "role_name": ROLE_NAME_DOCTOR,
                "last_login_time": u.last_login_time.isoformat() if u.last_login_time else None,
                "create_time": u.create_time.isoformat() if u.create_time else None,
            }
            for u, d in rows
        ]
        return {
            "page_no": page_no,
            "page_size": page_size,
            "total": total_count,
            "has_next": page_no * page_size < total_count,
            "items": items,
        }

    async def list_auditors(
        self,
        *,
        page_no: int,
        page_size: int,
        hospital_id: int | None,
        keyword: str | None,
        phone: str | None = None,
        status: int | None = None,
    ) -> dict:
        role_id = await self._auditor_role_id()
        conditions = [UserAccountModel.role_id == role_id]
        if hospital_id:
            conditions.append(UserAccountModel.hospital_id == hospital_id)
        if keyword:
            kw = f"%{keyword}%"
            conditions.append(
                or_(
                    UserAccountModel.real_name.like(kw),
                    UserAccountModel.username.like(kw),
                )
            )
        if phone:
            conditions.append(UserAccountModel.phone.like(f"%{phone}%"))
        if status is not None:
            conditions.append(UserAccountModel.status == status)

        total = await self.db.execute(
            select(func.count())
            .select_from(UserAccountModel)
            .join(AuditorInfoModel, AuditorInfoModel.user_id == UserAccountModel.id)
            .where(*conditions)
        )
        total_count = total.scalar() or 0

        sql = (
            select(UserAccountModel, AuditorInfoModel)
            .join(AuditorInfoModel, AuditorInfoModel.user_id == UserAccountModel.id)
            .where(*conditions)
            .order_by(UserAccountModel.id.desc())
            .offset((page_no - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(sql)
        rows = result.all()

        items = [
            {
                "id": u.id,
                "username": u.username,
                "real_name": u.real_name,
                "phone": u.phone,
                "hospital_id": u.hospital_id,
                "hospital_name": u.hospital.hospital_name if u.hospital else None,
                "audit_level": a.audit_level,
                "status": u.status,
                "role_name": ROLE_NAME_AUDITOR,
                "last_login_time": u.last_login_time.isoformat() if u.last_login_time else None,
                "create_time": u.create_time.isoformat() if u.create_time else None,
            }
            for u, a in rows
        ]
        return {
            "page_no": page_no,
            "page_size": page_size,
            "total": total_count,
            "has_next": page_no * page_size < total_count,
            "items": items,
        }

    # ── 新增 ────────────────────────────────────────────────

    async def create_doctor(self, data: DoctorCreateSchema) -> dict:
        role_id = await self._doctor_role_id()
        try:
            user = UserAccountModel(
                username=data.username,
                password=PwdUtil.hash_password(data.password),
                real_name=data.real_name,
                phone=data.phone,
                role_id=role_id,
                hospital_id=data.hospital_id,
                status=data.status,
            )
            self.db.add(user)
            await self.db.flush()

            info = DoctorInfoModel(
                user_id=user.id,
                hospital_id=data.hospital_id,
                doctor_no=data.doctor_no,
                department=data.department,
                title=data.title,
            )
            self.db.add(info)
            await self.db.flush()
        except IntegrityError as e:
            raise CustomException(msg="登录账号已存在，请更换") from e
        return {"id": user.id, "username": user.username, "real_name": user.real_name}

    async def create_auditor(self, data: AuditorCreateSchema) -> dict:
        role_id = await self._auditor_role_id()
        try:
            user = UserAccountModel(
                username=data.username,
                password=PwdUtil.hash_password(data.password),
                real_name=data.real_name,
                phone=data.phone,
                role_id=role_id,
                hospital_id=data.hospital_id,
                status=data.status,
            )
            self.db.add(user)
            await self.db.flush()

            info = AuditorInfoModel(
                user_id=user.id,
                hospital_id=data.hospital_id,
                audit_level=data.audit_level,
            )
            self.db.add(info)
            await self.db.flush()
        except IntegrityError as e:
            raise CustomException(msg="登录账号已存在，请更换") from e
        return {"id": user.id, "username": user.username, "real_name": user.real_name}

    # ── 修改 ────────────────────────────────────────────────

    async def update_doctor(self, *, id: int, data: DoctorUpdateSchema) -> dict:
        user = await self._get_user(id)
        info = await self.db.execute(
            select(DoctorInfoModel).where(DoctorInfoModel.user_id == id)
        )
        info = info.scalars().first()
        payload = data.model_dump(exclude_unset=True, exclude_none=True)
        for key in ("real_name", "phone", "status"):
            if key in payload:
                setattr(user, key, payload[key])
        self.db.add(user)
        if info and any(k in payload for k in ("doctor_no", "department", "title")):
            for key in ("doctor_no", "department", "title"):
                if key in payload:
                    setattr(info, key, payload[key])
            self.db.add(info)
        await self.db.flush()
        return {"id": user.id, "username": user.username}

    async def update_auditor(self, *, id: int, data: AuditorUpdateSchema) -> dict:
        user = await self._get_user(id)
        info = await self.db.execute(
            select(AuditorInfoModel).where(AuditorInfoModel.user_id == id)
        )
        info = info.scalars().first()
        payload = data.model_dump(exclude_unset=True, exclude_none=True)
        for key in ("real_name", "phone", "status"):
            if key in payload:
                setattr(user, key, payload[key])
        self.db.add(user)
        if info and "audit_level" in payload:
            info.audit_level = payload["audit_level"]
            self.db.add(info)
        await self.db.flush()
        return {"id": user.id, "username": user.username}

    async def set_status(self, *, ids: list[int], status: int) -> None:
        if not ids:
            return
        await self.db.execute(
            update(UserAccountModel).where(UserAccountModel.id.in_(ids)).values(status=status)
        )
        await self.db.flush()

    async def reset_password(self, *, id: int, password: str) -> None:
        user = await self._get_user(id)
        user.password = PwdUtil.hash_password(password)
        self.db.add(user)
        await self.db.flush()

    async def detail(self, *, id: int) -> dict:
        user = await self._get_user(id)
        role = await user.awaitable_attrs.role
        base = {
            "id": user.id,
            "username": user.username,
            "real_name": user.real_name,
            "phone": user.phone,
            "hospital_id": user.hospital_id,
            "hospital_name": user.hospital.hospital_name if user.hospital else None,
            "status": user.status,
            "role_name": role.role_name if role else None,
            "create_time": user.create_time.isoformat() if user.create_time else None,
        }
        if role and role.role_name == ROLE_NAME_DOCTOR:
            info = (
                await self.db.execute(select(DoctorInfoModel).where(DoctorInfoModel.user_id == id))
            ).scalars().first()
            base["doctor_no"] = info.doctor_no if info else None
            base["department"] = info.department if info else None
            base["title"] = info.title if info else None
        elif role and role.role_name == ROLE_NAME_AUDITOR:
            info = (
                await self.db.execute(select(AuditorInfoModel).where(AuditorInfoModel.user_id == id))
            ).scalars().first()
            base["audit_level"] = info.audit_level if info else None
        return base

    async def _get_user(self, id: int) -> UserAccountModel:
        user = await self.db.get(UserAccountModel, id)
        if not user:
            raise CustomException(msg="用户不存在")
        return user
