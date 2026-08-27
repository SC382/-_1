# -*- coding: utf-8 -*-
"""驾驶舱真实数据种子：近 12 个月病例 + 审核记录（幂等）。

用法:
    cd backend
    ENVIRONMENT=dev uv run python -m app.scripts.seed_dashboard_data

幂等规则：case_record 总数 >= 60 时直接跳过（防止重复灌数据）。
生成内容：
    - 2025-09 ~ 2026-08 每月 5~16 条病例（近月越多），今日固定 4 条
    - 病例状态分布：历史 approved/rejected 为主，近期 submitted/draft
    - approved/rejected 病例生成对应 audit_record（auditor=审核员）
    - 每条病例生成 case_detail（模板 4，form_data 为 JSON）
"""

import asyncio
import json
import random
from datetime import datetime, timedelta

from sqlalchemy import text

from app.core.database import async_engine

MIN_CASES = 60  # 已有病例数超过该值则跳过

SURNAMES = "赵钱孙李周吴郑王冯陈褚卫蒋沈韩杨朱秦尤许何吕施张孔曹严华金魏陶姜"
GIVEN_M = ["建国", "志强", "永刚", "海涛", "建军", "伟", "磊", "洋", "鹏", "超",
           "国栋", "志明", "立新", "建华", "国庆", "卫东", "春生", "德福", "文斌", "成明"]
GIVEN_F = ["秀英", "桂英", "玉兰", "秀兰", "丽华", "淑珍", "春梅", "小红", "晓燕",
           "雪梅", "海燕", "静", "敏", "芳", "丽", "娟", "萍", "红", "英", "慧"]
STREETS = ["中山路", "人民大道", "解放街", "建设路", "朝阳小区", "幸福家园",
           "锦绣花园", "金湖湾", "康宁路", "健康巷", "杏林街", "仁和里", "望江路", "梧桐巷"]
CITIES = ["北京市", "上海市", "广州市", "苏州市", "杭州市", "南京市", "成都市", "武汉市"]
DIAGNOSES = ["STEMI", "NSTEMI", "UA", "主动脉夹层", "肺栓塞", "低危胸痛"]
DIAG_W = [0.28, 0.22, 0.16, 0.06, 0.09, 0.19]
COME_TYPES = ["120", "自行", "转诊"]
COME_W = [0.55, 0.30, 0.15]
INSURANCES = ["职工医保", "居民医保", "新农合", "自费"]
OUTCOMES = ["好转", "治愈", "转院", "自动出院"]
CONSCIOUSNESS = ["清醒", "嗜睡", "烦躁", "昏迷"]
# 状态分布按时间段：早期（历史）→ 中期 → 近期
STATUS_W_OLD = [("approved", 0.60), ("rejected", 0.08), ("submitted", 0.20), ("draft", 0.12)]
STATUS_W_MID = [("approved", 0.50), ("rejected", 0.05), ("submitted", 0.30), ("draft", 0.15)]
STATUS_W_NEW = [("submitted", 0.60), ("draft", 0.40)]
AUDIT_PASS_CMT = ["数据完整，时间节点符合规范，同意通过。", "各项指标填报完整，通过。", "FMC 到心电图时间达标，通过。", "表单齐全，诊疗路径规范，通过。"]
AUDIT_REJECT_CMT = ["发病时间与到院时间逻辑异常，请核实后重新提交。", "必填字段缺失（心电图时间），驳回重填。", "院前与院内血压记录不一致，请修正。"]


def weighted(choices, weights):
    return random.choices(choices, weights=weights, k=1)[0]


def make_patient(gender):
    surname = random.choice(SURNAMES)
    given = random.choice(GIVEN_M if gender == "男" else GIVEN_F)
    return surname + given


def make_phone():
    return "1" + random.choice("35789") + "".join(str(random.randint(0, 9)) for _ in range(9))


def make_case_no(seq: int) -> str:
    now = datetime.now()
    return f"CASE{now:%Y%m%d}{seq:04d}"


