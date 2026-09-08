# -*- coding: utf-8 -*-
"""随访表扩展：follow_up 增加 form_data 列（35 字段分组表单 JSON）。

- 先建完整备份表 follow_up_backup_20260902_full（可一键回滚）
- ALTER TABLE 加列 form_data TEXT NULL（幂等：已存在则跳过）
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pymysql

DB = {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "root",
    "password": "123456",
    "database": "fastapiadmin",
    "charset": "utf8mb4",
}


def main() -> None:
    conn = pymysql.connect(**DB)
    cur = conn.cursor()
    try:
        # 1) 完整备份（当前所有 240 条 + 结构）
        cur.execute("DROP TABLE IF EXISTS follow_up_backup_20260902_full")
        cur.execute("CREATE TABLE follow_up_backup_20260902_full AS SELECT * FROM follow_up")
        n = cur.fetchone() if cur.rowcount is None else None
        cur.execute("SELECT COUNT(*) FROM follow_up_backup_20260902_full")
        print(f"备份表 follow_up_backup_20260902_full 已创建，共 {cur.fetchone()[0]} 条")

        # 2) 加列（幂等）
        cur.execute(
            "SELECT COUNT(*) FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA=%s AND TABLE_NAME='follow_up' AND COLUMN_NAME='form_data'",
            (DB["database"],),
        )
        if cur.fetchone()[0]:
            print("form_data 列已存在，跳过 ALTER")
        else:
            cur.execute("ALTER TABLE follow_up ADD COLUMN form_data TEXT NULL COMMENT '随访表单扩展数据 JSON'")
            print("已执行: ALTER TABLE follow_up ADD COLUMN form_data TEXT NULL")

        conn.commit()
        print("迁移完成 ✅")
    except Exception as e:  # noqa: BLE001
        conn.rollback()
        print(f"迁移失败，已回滚: {e}")
        sys.exit(1)
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
