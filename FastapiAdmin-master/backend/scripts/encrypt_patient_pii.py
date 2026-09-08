# -*- coding: utf-8 -*-
"""存量患者 PII 数据补加密（安全加固）。

幂等、可重复执行：
- case_record 表：phone / id_number / insurance_no 明文行 → 加密
- case_detail 表：form_data JSON 内 PII_FIELDS 命中的明文值 → 加密

用法（在 backend 目录下，使用与后端一致的环境，推荐在后端容器内执行）：
  ENVIRONMENT=prod python scripts/encrypt_patient_pii.py
"""
import json
import os
import sys

import pymysql

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config.setting import settings
from app.core.crypto import encrypt_pii_deep, encrypt_value, is_encrypted

# case_record 中需加密的明文列
PII_COLUMNS = ["phone", "id_number", "insurance_no"]


def get_conn():
    return pymysql.connect(
        host=settings.DATABASE_HOST,
        port=settings.DATABASE_PORT,
        user=settings.DATABASE_USER,
        password=settings.DATABASE_PASSWORD,
        database=settings.DATABASE_NAME,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )


def main() -> None:
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            # 1) case_record 结构化列
            cur.execute("SELECT id, phone, id_number, insurance_no FROM case_record")
            rows = cur.fetchall()
            upd = 0
            for r in rows:
                sets = {}
                for col in PII_COLUMNS:
                    v = r.get(col)
                    if v and isinstance(v, str) and not is_encrypted(v):
                        sets[col] = encrypt_value(v)
                if sets:
                    sql = "UPDATE case_record SET " + ", ".join(f"{c}=%s" for c in sets) + " WHERE id=%s"
                    cur.execute(sql, list(sets.values()) + [r["id"]])
                    upd += 1
            conn.commit()
            print(f"[case_record] 补加密 {upd}/{len(rows)} 行")

            # 2) case_detail.form_data 内 PII 键
            cur.execute("SELECT id, form_data FROM case_detail")
            drows = cur.fetchall()
            dupd = 0
            for r in drows:
                fd = r.get("form_data")
                if not fd:
                    continue
                new = encrypt_pii_deep(fd)
                if json.dumps(new, ensure_ascii=False) != json.dumps(fd, ensure_ascii=False):
                    cur.execute(
                        "UPDATE case_detail SET form_data=%s WHERE id=%s",
                        (json.dumps(new, ensure_ascii=False), r["id"]),
                    )
                    dupd += 1
            conn.commit()
            print(f"[case_detail] 补加密 {dupd}/{len(drows)} 行")
        print("✅ 存量患者 PII 加密完成")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
