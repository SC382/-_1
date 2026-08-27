# -*- coding: utf-8 -*-
"""业务操作日志服务：供其它业务模块统一调用记录，并支持分页查询。"""

from typing import Any

from fastapi import Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import CustomException

from app.plugin.module_cpx.models import SystemLogModel, UserAccountModel


def get_client_ip(request: Request | None) -> str | None:
    """从请求中解析客户端 IP（兼容反向代理）。"""
    if request is None:
        return None
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else None


class LogService:
    """系统日志服务"""

    @staticmethod
    async def create(
        db: AsyncSession,
        *,
        user_id: int | None,
        module: str,
        operation: str,
        description: str,
        ip_address: str | None = None,
        result: str = "success",
    ) -> None:
        """写入一条业务操作日志（result: success成功 / fail失败）。"""
        log = SystemLogModel(
            user_id=user_id,
            module=module,
            operation=operation,
            description=description,
            ip_address=ip_address,
            result=result,
        )
        db.add(log)
        await db.flush()

    @staticmethod
    async def page(
        db: AsyncSession,
        *,
        page_no: int = 1,
        page_size: int = 10,
        user_id: int | None = None,
        user_name: str | None = None,
        role_id: int | None = None,
        hospital_id: int | None = None,
        module: str | None = None,
        operation: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
    ) -> dict[str, Any]:
        """分页查询日志（操作用户姓名/角色/医院/模块/操作类型/时间组合筛选）。"""
        from app.plugin.module_cpx.models import CpxRoleModel

        conditions = []
        if user_id:
            conditions.append(SystemLogModel.user_id == user_id)
        if user_name:
            conditions.append(UserAccountModel.real_name.like(f"%{user_name.strip()}%"))
        if role_id is not None:
            conditions.append(UserAccountModel.role_id == role_id)
        if hospital_id is not None:
            conditions.append(UserAccountModel.hospital_id == hospital_id)
        if module:
            conditions.append(SystemLogModel.module.like(f"%{module}%"))
        if operation:
            conditions.append(SystemLogModel.operation.like(f"%{operation}%"))
        if start_time:
            conditions.append(SystemLogModel.create_time >= start_time)
        if end_time:
            conditions.append(SystemLogModel.create_time <= f"{end_time} 23:59:59")

        base_query = (
            select(SystemLogModel)
            .outerjoin(UserAccountModel, UserAccountModel.id == SystemLogModel.user_id)
            .where(*conditions)
        )
        total = await db.execute(select(func.count()).select_from(base_query.subquery()))
        total_count = total.scalar() or 0

        sql = (
            base_query.order_by(SystemLogModel.create_time.desc(), SystemLogModel.id.desc())
            .offset((page_no - 1) * page_size)
            .limit(page_size)
        )
        result = await db.execute(sql)
        rows = result.scalars().all()

        items = []
        for row in rows:
            user = row.user
            role_name = None
            hospital_name = None
            if user is not None:
                role_name = user.role.role_name if user.role else None
                hospital_name = user.hospital.hospital_name if user.hospital else None
            items.append(
                {
                    "id": row.id,
                    "user_id": row.user_id,
                    "username": user.username if user else None,
                    "real_name": user.real_name if user else None,
                    "role_name": role_name,
                    "hospital_name": hospital_name,
                    "module": row.module,
                    "operation": row.operation,
                    "description": row.description,
                    "ip_address": row.ip_address,
                    "result": row.result,
                    "create_time": row.create_time.isoformat() if row.create_time else None,
                }
            )

        return {
            "page_no": page_no,
            "page_size": page_size,
            "total": total_count,
            "has_next": page_no * page_size < total_count,
            "items": items,
        }
