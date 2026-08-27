/**
 * 医生端 API（cpx/doctor）：工作台统计 / 模板 / 病例建档 / 动态表单 / 我的病例
 */
import { http } from '@/http'

export interface DoctorStats {
  today_new: number
  draft: number
  pending: number
  approved: number
  rejected: number
}

export interface TemplateField {
  id: number
  field_name: string
  field_code: string
  field_type: string
  field_options?: unknown
  required_flag?: number
  sort_num?: number
  tab_name?: string | null
  tab_order?: number
}

export interface DoctorTemplate {
  id: number
  template_name: string
  version?: string
  fields: TemplateField[]
}

export interface CaseRecordItem {
  id: number
  case_no?: string
  patient_name?: string
  gender?: string
  age?: number
  phone?: string
  first_contact_time?: string
  id_type?: string
  id_number?: string
  birth_date?: string
  onset_address?: string
  detail_address?: string
  insurance_type?: string
  insurance_no?: string
  come_type?: string
  diagnose_type?: string
  status?: string
  create_time?: string
  update_time?: string
}

export interface AuditFeedback {
  id: number
  auditor_name?: string
  audit_result?: string
  audit_comment?: string
  audit_time?: string
}

export interface HospitalOpenItem {
  hospital_id: number
  hospital_name: string
  hospital_level?: string | null
  city?: string | null
  opened: boolean
  unit_count: number
  case_count: number
}

export interface CaseDetailData {
  id: number
  case_no?: string
  patient_name?: string
  gender?: string
  age?: number
  phone?: string
  first_contact_time?: string
  id_type?: string
  id_number?: string
  birth_date?: string
  onset_address?: string
  detail_address?: string
  insurance_type?: string
  insurance_no?: string
  come_type?: string
  diagnose_type?: string
  hospital_name?: string
  status?: string
  create_time?: string
  update_time?: string
  template_id?: number
  template_name?: string
  fields: TemplateField[]
  form_data: Record<string, unknown>
  checks: {
    complete: boolean
    missing_required: { field_name: string; field_code: string }[]
    time_ok: boolean
    time_issues: string[]
  }
  audit_records: AuditFeedback[]
}

export interface CaseListQuery {
  page_no: number
  page_size: number
  status?: string
  keyword?: string
  start_time?: string
  end_time?: string
  diagnose_type?: string
  come_type?: string
}

export interface FieldDict {
  tabs: { key: string; name: string }[]
  fields: FieldDef[]
  diagnose_types: { label: string; value: string }[]
  come_types: { label: string; value: string }[]
  timeline_nodes: { code: string; name: string }[]
  quality_metrics: { key: string; name: string; desc: string; start: string; end: string; limit: number | null }[]
}

export interface FieldDef {
  code: string
  name: string
  type: string
  tab: string
  options?: { label: string; value: string }[]
  required?: number
}

export interface TimelineMetric {
  key: string
  name: string
  desc: string
  start: string
  end: string
  limit: number | null
  minutes: number | null
  status: string
}

export interface TimelineNode {
  code: string
  name: string
  value?: unknown
  time?: string
}

export interface AnalysisItem {
  key: string
  name: string
  desc: string
  limit: number | null
  minutes: number | null
  status: string
}

export interface EcgConsultItem {
  id: number
  case_id?: number | null
  case_no?: string | null
  patient_name?: string | null
  image_path?: string | null
  status?: string | null
  is_initiator?: boolean
  ai_summary?: string | null
  feedback?: string | null
  target_hospital_name?: string | null
  create_time?: string | null
  feedback_time?: string | null
}

export interface EcgConsultDetail extends EcgConsultItem {
  patient_info_json?: string | null
  ai_diagnosis?: string | null
  target_hospital_id?: number | null
}

