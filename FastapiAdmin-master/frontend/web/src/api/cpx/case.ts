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

export const CaseAPI = {
  list(query: CasePageQuery) {
    return request<ApiResponse<PageResult<CaseTable>>>({ url: `${API_PATH}/list`, method: "get", params: query });
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
