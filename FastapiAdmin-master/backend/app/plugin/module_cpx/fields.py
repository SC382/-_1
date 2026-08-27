# -*- coding: utf-8 -*-
"""胸痛中心标准字段字典（三端共用：Web 管理员/审核员/APP 医生端）。

- 字段定义：field_code -> {name, type, tab, options, required}
- 时间节点：TIME_FIELDS（用于时间轴 & 质控指标计算）
- 诊断类型 / 来院方式选项
所有业务字段值统一存入 case_detail.form_data（JSON），case_record 仅存列表筛选所需的
come_type / diagnose_type。
"""

# ── 诊断类型 / 来院方式 ──────────────────────────────

DIAGNOSE_TYPES = [
    {"label": "STEMI", "value": "STEMI"},
    {"label": "NSTEMI", "value": "NSTEMI"},
    {"label": "UA（不稳定心绞痛）", "value": "UA"},
    {"label": "主动脉夹层", "value": "主动脉夹层"},
    {"label": "肺栓塞", "value": "肺栓塞"},
    {"label": "低危胸痛", "value": "低危胸痛"},
]

COME_TYPES = [
    {"label": "120 急救", "value": "120"},
    {"label": "自行来院", "value": "自行"},
    {"label": "网络医院转诊", "value": "转诊"},
]

# ── 字段字典 ─────────────────────────────────────────
# tab: basic 基本信息 / prehospital 院前急救 / triage 急诊分诊 / exam 检验检查
#      treatment 院内诊疗 / pci 介入手术 / outcome 患者转归

