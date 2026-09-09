import { request } from "@utils";

const API_PATH = "/cpx/stats";

/** 胸痛质控指标统计（单指标） */
export interface QcMetric {
  key: string;
  name: string;
  desc: string;
  /** 达标阈值（分钟），无阈值指标为 null */
  limit: number | null;
  /** 可评估病例数（起止时间均有效且逻辑正常） */
  eligible: number;
  /** 达标病例数 */
  pass: number;
  /** 达标率（%），无阈值指标为 null */
  rate: number | null;
  avg_min: number | null;
  median_min: number | null;
}

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
  qc_stats: {
    case_total: number;
    time_issue_cases: number;
    metrics: QcMetric[];
  };
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