def build_form_data(patient_name, gender, age, diagnose_type) -> dict:
    now = datetime.now()
    onset = now - timedelta(minutes=random.randint(120, 480))
    fmc = onset + timedelta(minutes=random.randint(10, 40))
    er = fmc + timedelta(minutes=random.randint(5, 20))
    ecg = er + timedelta(minutes=random.randint(3, 10))
    return {
        "patient_name": patient_name,
        "gender": gender,
        "age": str(age),
        "phone": make_phone(),
        "come_type": weighted(COME_TYPES, COME_W),
        "diagnose_type": diagnose_type,
        "card_type": "身份证",
        "birth_date": (now - timedelta(days=age * 365 + random.randint(0, 300))).strftime("%Y-%m-%d"),
        "insurance": weighted(INSURANCES, [0.5, 0.3, 0.15, 0.05]),
        "onset_address": f"{random.choice(CITIES)}{random.choice(['东城区', '西城区', '高新区', '滨江区', '开发区', '老城区'])}{random.choice(STREETS)}{random.randint(1, 500)}号",
        "onset_time": onset.strftime("%Y-%m-%d %H:%M"),
        "fmc_time": fmc.strftime("%Y-%m-%d %H:%M"),
        "call_time": onset.strftime("%Y-%m-%d %H:%M"),
        "ambulance_unit": random.choice(["市急救中心", "区人民医院120", "市中心医院120", "急救站"]),
        "ambulance_staff": random.choice(["王医生+李护士", "张医生+刘护士", "陈医生+周护士", "赵医生+孙护士"]),
        "transfer_up": random.choice(["是", "否"]),
        "consciousness": weighted(CONSCIOUSNESS, [0.8, 0.1, 0.07, 0.03]),
        "respiration": str(random.randint(16, 24)),
        "pulse": str(random.randint(70, 110)),
        "pre_heart_rate": str(random.randint(70, 120)),
        "pre_blood_pressure": f"{random.randint(90, 170)}/{random.randint(60, 100)}",
        "pre_temp": str(round(random.uniform(36.2, 37.8), 1)),
        "pre_ecg": "",
        "remote_consult": random.choice(["已远程会诊", ""]),
        "pre_medication": random.choice(["阿司匹林 300mg", "替格瑞洛 180mg", "硝酸甘油 0.5mg", ""]),
        "pre_thrombolysis": random.choice(["是", "否"]),
        "handover": random.choice(["交接顺利", "已交接急诊科", ""]),
        "clinic_no": f"JZ{random.randint(100000, 999999)}",
        "inpatient_no": f"ZY{random.randint(100000, 999999)}",
        "chief_complaint": random.choice(["胸痛 2 小时", "胸闷伴大汗 1 小时", "持续性胸骨后压榨样疼痛 3 小时", "突发胸痛伴气促 40 分钟"]),
        "assessment": random.choice(["高度怀疑 ACS，立即启动胸痛中心绿色通道", "疑似不稳定型心绞痛", "低危胸痛，门诊观察", "高度怀疑主动脉夹层，控制血压心率"]),
        "first_visit_time": er.strftime("%Y-%m-%d %H:%M"),
        "arrive_gate_time": (fmc + timedelta(minutes=random.randint(3, 15))).strftime("%Y-%m-%d %H:%M"),
        "er_heart_rate": str(random.randint(70, 120)),
        "er_blood_pressure": f"{random.randint(90, 170)}/{random.randint(60, 100)}",
        "er_respiration": str(random.randint(16, 24)),
        "er_temp": str(round(random.uniform(36.2, 37.8), 1)),
        "triage_result": random.choice(["I 级（濒危）", "II 级（危重）", "III 级（急症）"]),
        "first_ecg_time": ecg.strftime("%Y-%m-%d %H:%M"),
        "in_ecg": "",
        "remote_ecg_receive": "",
        "troponin_time": ecg.strftime("%Y-%m-%d %H:%M"),
        "troponin_result": random.choice(["<0.04", "0.05", "0.12", "0.35", "0.8", "1.2", "3.5"]),
        "lab_other": random.choice(["K 3.8 Na 141", "D-二聚体 0.3", "BUN 6.2 Cr 88", ""]),
        "consultation": random.choice(["心内科已会诊", "已电话会诊", ""]),
        "preliminary_diag": random.choice(["急性ST段抬高型心肌梗死", "急性非ST段抬高型心肌梗死", "不稳定型心绞痛", "胸痛待查"]),
        "dual_anti": random.choice(["阿司匹林+替格瑞洛", "阿司匹林+氯吡格雷"]),
        "anticoagulation": random.choice(["普通肝素 4000U", "依诺肝素 0.4ml", ""]),
        "statin": random.choice(["阿托伐他汀 40mg", "瑞舒伐他汀 20mg"]),
        "beta_blocker": random.choice(["美托洛尔 25mg bid", "比索洛尔 2.5mg qd"]),
        "reperfusion": random.choice(["急诊 PCI", "溶栓后转 PCI", "择期 PCI", "药物保守治疗"]),
        "cath_lab_activate_time": ecg.strftime("%Y-%m-%d %H:%M"),
        "arrive_cath_time": (ecg + timedelta(minutes=random.randint(20, 60))).strftime("%Y-%m-%d %H:%M"),
        "puncture_time": (ecg + timedelta(minutes=random.randint(25, 70))).strftime("%Y-%m-%d %H:%M"),
        "angio_start_time": (ecg + timedelta(minutes=random.randint(30, 80))).strftime("%Y-%m-%d %H:%M"),
        "timi_flow": random.choice(["0 级", "1 级", "2 级", "3 级"]),
        "anticoag_dose": "肝素 100U/kg",
        "balloon_time": (ecg + timedelta(minutes=random.randint(35, 95))).strftime("%Y-%m-%d %H:%M"),
        "surgery_end_time": (ecg + timedelta(minutes=random.randint(70, 150))).strftime("%Y-%m-%d %H:%M"),
        "discharge_date": (now + timedelta(days=random.randint(3, 10))).strftime("%Y-%m-%d"),
        "discharge_diag": random.choice(["冠状动脉粥样硬化性心脏病 急性前壁心肌梗死", "冠心病 急性下壁心肌梗死", "不稳定型心绞痛", "胸痛待查"]),
        "confirm_time": (fmc + timedelta(minutes=random.randint(25, 60))).strftime("%Y-%m-%d %H:%M"),
        "complications": random.choice(["无", "心源性休克", "室速", "消化道出血"]),
        "risk_factors": random.choice(["高血压、吸烟", "糖尿病、高血脂", "吸烟、肥胖", "高血压、糖尿病、吸烟"]),
        "comorbidity": random.choice(["高血压", "2型糖尿病", "COPD", "肾功能不全", "无"]),
        "discharge_medication": random.choice(["阿司匹林+替格瑞洛+阿托伐他汀", "双抗+他汀+β受体阻滞剂", "阿司匹林+氯吡格雷"]),
        "outcome": weighted(OUTCOMES, [0.82, 0.1, 0.05, 0.03]),
    }


