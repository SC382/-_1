# -*- coding: utf-8 -*-
"""胸痛中心一期种子数据初始化（幂等，可重复执行）。

用法：
    cd backend
    .venv/Scripts/python.exe -m app.scripts.init_cpx_data

初始化内容：
- role：管理员 / 审核员 / 医生
- user_account：admin 管理员账号（密码 Admin123）
- 演示医院（可选，默认创建一家「演示医院」）
"""

import asyncio
import os

# 必须在导入 app 模块前设置，决定加载 .env.dev
os.environ.setdefault("ENVIRONMENT", "dev")

from sqlalchemy import select

from app.core.database import async_db_session
from app.plugin.module_cpx.models import CpxRoleModel, HospitalModel, UserAccountModel
from app.utils.password_util import PwdUtil


async def main() -> None:
    async with async_db_session() as session, session.begin():
        # ── 角色 ──────────────────────────────────────────
        role_names = ["管理员", "审核员", "医生"]
        role_map: dict[str, CpxRoleModel] = {}
        for name in role_names:
            existing = (
                await session.execute(select(CpxRoleModel).where(CpxRoleModel.role_name == name))
            ).scalars().first()
            if existing:
                role_map[name] = existing
                print(f"[skip] 角色已存在: {name}")
            else:
                role = CpxRoleModel(role_name=name, description=f"{name}角色")
                session.add(role)
                await session.flush()
                role_map[name] = role
                print(f"[ok] 新增角色: {name}")

        # ── 演示医院（可选） ──────────────────────────────
        demo_hospital = None
        hospital_existing = (
            await session.execute(select(HospitalModel).where(HospitalModel.hospital_name == "演示医院"))
        ).scalars().first()
        if not hospital_existing:
            demo_hospital = HospitalModel(
                hospital_name="演示医院",
                hospital_level="三级甲等",
                province="北京市",
                city="北京市",
                address="演示地址",
                contact_name="演示联系人",
                contact_phone="010-00000000",
                status=1,
            )
            session.add(demo_hospital)
            await session.flush()
            print("[ok] 新增演示医院")
        else:
            demo_hospital = hospital_existing
            print("[skip] 演示医院已存在")

        # ── 管理员账号 ────────────────────────────────────
        admin = (
            await session.execute(select(UserAccountModel).where(UserAccountModel.username == "admin"))
        ).scalars().first()
        if not admin:
            admin = UserAccountModel(
                username="admin",
                password=PwdUtil.hash_password("Admin123"),
                real_name="系统管理员",
                phone="13800000000",
                role_id=role_map["管理员"].id,
                hospital_id=demo_hospital.id if demo_hospital else None,
                status=1,
            )
            session.add(admin)
            await session.flush()
            print("[ok] 新增管理员账号: admin / Admin123")
        else:
            print("[skip] 管理员账号已存在")

    print("\n完成。")


if __name__ == "__main__":
    asyncio.run(main())
