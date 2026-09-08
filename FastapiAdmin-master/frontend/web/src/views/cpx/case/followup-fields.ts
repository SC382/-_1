/**
 * 随访扩展表单展示定义（与 App 随访表单 6 大分组一致）。
 * key 为 follow_up.form_data 里的字段编码（见 doctor/schema.py FollowUpSubmitSchema）。
 */
export interface FollowupExtField {
  key: string;
  label: string;
  /** image = 图片（后端已转可访问 URL） */
  type?: "text" | "image";
}
export interface FollowupExtGroup {
  name: string;
  fields: FollowupExtField[];
}

export const FOLLOWUP_EXT_GROUPS: FollowupExtGroup[] = [
  {
    name: "基本信息",
    fields: [
      { key: "plan_date_start", label: "随访计划日期起" },
      { key: "plan_date_end", label: "随访计划日期止" },
      { key: "follow_dept", label: "随访科室" },
      { key: "follow_user", label: "随访人" },
      { key: "unplanned_admission", label: "非计划入院" },
      { key: "info_channel", label: "信息获取途径" },
      { key: "current_condition", label: "目前状况" },
      { key: "cardiac_rehab", label: "加入心脏康复计划" },
      { key: "mace", label: "出院后主要心血管不良事件" },
    ],
  },
  {
    name: "危险因素控制",
    fields: [
      { key: "bp_monitor", label: "血压监测" },
      { key: "lipid_panel", label: "血脂四项" },
      { key: "lpa", label: "脂蛋白a（LPa）" },
      { key: "fasting_glucose", label: "空腹血糖" },
      { key: "hba1c", label: "糖化血红蛋白" },
      { key: "smoking", label: "吸烟" },
      { key: "alcohol", label: "饮酒" },
      { key: "height", label: "身高（cm）" },
      { key: "weight", label: "体重（kg）" },
      { key: "bmi", label: "BMI" },
    ],
  },
  {
    name: "躯体症状与心功能评价",
    fields: [
      { key: "symptoms", label: "躯体症状" },
      { key: "nyha", label: "NYHA 分级" },
    ],
  },
  {
    name: "心电图",
    fields: [
      { key: "ecg_result", label: "心电图结果" },
      { key: "ecg_image", label: "心电图图片", type: "image" },
    ],
  },
  {
    name: "检查项目",
    fields: [
      { key: "ckmb", label: "CKMB" },
      { key: "troponin", label: "肌钙蛋白" },
      { key: "bnp", label: "脑钠肽" },
      { key: "echocardiography", label: "超声心动图" },
      { key: "coronary_angiography", label: "冠脉造影" },
      { key: "coronary_cta", label: "冠脉CTA" },
    ],
  },
  {
    name: "用药情况",
    fields: [
      { key: "med_antiplatelet", label: "抗血小板" },
      { key: "med_lipid_lowering", label: "调脂" },
      { key: "med_acei", label: "ACEI" },
      { key: "med_arb", label: "ARB" },
      { key: "med_arni", label: "ARNI" },
      { key: "med_beta_blocker", label: "β受体阻滞剂" },
      { key: "med_hypoglycemic", label: "降糖" },
      { key: "med_anticoagulant", label: "抗凝" },
      { key: "med_diuretic", label: "利尿剂" },
    ],
  },
];
