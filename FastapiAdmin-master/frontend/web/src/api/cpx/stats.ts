import { request } from "@utils";

const API_PATH = "/cpx/stats";

/** 数据驾驶舱统计结果 */
export interface DashboardStats {
  hospital_stats: {
    total: number;
    active: number;
    disabled: number;
  };
  user_stats: {
    doctor: number;
    auditor: number;
  };
  case_stats: {
    total: number;
    today: number;
    pending: number;
    approved: number;
    rejected: number;
    completed: number;
  };
  audit_stats: {
    total: number;
    pass: number;
    reject: number;
    pass_rate: number;
    reject_rate: number;
  };
  case_trend: {
    xAxis: string[];
    data: number[];
  };
  case_trend_monthly: {
    xAxis: string[];
    data: number[];
  };
  hospital_ranking: Array<{ name: string; value: number }>;
}

export const CpxStatsAPI = {
  /** 数据驾驶舱统计 */
  dashboard() {
    return request<ApiResponse<DashboardStats>>({ url: `${API_PATH}/dashboard`, method: "get" });
  },
  /** 统计分析 */
  analysis() {
    return request<ApiResponse>({ url: `${API_PATH}/analysis`, method: "get" });
  },
};

export default CpxStatsAPI;
