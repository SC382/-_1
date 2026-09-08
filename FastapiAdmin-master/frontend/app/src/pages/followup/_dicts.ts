/**
 * 随访表单字典（35 字段下拉选项，集中维护）
 * 样式对齐图片：基本信息 / 危险因素控制 / 躯体症状与心功能评价 / 心电图 / 检查项目 / 用药情况
 */

/** 是/否 通用选项 */
export const YES_NO = ['是', '否']

/** 随访科室（可下拉切换，也可手动输入） */
export const FOLLOWUP_DEPTS = ['心内科', 'CCU', '急诊', '门诊', '其他']

/** 信息获取途径 */
export const INFO_CHANNELS = ['电话随访', '门诊复查', '住院复查', '微信', '家访', '其他']

/** 目前状况 */
export const CURRENT_CONDITIONS = ['稳定', '波动', '恶化', '死亡', '其他']

/** 躯体症状 */
export const SYMPTOMS = ['无', '胸痛', '胸闷', '心悸', '气促', '乏力', '其他']

/** NYHA 心功能分级 */
export const NYHA_LEVELS = ['Ⅰ级', 'Ⅱ级', 'Ⅲ级', 'Ⅳ级']

/** 达标类（血压/血脂/LPa/血糖/糖化） */
export const REACH_STATUS = ['达标', '未达标', '未监测']

/** 检查类（心电图/检验/影像） */
export const EXAM_STATUS = ['阴性', '阳性', '未查']

/** 随访状态（是否随访） */
export const FOLLOW_STATUS = ['已随访', '未随访']

/** 生存状态 */
export const SURVIVAL_STATUS = ['存活', '死亡', '未知']

/** 出院后主要心血管不良事件 MACE（多选项示例，此处用单选常用项） */
export const MACE_OPTIONS = ['无', '心绞痛复发', '心肌梗死复发', '心力衰竭', '心源性死亡', '脑卒中', '再入院', '其他']

/** 按字段编码取选项 */
export function dictOf(field: string): string[] | undefined {
  const map: Record<string, string[]> = {
    follow_dept: FOLLOWUP_DEPTS,
    info_channel: INFO_CHANNELS,
    current_condition: CURRENT_CONDITIONS,
    symptoms: SYMPTOMS,
    nyha: NYHA_LEVELS,
    bp_monitor: REACH_STATUS,
    lipid_panel: REACH_STATUS,
    lpa: REACH_STATUS,
    fasting_glucose: REACH_STATUS,
    hba1c: REACH_STATUS,
    ecg_result: EXAM_STATUS,
    ckmb: EXAM_STATUS,
    troponin: EXAM_STATUS,
    bnp: EXAM_STATUS,
    echocardiography: EXAM_STATUS,
    coronary_angiography: EXAM_STATUS,
    coronary_cta: EXAM_STATUS,
    unplanned_admission: YES_NO,
    cardiac_rehab: YES_NO,
    smoking: YES_NO,
    alcohol: YES_NO,
    med_antiplatelet: YES_NO,
    med_lipid_lowering: YES_NO,
    med_acei: YES_NO,
    med_arb: YES_NO,
    med_arni: YES_NO,
    med_beta_blocker: YES_NO,
    med_hypoglycemic: YES_NO,
    med_anticoagulant: YES_NO,
    med_diuretic: YES_NO,
  }
  return map[field]
}
