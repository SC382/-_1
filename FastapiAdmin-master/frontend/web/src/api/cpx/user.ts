import { request } from "@utils";

const API_PATH = "/cpx/user";

export interface DoctorTable {
  id: number;
  username: string;
  real_name: string;
  phone?: string;
  hospital_id: number;
  hospital_name?: string;
  doctor_no?: string;
  department?: string;
  title?: string;
  status?: number;
  role_name?: string;
  last_login_time?: string;
  create_time?: string;
}

export interface AuditorTable {
  id: number;
  username: string;
  real_name: string;
  phone?: string;
  hospital_id: number;
  hospital_name?: string;
  audit_level?: string;
  status?: number;
  role_name?: string;
  last_login_time?: string;
  create_time?: string;
}

export interface DoctorForm {
  id?: number;
  username: string;
  password?: string;
  real_name: string;
  phone?: string;
  hospital_id: number;
  doctor_no?: string;
  department?: string;
  title?: string;
  status?: number;
}

export interface AuditorForm {
  id?: number;
  username: string;
  password?: string;
  real_name: string;
  phone?: string;
  hospital_id: number;
  audit_level?: string;
  status?: number;
}

export interface UserPageQuery {
  page_no: number;
  page_size: number;
  hospital_id?: number;
  keyword?: string;
  phone?: string;
  department?: string;
  title?: string;
  status?: number;
}

export const UserAPI = {
  listDoctors(query: UserPageQuery) {
    return request<ApiResponse<PageResult<DoctorTable>>>({ url: `${API_PATH}/doctors`, method: "get", params: query });
  },
  listAuditors(query: UserPageQuery) {
    return request<ApiResponse<PageResult<AuditorTable>>>({ url: `${API_PATH}/auditors`, method: "get", params: query });
  },
  detail(id: number) {
    return request<ApiResponse>({ url: `${API_PATH}/detail/${id}`, method: "get" });
  },
  createDoctor(body: DoctorForm) {
    return request<ApiResponse>({ url: `${API_PATH}/doctor`, method: "post", data: body });
  },
  createAuditor(body: AuditorForm) {
    return request<ApiResponse>({ url: `${API_PATH}/auditor`, method: "post", data: body });
  },
  updateDoctor(id: number, body: Partial<DoctorForm>) {
    return request<ApiResponse>({ url: `${API_PATH}/doctor/${id}`, method: "put", data: body });
  },
  updateAuditor(id: number, body: Partial<AuditorForm>) {
    return request<ApiResponse>({ url: `${API_PATH}/auditor/${id}`, method: "put", data: body });
  },
  batchStatus(body: BatchType) {
    return request<ApiResponse>({ url: `${API_PATH}/status/batch`, method: "patch", data: body });
  },
  resetPassword(id: number, body: { password: string }) {
    return request<ApiResponse>({ url: `${API_PATH}/password/${id}`, method: "put", data: body });
  },
};

export default UserAPI;