FIELDS: list[dict] = [
    # 基本信息（patient_name/gender/age/phone/come_type/diagnose_type 建档时已填，自动带入）
    {"code": "patient_name", "name": "患者姓名", "type": "text", "tab": "basic", "required": 1},
    {"code": "gender", "name": "性别", "type": "select", "tab": "basic", "options": [{"label": "男", "value": "男"}, {"label": "女", "value": "女"}]},
    {"code": "age", "name": "年龄", "type": "number", "tab": "basic"},
    {"code": "phone", "name": "联系电话", "type": "text", "tab": "basic"},
    {"code": "come_type", "name": "来院方式", "type": "select", "tab": "basic", "options": COME_TYPES},
    {"code": "diagnose_type", "name": "诊断类型", "type": "select", "tab": "basic", "options": DIAGNOSE_TYPES},
    {"code": "card_type", "name": "证件类型", "type": "select", "tab": "basic", "options": [{"label": "身份证", "value": "身份证"}, {"label": "医保卡", "value": "医保卡"}, {"label": "其他", "value": "其他"}]},
    {"code": "birth_date", "name": "出生日期", "type": "date", "tab": "basic"},
    {"code": "insurance", "name": "医保信息", "type": "text", "tab": "basic"},
    {"code": "onset_address", "name": "发病地址", "type": "text", "tab": "basic"},
    {"code": "fmc_time", "name": "首次医疗接触时间(FMC)", "type": "datetime", "tab": "basic"},

    # 院前急救（时间）
    {"code": "onset_time", "name": "发病时间", "type": "datetime", "tab": "prehospital", "required": 1},
    {"code": "call_time", "name": "呼救时间", "type": "datetime", "tab": "prehospital"},
    {"code": "ambulance_unit", "name": "出车单位", "type": "text", "tab": "prehospital"},
    {"code": "ambulance_staff", "name": "医护人员", "type": "text", "tab": "prehospital"},
    {"code": "transfer_up", "name": "是否转送上级", "type": "select", "tab": "prehospital", "options": [{"label": "是", "value": "是"}, {"label": "否", "value": "否"}]},
    {"code": "consciousness", "name": "意识状态", "type": "select", "tab": "prehospital", "options": [{"label": "清醒", "value": "清醒"}, {"label": "嗜睡", "value": "嗜睡"}, {"label": "昏迷", "value": "昏迷"}]},
    {"code": "respiration", "name": "呼吸(次/分)", "type": "number", "tab": "prehospital"},
    {"code": "pulse", "name": "脉搏(次/分)", "type": "number", "tab": "prehospital"},
    {"code": "pre_heart_rate", "name": "院前心率(次/分)", "type": "number", "tab": "prehospital"},
    {"code": "pre_blood_pressure", "name": "院前血压(mmHg)", "type": "text", "tab": "prehospital"},
    {"code": "pre_temp", "name": "院前体温(℃)", "type": "number", "tab": "prehospital"},
    {"code": "pre_ecg", "name": "院前心电图", "type": "image", "tab": "prehospital"},
    {"code": "remote_consult", "name": "远程会诊", "type": "text", "tab": "prehospital"},
    {"code": "pre_medication", "name": "院前用药", "type": "text", "tab": "prehospital"},
    {"code": "pre_thrombolysis", "name": "院前溶栓治疗", "type": "text", "tab": "prehospital"},
    {"code": "handover", "name": "到院交接信息", "type": "text", "tab": "prehospital"},

    # 急诊分诊
    {"code": "clinic_no", "name": "门诊号", "type": "text", "tab": "triage"},
    {"code": "inpatient_no", "name": "住院号", "type": "text", "tab": "triage"},
    {"code": "chief_complaint", "name": "主诉", "type": "text", "tab": "triage"},
    {"code": "assessment", "name": "病情评估", "type": "text", "tab": "triage"},
    {"code": "first_visit_time", "name": "院内首诊接诊时间", "type": "datetime", "tab": "triage"},
    {"code": "arrive_gate_time", "name": "到达大门时间", "type": "datetime", "tab": "triage"},
    {"code": "er_heart_rate", "name": "院内心率(次/分)", "type": "number", "tab": "triage"},
    {"code": "er_blood_pressure", "name": "院内血压(mmHg)", "type": "text", "tab": "triage"},
    {"code": "er_respiration", "name": "院内呼吸(次/分)", "type": "number", "tab": "triage"},
    {"code": "er_temp", "name": "院内体温(℃)", "type": "number", "tab": "triage"},
    {"code": "triage_result", "name": "分诊结果", "type": "select", "tab": "triage", "options": [{"label": "高危", "value": "高危"}, {"label": "中危", "value": "中危"}, {"label": "低危", "value": "低危"}]},

    # 检验检查
    {"code": "first_ecg_time", "name": "首份心电图时间", "type": "datetime", "tab": "exam"},
    {"code": "in_ecg", "name": "院内心电图", "type": "image", "tab": "exam"},
    {"code": "remote_ecg_receive", "name": "接收远程心电图", "type": "image", "tab": "exam"},
    {"code": "troponin_time", "name": "肌钙蛋白抽血时间", "type": "datetime", "tab": "exam"},
    {"code": "troponin_result", "name": "肌钙蛋白结果", "type": "text", "tab": "exam"},
    {"code": "lab_other", "name": "实验室检查", "type": "text", "tab": "exam"},
    {"code": "consultation", "name": "胸痛会诊", "type": "text", "tab": "exam"},
    {"code": "preliminary_diag", "name": "初步诊断", "type": "text", "tab": "exam"},

    # 院内诊疗
    {"code": "dual_anti", "name": "双抗给药", "type": "text", "tab": "treatment"},
    {"code": "anticoagulation", "name": "术前抗凝", "type": "text", "tab": "treatment"},
    {"code": "statin", "name": "他汀", "type": "text", "tab": "treatment"},
    {"code": "beta_blocker", "name": "β受体阻滞剂", "type": "text", "tab": "treatment"},
    {"code": "reperfusion", "name": "再灌注措施", "type": "select", "tab": "treatment", "options": [{"label": "直接PCI", "value": "直接PCI"}, {"label": "溶栓", "value": "溶栓"}, {"label": "择期PCI", "value": "择期PCI"}, {"label": "药物保守", "value": "药物保守"}]},

    # 介入手术
    {"code": "cath_lab_activate_time", "name": "导管室激活时间", "type": "datetime", "tab": "pci"},
    {"code": "arrive_cath_time", "name": "到达导管室时间", "type": "datetime", "tab": "pci"},
    {"code": "puncture_time", "name": "穿刺时间", "type": "datetime", "tab": "pci"},
    {"code": "angio_start_time", "name": "造影开始时间", "type": "datetime", "tab": "pci"},
    {"code": "timi_flow", "name": "TIMI血流等级", "type": "select", "tab": "pci", "options": [{"label": "0级", "value": "0"}, {"label": "1级", "value": "1"}, {"label": "2级", "value": "2"}, {"label": "3级", "value": "3"}]},
    {"code": "anticoag_dose", "name": "术中抗凝药物剂量", "type": "text", "tab": "pci"},
    {"code": "balloon_time", "name": "球囊开通时间", "type": "datetime", "tab": "pci"},
    {"code": "surgery_end_time", "name": "手术结束时间", "type": "datetime", "tab": "pci"},

    # 患者转归
    {"code": "discharge_date", "name": "出院日期", "type": "date", "tab": "outcome"},
    {"code": "discharge_diag", "name": "出院诊断", "type": "text", "tab": "outcome"},
    {"code": "confirm_time", "name": "确诊时间", "type": "datetime", "tab": "outcome"},
    {"code": "complications", "name": "院内并发症", "type": "text", "tab": "outcome"},
    {"code": "risk_factors", "name": "危险因素", "type": "text", "tab": "outcome"},
    {"code": "comorbidity", "name": "合并疾病", "type": "text", "tab": "outcome"},
    {"code": "discharge_medication", "name": "出院用药", "type": "text", "tab": "outcome"},
    {"code": "outcome", "name": "出院转归", "type": "select", "tab": "outcome", "options": [{"label": "好转", "value": "好转"}, {"label": "治愈", "value": "治愈"}, {"label": "死亡", "value": "死亡"}, {"label": "转院", "value": "转院"}]},
]

