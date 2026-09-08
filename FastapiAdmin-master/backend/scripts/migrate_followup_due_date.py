# -*- coding: utf-8 -*-
"""
一次性迁移：历史随访到期日按「出院日期」重算（2026-09-02，用户确认方案 A）
- 仅迁移 status in ('pending', 'overdue') 的未来任务；submitted（已完成）不动
- 到期日 = 出院日期 + plan_month * 30 天（与 audit/service.py _followup_base_date 逻辑对齐）
- 重算后按 due_date 与今天的关系重新校正 pending/overdue
- 迁移前自动建备份表 follow_up_backup_20260902，可随时回滚

用法: cd backend && ENVIRONMENT=dev ./.venv/Scripts/python.exe scripts/migrate_followup_due_date.py
"""
import sys
import os
import json
import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pymysql

DB = dict(
    host="127.0.0.1", port=3306, user="root", password="123456",
    database="fastapiadmin", charset="utf8mb4",
)


def get_discharge(cur, case_id):
    """与后端 _followup_base_date 一致：优先 form_data 的 discharge_date / 出院日期"""
    cur.execute("select form_data from case_detail where case_id=%s", (case_id,))
    row = cur.fetchone()
    if not row or not row.get("form_data"):
        return None
    fd = row["form_data"]
    if isinstance(fd, (bytes, str)):
        fd = json.loads(fd)
    raw = fd.get("discharge_date") or fd.get("出院日期")
    if not raw:
        return None
    try:
        return datetime.datetime.strptime(str(raw)[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def main():
    conn = pymysql.connect(**DB)
    cur = conn.cursor(pymysql.cursors.DictCursor)
    cur.execute("select id, case_id, plan_month, due_date, status from follow_up "
                "where status in ('pending','overdue') order by id")
    rows = cur.fetchall()
    print(f"[1/3] 待迁移记录: {len(rows)} 条 (pending+overdue)")

    if not rows:
        print("无待迁移记录，退出")
        conn.close()
        return

    # 1) 备份（同库建备份表，可回滚）
    ids = [r["id"] for r in rows]
    ph = ",".join(["%s"] * len(ids))
    cur.execute("drop table if exists follow_up_backup_20260902")
    cur.execute(f"create table follow_up_backup_20260902 as select * from follow_up where id in ({ph})", ids)
    conn.commit()
    print(f"[1/3] 备份表 follow_up_backup_20260902 已建: {len(ids)} 条")

    # 2) 重算
    today = datetime.date.today()
    updated, skipped = 0, 0
    for r in rows:
        d = get_discharge(cur, r["case_id"])
        if not d:
            print(f"  !! 病例 {r['case_id']} 无出院日期，跳过随访 {r['id']}")
            skipped += 1
            continue
        new_due = d + datetime.timedelta(days=(r["plan_month"] or 0) * 30)
        new_status = "pending" if new_due >= today else "overdue"
        cur.execute("update follow_up set due_date=%s, status=%s where id=%s",
                    (new_due, new_status, r["id"]))
        updated += 1
    conn.commit()
    print(f"[2/3] 已重算更新 {updated} 条，跳过 {skipped} 条")

    # 3) 汇总
    cur.execute("select status, count(*) n from follow_up group by status order by status")
    dist = dict((x["status"], x["n"]) for x in cur.fetchall())
    print("[3/3] 迁移后状态分布:", dist, " 总计:", sum(dist.values()))
    conn.close()


if __name__ == "__main__":
    main()
