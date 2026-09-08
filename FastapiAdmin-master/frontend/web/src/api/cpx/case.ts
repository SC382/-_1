import { request } from "@utils";

const API_PATH = "/cpx/case";

/** 病例状态 */
export type CaseStatus = "draft" | "submitted" | "approved" | "rejected";

export interface CaseTable {
  id: number;
  case_no?: string;
  patient_name?: string;
  gender?: string;
  age?: number;
  phone?: string;
  come_type?: string;
  diagnose_type?: string;
  hospital_id: number;
  hospital_name?: string;
  doctor_id: number;
  doctor_name?: string;
  status?: CaseStatus;
  create_time?: string;
}

export interface AuditRecordItem {
  id: number;
  auditor_name?: string;
  auditor_hospital_name?: string;
  audit_result?: string;
  audit_comment?: string;
  audit_time?: string;
}

export interface TemplateFieldDef {
  id: number;
  field_name: string;
  field_code: string;
  field_type: string;
  field_options?: unknown;
}

export interface CaseDetail {
  id: number;
  case_no?: string;
  patient_name?: string;
  gender?: string;
  age?: number;
  phone?: string;
  come_type?: string;
  diagnose_type?: string;
  hospital_id: number;
  hospital_name?: string;
  doctor_id: number;
  doctor_name?: string;
  status?: CaseStatus;
  create_time?: string;
  update_time?: string;
  template_id?: number;
  template_name?: string;
  form_data?: Record<string, unknown>;
  template_fields: TemplateFieldDef[];
  field_dict?: TemplateFieldDef[];
  audit_records: AuditRecordItem[];
  ecg_records?: EcgRecordItem[];
}

export interface EcgRecordItem {
  id: number;
  image_path?: string | null;
  ai_diagnosis?: string | null;
  ai_summary?: string | null;
  feedback?: string | null;
  status?: string;
  create_time?: string | null;
}

export interface CasePageQuery {
  page_no: number;
  page_size: number;
  hospital_id?: number;
  doctor_id?: number;
  case_no?: string;
  patient_name?: string;
  doctor_name?: string;
  status?: string;
  start_time?: string;
  end_time?: string;
}

export interface CaseForm {
  hospital_id: number;
  doctor_id: number;
  patient_name?: string;
  gender?: string;
  age?: number;
  phone?: string;
  template_id?: number;
  form_data?: Record<string, unknown>;
  status?: string;
}

export interface TimelineNode {
  code: string;
  name: string;
  value: string | null;
  time: string | null;
}

export interface TimelineMetric {
  key: string;
  name: string;
  desc: string;
  start: string;
  end: string;
  limit: number | null;
  minutes: number | null;
  status: "pass" | "fail" | "n/a";
}

export interface CaseTimeline {
  case_no?: string;
  patient_name?: string;
  diagnose_type?: string;
  nodes: TimelineNode[];
  metrics: TimelineMetric[];
}

export interface AnalysisItem {
  key: string;
  name: string;
  desc: string;
  limit: number | null;
  minutes: number | null;
  status: "pass" | "fail" | "info" | "n/a";
}

export interface CaseAnalysis {
  case_no?: string;
  patient_name?: string;
  diagnose_type?: string;
  items: AnalysisItem[];
  missing_required: { field_code: string; field_name: string; tab?: string }[];
}

/** 随访状态枚举（中英映射用） */
export const FOLLOW_STATUS_TEXT: Record<string, string> = {
  pending: "随访中",
  submitted: "已提交",
  overdue: "已过期",
};
export const FOLLOW_DONE_TEXT: Record<string, string> = {
  followed: "已随访",
  unfollowed: "未随访",
};
export const SURVIVAL_TEXT: Record<string, string> = {
  alive: "存活",
  dead: "死亡",
  unknown: "未知",
};
export const PLAN_MONTH_TEXT: Record<number, string> = {
  1: "1个月",
  3: "3个月",
  6: "6个月",
  12: "12个月",
};

export interface CaseFollowupItem {
  id: number;
  case_id: number;
  patient_name?: string | null;
  doctor_id: number;
  doctor_name?: string | null;
  plan_month?: number | null;
  due_date?: string | null;
  status?: string | null;
  follow_date?: string | null;
  follow_status?: string | null;
  survival_status?: string | null;
  risk_control?: string | null;
  medication?: string | null;
  remark?: string | null;
  create_time?: string | null;
  update_time?: string | null;
  /** App 端完整随访表单（form_data JSON 展开，含 ecg_image 绝对 URL；无扩展数据为 null） */
  form_data?: Record<string, unknown> | null;
}

export interface CaseFollowup {
  case_no?: string;
  patient_name?: string;
  total: number;
  items: CaseFollowupItem[];
}

export const CaseAPI = {
  list(query: CasePageQuery) {
    return request<ApiResponse<PageResult<CaseTable>>>({ url: `${API_PATH}/list`, method: "get", params: query });
  },
  /** 救治时间轴（节点时间线 + 关键质控指标） */
  timeline(id: number) {
    return request<ApiResponse<CaseTimeline>>({ url: `${API_PATH}/timeline/${id}`, method: "get" });
  },
  /** 单病例分析（质控指标校验 + 必填缺失清单） */
  analysis(id: number) {
    return request<ApiResponse<CaseAnalysis>>({ url: `${API_PATH}/analysis/${id}`, method: "get" });
  },
  /** 病例随访记录详情（按随访计划月、应随访日期排序） */
  followup(id: number) {
    return request<ApiResponse<CaseFollowup>>({ url: `${API_PATH}/followup/${id}`, method: "get" });
  },
  /** 导出病例数据 Excel（带当前筛选条件，返回 Blob） */
  exportExcel(query: Omit<CasePageQuery, "page_no" | "page_size">) {
    return request<Blob>({ url: `${API_PATH}/export`, method: "get", params: query, responseType: "blob" });
  },
  /** 导出病例数据 PDF（带当前筛选条件，返回 Blob） */
  exportPdf(query: Omit<CasePageQuery, "page_no" | "page_size">) {
    return request<Blob>({ url: `${API_PATH}/export_pdf`, method: "get", params: query, responseType: "blob" });
  },
  /** 导出单个病例报告 PDF（按病例 ID） */
  exportPdfById(id: number) {
    return request<Blob>({ url: `${API_PATH}/export_pdf/${id}`, method: "get", responseType: "blob" });
  },
  detail(id: number) {
    return request<ApiResponse<CaseDetail>>({ url: `${API_PATH}/detail/${id}`, method: "get" });
  },
  create(body: CaseForm) {
    return request<ApiResponse>({ url: `${API_PATH}/create`, method: "post", data: body });
  },
  submit(id: number) {
    return request<ApiResponse>({ url: `${API_PATH}/submit/${id}`, method: "post" });
  },
  update(id: number, body: { patient_name?: string; gender?: string; age?: number; phone?: string }) {
    return request<ApiResponse>({ url: `${API_PATH}/${id}`, method: "put", data: body });
  },
  remove(id: number) {
    return request<ApiResponse>({ url: `${API_PATH}/${id}`, method: "delete" });
  },
};

export default CaseAPI;
