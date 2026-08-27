import { request } from "@utils";

const API_PATH = "/cpx/hospital";

export interface HospitalTable {
  id: number;
  hospital_name: string;
  hospital_level?: string;
  province?: string;
  city?: string;
  address?: string;
  contact_name?: string;
  contact_phone?: string;
  status?: number;
  doctor_count?: number;
  auditor_count?: number;
  case_count?: number;
  create_time?: string;
  update_time?: string;
}

export interface HospitalForm {
  id?: number;
  hospital_name: string;
  hospital_level?: string;
  province?: string;
  city?: string;
  address?: string;
  contact_name?: string;
  contact_phone?: string;
  status?: number;
}

export interface HospitalPageQuery {
  page_no: number;
  page_size: number;
  hospital_name?: string;
  hospital_level?: string;
  province?: string;
  status?: number;
}

export interface HospitalOption {
  id: number;
  hospital_name: string;
}

export const HospitalAPI = {
  list(query: HospitalPageQuery) {
    return request<ApiResponse<PageResult<HospitalTable>>>({ url: `${API_PATH}/list`, method: "get", params: query });
  },
  all() {
    return request<ApiResponse<HospitalOption[]>>({ url: `${API_PATH}/all`, method: "get" });
  },
  detail(id: number) {
    return request<ApiResponse<HospitalTable>>({ url: `${API_PATH}/detail/${id}`, method: "get" });
  },
  create(body: HospitalForm) {
    return request<ApiResponse>({ url: `${API_PATH}/create`, method: "post", data: body });
  },
  update(id: number, body: HospitalForm) {
    return request<ApiResponse>({ url: `${API_PATH}/update/${id}`, method: "put", data: body });
  },
  batchStatus(body: BatchType) {
    return request<ApiResponse>({ url: `${API_PATH}/status/batch`, method: "patch", data: body });
  },
};

export default HospitalAPI;
