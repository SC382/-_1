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

/** 质控指标病例明细行（驾驶舱下钻） */
export interface QcCaseRow {
  case_id: number;
  case_no: string | null;
  patient_name: string | null;
  hospital_name: string;
  start_value: string | null;
  end_value: string | null;
  actual_min: number | null;
  /** pass 达标 / over 超阈值未达标 / invert 时间倒挂 / missing 数据缺失 / ok 无阈值有效 */
  result: "pass" | "over" | "invert" | "missing" | "ok";
}

/** 质控指标病例明细（弹窗） */
export interface QcDetail {
  key: string;
  name: string;
  desc: string;
  /** 达标阈值（分钟），无阈值指标为 null */
  limit: number | null;
  total: number;
  over: number;
  invert: number;
  missing: number;
  cases: QcCaseRow[];
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
  /** 质控指标病例明细 */
  qcDetail(key: string) {
    return request<ApiResponse<QcDetail>>({ url: `${API_PATH}/qc-detail/${key}`, method: "get" });
  },
};

export default CpxStatsAPI;