export const DoctorAPI = {
  /** 工作台统计 */
  stats() {
    return http.Get<DoctorStats>('/cpx/doctor/stats')
  },
  /** 已发布模板（含字段） */
  templates() {
    return http.Get<DoctorTemplate[]>('/cpx/doctor/templates')
  },
  /** 患者建档 */
  createCase(body: { patient_name: string; gender?: string; age?: number; phone?: string; template_id: number; come_type?: string; diagnose_type?: string; first_contact_time?: string; id_type?: string; id_number?: string; birth_date?: string; onset_address?: string; detail_address?: string; insurance_type?: string; insurance_no?: string }) {
    return http.Post<{ id: number; case_no: string }>('/cpx/doctor/case/create', body)
  },
  /** 更新基础信息 */
  updateCase(id: number, body: { patient_name?: string; gender?: string; age?: number; phone?: string; come_type?: string; diagnose_type?: string; first_contact_time?: string; id_type?: string; id_number?: string; birth_date?: string; onset_address?: string; detail_address?: string; insurance_type?: string; insurance_no?: string }) {
    return http.Put<CaseRecordItem>(`/cpx/doctor/case/${id}`, body)
  },
  /** 保存表单（草稿） */
  saveForm(id: number, body: { template_id: number; form_data: Record<string, unknown> }) {
    return http.Post<CaseRecordItem>(`/cpx/doctor/case/${id}/save`, body)
  },
  /** 提交审核 */
  submitCase(id: number) {
    return http.Post<CaseRecordItem>(`/cpx/doctor/case/${id}/submit`)
  },
  /** 病例详情（含审核反馈） */
  caseDetail(id: number) {
    return http.Get<CaseDetailData>(`/cpx/doctor/case/${id}`)
  },
  /** 删除我的病例（仅本人，级联删除关联数据） */
  deleteCase(id: number) {
    return http.Delete<{ id: number; case_no?: string; deleted?: number }>(`/cpx/doctor/case/${id}`)
  },
  /** 修改密码 */
  changePassword(body: { old_password: string; new_password: string }) {
    return http.Post(`/cpx/doctor/password`, body)
  },
  /** 字段字典 */
  fieldDict() {
    return http.Get<FieldDict>('/cpx/doctor/field-dict')
  },
  /** 时间轴 */
  timeline(id: number) {
    return http.Get<{ case_no: string; patient_name: string; nodes: TimelineNode[]; metrics: TimelineMetric[] }>(`/cpx/doctor/case/${id}/timeline`)
  },
  /** 单病例分析 */
  analysis(id: number) {
    return http.Get<{ case_no: string; patient_name: string; items: AnalysisItem[]; missing_required: { field_code: string; field_name: string; tab: string }[] }>(`/cpx/doctor/case/${id}/analysis`)
  },
  /** 当前医生基本信息 */
  doctorMe() {
    return http.Get<DoctorMe>('/cpx/doctor/me')
  },
  /** 随访：生成计划 */
  followupGenerate() {
    return http.Post<{ generated: number }>('/cpx/doctor/followup/generate')
  },
  /** 随访：列表 */
  followupList(query: { page_no: number; page_size: number; status?: string }) {
    return http.Get<PageData<FollowUpItem>>('/cpx/doctor/followup/list', query)
  },
  /** 随访：按患者聚合列表（每患者一条，展开显示 4 个月） */
  followupGroups(status?: string) {
    return http.Get<{ total: number; items: FollowUpGroup[] }>('/cpx/doctor/followup/groups', { status: status || undefined })
  },
  /** 随访：提交 */
  followupSubmit(id: number, body: { follow_date?: string; follow_status?: string; survival_status?: string; risk_control?: string; medication?: string; remark?: string }) {
    return http.Post(`/cpx/doctor/followup/${id}/submit`, body)
  },
  /** 数据概览 */
  statsOverview(months = 6) {
    return http.Get<StatsOverview>('/cpx/doctor/stats/overview', { months })
  },
  /** 区域胸痛中心网络：所有医院及其是否开通智慧胸痛（禁用缓存，保证 web 端启用/禁用医院后立即同步） */
  units() {
    return http.Get<HospitalOpenItem[]>('/cpx/doctor/units', { cacheFor: 0 })
  },
  /** 远程心电上传（AI 诊断 + 病例快照） */
  ecgUpload(params: { case_id?: number; image_path?: string }) {
    return http.Post<{ id: number; diagnosis?: string; ai_summary?: string; status?: string }>(
      '/cpx/doctor/ecg/upload',
      undefined,
      { params },
    )
  },
  /** 远程心电记录列表（发起 + 接收合并），禁用缓存 */
  ecgList() {
    return http.Get<{ items: EcgConsultItem[] }>('/cpx/doctor/ecg/list', { cacheFor: 0 })
  },
  /** 远程心电详情 */
  ecgDetail(id: number) {
    return http.Get<EcgConsultDetail>(`/cpx/doctor/ecg/detail/${id}`, { cacheFor: 0 })
  },
  /** 申请协同会诊：选接收医院后调用 */
  ecgSendConsult(id: number, body: { target_hospital_id: number }) {
    return http.Post<{ id: number; status: string; target_hospital_id: number }>(
      `/cpx/doctor/ecg/send-consult/${id}`,
      body,
    )
  },
  /** 接收方医生写反馈意见 */
  ecgFeedback(id: number, body: { feedback: string }) {
    return http.Post<{ id: number; status: string }>(`/cpx/doctor/ecg/feedback/${id}`, body)
  },
  /** AI 再认证自评 */
  selfcheck(start?: string, end?: string) {
    return http.Get<{ case_count: number; score: number; items: { key: string; name: string; desc: string; limit: number | null; total: number; pass: number; rate: number | null; ok: boolean }[]; suggestions: string[] }>('/cpx/doctor/selfcheck', { start, end })
  },
  /** 三会模板列表 */
  meetingTemplates() {
    return http.Get<{ type: string; name: string; desc: string }[]>('/cpx/doctor/meeting/templates')
  },
  /** 生成三会 PPT */
  meetingGenerate(params: { meeting_type: string; start?: string; end?: string; case_id?: number }) {
    return http.Post<{ id: number; title: string; file_url: string; file_size: number; stat: MeetingStat }>('/cpx/doctor/meeting/generate', undefined, { params })
  },
  /** 三会记录（禁用缓存，确保删除/生成后列表实时刷新） */
  meetingList() {
    return http.Get<{ id: number; meeting_type: string; title: string; start_date?: string; end_date?: string; file_url?: string; file_size?: number; create_time?: string }[]>('/cpx/doctor/meeting/list', { cacheFor: 0 })
  },
  /** 会议预览 */
  meetingPreview(id: number) {
    return http.Get<{ id: number; title: string; meeting_type: string; start_date?: string; end_date?: string; file_url?: string; create_time?: string; stat: MeetingStat }>(`/cpx/doctor/meeting/${id}`)
  },
  /** 删除生成记录 */
  meetingDelete(id: number) {
    return http.Delete(`/cpx/doctor/meeting/${id}`)
  },
  /** 我的病例列表（支持按状态/日期筛选，手动拼 URL 参数避免 alova params 兼容问题） */
  myCases(params: { status?: string; page_no?: number; page_size?: number; keyword?: string; start_time?: string; end_time?: string }) {
    const qs = new URLSearchParams()
    if (params.status) qs.set('status', params.status)
    if (params.page_no) qs.set('page_no', String(params.page_no))
    if (params.page_size) qs.set('page_size', String(params.page_size))
    if (params.keyword) qs.set('keyword', params.keyword)
    if (params.start_time) qs.set('start_time', params.start_time)
    if (params.end_time) qs.set('end_time', params.end_time)
    const suffix = qs.toString() ? `?${qs.toString()}` : ''
    // cacheFor: 0 禁用缓存，确保每次切换 Tab 都发新请求
    return http.Get<{ page_no: number; page_size: number; total: number; has_next: boolean; items: CaseRecordItem[] }>(`/cpx/doctor/case/list${suffix}`, undefined, { cacheFor: 0 } as any)
  },
  /** 认证知识库 AI 问答（回答标注来源文件与页码；v4-flash 推理耗时 30-60s，超时放宽到 120s） */
  kbAsk(question: string) {
    return http.Post<{ answer: string; sources: { source_file: string; page_no: number }[]; hit_count: number }>('/cpx/doctor/kb/ask', { question }, { timeout: 120000 })
  },
}