async def main() -> None:
    async with async_engine.begin() as conn:
        total = (await conn.execute(text("SELECT COUNT(*) FROM case_record"))).scalar() or 0
        if total >= MIN_CASES:
            print(f"[跳过] case_record 已有 {total} 条（>= {MIN_CASES}），不重复灌数据。")
            return

        # 医院 / 医生 / 审核员
        hospitals = [(await conn.execute(text("SELECT id FROM hospital WHERE status=1 ORDER BY id"))).scalars().all()]
        hospitals = hospitals[0]
        doctors = (await conn.execute(text("SELECT id FROM user_account WHERE role_id=(SELECT id FROM role WHERE role_name='医生') AND status=1 ORDER BY id"))).scalars().all()
        auditor = (await conn.execute(text("SELECT id FROM user_account WHERE role_id=(SELECT id FROM role WHERE role_name='审核员') AND status=1 LIMIT 1"))).scalar()
        if not hospitals or not doctors or not auditor:
            print("[错误] 缺少医院/医生/审核员基础数据，先初始化用户与医院。")
            return
        print(f"基础数据: hospitals={hospitals}, doctors={doctors}, auditor={auditor}")

        # 生成病例计划：近 12 个月（当前月为最后一个月），近月递增
        now = datetime.now()
        plan: list[tuple[datetime, float]] = []  # (create_time, status_phase)
        for mi in range(12):
            month_count = 5 + mi  # 5 ~ 16 条/月
            month_first = datetime(now.year, now.month, 1)
            for _ in range(11 - mi):
                month_first = datetime(month_first.year, month_first.month - 1, 1) if month_first.month > 1 else datetime(month_first.year - 1, 12, 1)
            for _ in range(month_count):
                day = random.randint(1, 28)
                try:
                    dt = month_first.replace(day=day, hour=random.randint(6, 22), minute=random.randint(0, 59))
                except ValueError:
                    dt = month_first.replace(day=28, hour=random.randint(6, 22), minute=random.randint(0, 59))
                phase = "old" if mi <= 8 else ("mid" if mi <= 10 else "new")
                plan.append((dt, phase))
        # 今天固定 4 条（submitted/draft）
        today_start = datetime.combine(now.date(), datetime.min.time())
        for _ in range(4):
            plan.append((today_start + timedelta(hours=random.randint(8, 21), minutes=random.randint(0, 59)), "new"))

        plan.sort(key=lambda x: x[0])

        seq = 1000
        inserted_cases = 0
        inserted_audits = 0
        for dt, phase in plan:
            if phase == "old":
                status = weighted([s for s, _ in STATUS_W_OLD], [w for _, w in STATUS_W_OLD])
            elif phase == "mid":
                status = weighted([s for s, _ in STATUS_W_MID], [w for _, w in STATUS_W_MID])
            else:
                status = weighted([s for s, _ in STATUS_W_NEW], [w for _, w in STATUS_W_NEW])

            gender = weighted(["男", "女"], [0.62, 0.38])
            age = random.randint(42, 82)
            diagnose_type = weighted(DIAGNOSES, DIAG_W)
            hospital_id = weighted([h for h in hospitals if h in hospitals], [0.5 if h == hospitals[0] else (0.3 if h == hospitals[1] else 0.2) for h in hospitals])
            # 医生尽量取所属医院，退化为随机
            doctor_id = random.choice(doctors)
            patient_name = make_patient(gender)
            case_no = make_case_no(seq)
            seq += 1

            # 插入病例
            res = await conn.execute(
                text("""INSERT INTO case_record
                    (case_no, hospital_id, doctor_id, patient_name, gender, age, phone,
                     first_contact_time, id_type, id_number, birth_date, onset_address, insurance_type,
                     come_type, diagnose_type, status, create_time, update_time)
                    VALUES (:no,:h,:d,:name,:g,:age,:ph,:fmc,:idtype,:idno,:birth,:addr,:ins,:come,:diag,:st,:ct,:ct)"""),
                {
                    "no": case_no, "h": hospital_id, "d": doctor_id, "name": patient_name,
                    "g": gender, "age": age, "ph": make_phone(),
                    "fmc": dt - timedelta(minutes=random.randint(10, 60)),
                    "idtype": "身份证", "idno": f"{random.randint(110101, 659001)}{random.randint(1900, 2005)}{random.randint(1001, 1231)}{random.randint(1000, 9999)}",
                    "birth": (dt - timedelta(days=age * 365 + random.randint(0, 200))).strftime("%Y-%m-%d"),
                    "addr": f"{random.choice(CITIES)}{random.choice(STREETS)}{random.randint(1, 500)}号",
                    "ins": weighted(INSURANCES, [0.5, 0.3, 0.15, 0.05]),
                    "come": weighted(COME_TYPES, COME_W),
                    "diag": diagnose_type, "st": status, "ct": dt,
                },
            )
            case_id = res.lastrowid

            # 病例详情（form_data 为 JSON 列，aiomysql 参数需序列化字符串）
            form = build_form_data(patient_name, gender, age, diagnose_type)
            await conn.execute(
                text("INSERT INTO case_detail (case_id, template_id, form_data, create_time, update_time) VALUES (:c, 4, :f, :ct, :ct)"),
                {"c": case_id, "f": json.dumps(form, ensure_ascii=False), "ct": dt},
            )
            inserted_cases += 1

            # 审核记录
            if status in ("approved", "rejected"):
                audit_result = "pass" if status == "approved" else "reject"
                comment = random.choice(AUDIT_PASS_CMT) if audit_result == "pass" else random.choice(AUDIT_REJECT_CMT)
                audit_time = dt + timedelta(hours=random.randint(1, 36), minutes=random.randint(0, 59))
                await conn.execute(
                    text("INSERT INTO audit_record (case_id, auditor_id, audit_result, audit_comment, audit_time) VALUES (:c, :a, :r, :cmt, :t)"),
                    {"c": case_id, "a": auditor, "r": audit_result, "cmt": comment, "t": audit_time},
                )
                inserted_audits += 1

        print(f"[完成] 新增病例 {inserted_cases} 条、审核记录 {inserted_audits} 条、病例详情 {inserted_cases} 条")
        print("刷新 Web 首页即可看到真实数据（趋势图/审核环图/医院排行/KPI）。")


if __name__ == "__main__":
    asyncio.run(main())