FIELDS_BY_CODE: dict = {f["code"]: f for f in FIELDS}

# ── Tab 定义 ─────────────────────────────────────────
TABS = [
    {"key": "basic", "name": "基本信息"},
    {"key": "prehospital", "name": "院前急救"},
    {"key": "triage", "name": "急诊分诊"},
    {"key": "exam", "name": "检验检查"},
    {"key": "treatment", "name": "院内诊疗"},
    {"key": "pci", "name": "介入手术"},
    {"key": "outcome", "name": "患者转归"},
]

# ── 时间轴关键时间节点（按救治流程顺序）──────────────
# (code, 中文名)
TIMELINE_NODES = [
    ("onset_time", "发病时间"),
    ("call_time", "呼救时间"),
    ("arrive_gate_time", "到达大门"),
    ("fmc_time", "首次医疗接触 FMC"),
    ("first_ecg_time", "首份心电图"),
    ("troponin_time", "肌钙蛋白抽血"),
    ("cath_lab_activate_time", "导管室激活"),
    ("puncture_time", "穿刺"),
    ("balloon_time", "球囊开通"),
    ("surgery_end_time", "手术结束"),
]

# ── 质控指标（单病例分析）────────────────────────────
# 指标名 -> 起止时间节点 code + 达标阈值(分钟)
QUALITY_METRICS = [
    {"key": "S2FMC", "name": "发病-首次医疗接触(S2FMC)", "start": "onset_time", "end": "fmc_time", "limit": None, "desc": "症状发作到首次医疗接触时间"},
    {"key": "FMC2ECG", "name": "首次接触-首份心电图(FMC2ECG)", "start": "fmc_time", "end": "first_ecg_time", "limit": 10, "desc": "首次医疗接触到首份心电图 ≤10分钟"},
    {"key": "D2W", "name": "入门-球囊开通(D2W)", "start": "arrive_gate_time", "end": "balloon_time", "limit": 90, "desc": "进入医院大门到球囊开通 ≤90分钟"},
    {"key": "FMC2W", "name": "首次接触-球囊开通(FMC2W)", "start": "fmc_time", "end": "balloon_time", "limit": 120, "desc": "首次医疗接触到球囊开通 ≤120分钟"},
    {"key": "D2N", "name": "入门-肌钙蛋白(D2N)", "start": "arrive_gate_time", "end": "troponin_time", "limit": 20, "desc": "进门到肌钙蛋白抽血 ≤20分钟"},
]