export interface MeetingStat {
  total: number
  status_dist: Record<string, number>
  diagnose_dist: Record<string, number>
  metrics: { key: string; name: string; limit: number | null; total: number; pass: number; rate: number | null }[]
  problems: { case_no?: string; patient_name?: string; diagnose_type?: string; status?: string }[]
  suggestions: string[]
}

/** 认证知识库问答结果 */
export interface KbAskResult {
  answer: string
  sources: { source_file: string; page_no: number }[]
  hit_count: number
}

export interface FollowUpItem {
  id: number
  case_id: number
  case_no?: string
  patient_name?: string
  plan_month?: number
  due_date?: string
  status?: string
  follow_date?: string
  follow_status?: string
  survival_status?: string
  risk_control?: string
  medication?: string
  remark?: string
}

/** 随访子项（某患者的单个月份随访任务） */
export interface FollowUpSubItem {
  id: number
  plan_month?: number
  due_date?: string
  status?: string
  display_status?: string
  follow_date?: string
  follow_status?: string
  survival_status?: string
}

/** 按患者聚合的随访分组（每患者一条，展开显示 4 个月随访） */
export interface FollowUpGroup {
  case_id: number
  patient_name?: string
  gender?: string
  age?: number
  phone?: string
  case_no?: string
  come_type?: string
  diagnose_type?: string
  discharge_date?: string
  inpatient_no?: string
  valid_start?: string
  valid_end?: string
  hospital_id?: number
  doctor_name?: string
  followups: FollowUpSubItem[]
}

/** 当前医生信息 */
export interface DoctorMe {
  real_name?: string
  username?: string
  hospital_id?: number
  hospital_name?: string
}

export interface StatsOverview {
  overview: { total: number; today_new: number; yesterday_new: number; week_new: number; month_new: number }
  diagnose_dist: { type: string; count: number }[]
  status_dist: Record<string, number>
  trend: { date: string; count: number }[]
  followup_stats: { month: string; total: number; done: number; rate: number | null }[]
  transfer: { total: number; list: { case_no?: string; patient_name?: string; diagnose_type?: string; status?: string; create_time?: string }[] }
  metrics_monthly: { month: string; cases: number; D2W?: number | null; FMC2ECG?: number | null }[]
}

export interface PageData<T> {
  page_no: number
  page_size: number
  total: number
  has_next: boolean
  items: T[]
}

export default DoctorAPI
