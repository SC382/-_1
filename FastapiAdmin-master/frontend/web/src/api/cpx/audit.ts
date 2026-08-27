import { request } from "@utils";

const API_PATH = "/cpx/audit";

export interface AuditWorkbench {
  pending_count: number;
  today_audit_count: number;
  pass_count: number;
  reject_count: number;
}

export interface AuditField {
  id: number;
  field_name: string;
  field_code: string;
  field_type: string;
  field_options?: unknown;
  required_flag?: number;
  sort_num?: number;
}

export interface AuditCheck {
  complete: boolean;
  missing_required: { field_name: string; field_code: string }[];
  time_ok: boolean;
  time_issues: string[];
}

export interface AuditDetail {
  id: number;
  case_no?: string;
  patient_name?: string;
  gender?: string;
  age?: number;
  phone?: string;
  hospital_name?: string;
  doctor_name?: string;
  status?: string;
  create_time?: string;
  template_id?: number;
  template_name?: string;
  fields: AuditField[];
  form_data: Record<string, unknown>;
  checks: AuditCheck;
  audit_records: AuditRecordItem[];
}

export interface AuditRecordItem {
  id: number;
  auditor_name?: string;
  auditor_hospital_name?: string;
  audit_result?: string;
  audit_comment?: string;
  audit_time?: string;
}

export interface AuditHistoryItem {
  id: number;
  case_id: number;
  case_no?: string;
  patient_name?: string;
  auditor_name?: string;
  audit_result?: string;
  audit_comment?: string;
  audit_time?: string;
}

export interface PendingCaseItem {
  id: number;
  case_no?: string;
  patient_name?: string;
  gender?: string;
  age?: number;
  doctor_name?: string;
  status?: string;
  create_time?: string;
}

export interface PendingQuery {
  page_no: number;
  page_size: number;
  keyword?: string;
  case_no?: string;
}

export interface HistoryQuery {
  page_no: number;
  page_size: number;
  case_no?: string;
}

export const AuditAPI = {
  workbench() {
    return request<ApiResponse<AuditWorkbench>>({ url: `${API_PATH}/workbench`, method: "get" });
  },
  pending(query: PendingQuery) {
    return request<ApiResponse<PageResult<PendingCaseItem>>>({ url: `${API_PATH}/pending`, method: "get", params: query });
  },
  detail(caseId: number) {
    return request<ApiResponse<AuditDetail>>({ url: `${API_PATH}/detail/${caseId}`, method: "get" });
  },
  approve(body: { case_id: number; audit_comment?: string }) {
    return request<ApiResponse>({ url: `${API_PATH}/approve`, method: "post", data: body });
  },
  reject(body: { case_id: number; audit_comment: string }) {
    return request<ApiResponse>({ url: `${API_PATH}/reject`, method: "post", data: body });
  },
  history(query: HistoryQuery) {
    return request<ApiResponse<PageResult<AuditHistoryItem>>>({ url: `${API_PATH}/history`, method: "get", params: query });
  },
  updateRecord(recordId: number, body: { audit_result: string; audit_comment?: string }) {
    return request<ApiResponse>({ url: `${API_PATH}/record/${recordId}`, method: "put", data: body });
  },
};

export default AuditAPI;
