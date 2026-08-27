import { request } from "@utils";

const API_PATH = "/cpx/log";

export interface LogTable {
  id: number;
  user_id?: number;
  username?: string;
  real_name?: string;
  role_name?: string;
  hospital_name?: string;
  module?: string;
  operation?: string;
  description?: string;
  ip_address?: string;
  result?: string;
  create_time?: string;
}

export interface LogPageQuery {
  page_no: number;
  page_size: number;
  user_id?: number;
  user_name?: string;
  role_id?: number;
  hospital_id?: number;
  module?: string;
  operation?: string;
  start_time?: string;
  end_time?: string;
}

export interface RoleOption {
  id: number;
  role_name: string;
}

export const LogAPI = {
  list(query: LogPageQuery) {
    return request<ApiResponse<PageResult<LogTable>>>({ url: `${API_PATH}/list`, method: "get", params: query });
  },
  roles() {
    return request<ApiResponse<RoleOption[]>>({ url: `${API_PATH}/roles`, method: "get" });
  },
};

export default LogAPI;
