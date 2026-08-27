import { request } from "@utils";

const API_PATH = "/cpx/auth";

/** 业务登录返回 */
export interface LoginResult {
  access_token: string;
  token_type: string;
  expires_in: number;
  userinfo: BizUserInfo;
}

/** 当前业务用户信息 */
export interface BizUserInfo {
  id: number;
  username: string;
  real_name: string;
  role_id: number;
  role_name: string;
  /** admin / auditor / doctor */
  role_code: string;
  hospital_id?: number;
  hospital_name?: string;
}

export interface LoginParams {
  username: string;
  password: string;
}

export const CpxAuthAPI = {
  login(body: LoginParams) {
    return request<ApiResponse<LoginResult>>({ url: `${API_PATH}/login`, method: "post", data: body });
  },
  logout() {
    return request<ApiResponse>({ url: `${API_PATH}/logout`, method: "post" });
  },
  userinfo() {
    return request<ApiResponse<BizUserInfo>>({ url: `${API_PATH}/userinfo`, method: "get" });
  },
};

export default CpxAuthAPI;
