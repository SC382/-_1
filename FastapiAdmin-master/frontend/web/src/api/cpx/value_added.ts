import { request } from "@utils";

const API_PATH = "/cpx/value-added";

/** 跳转类型 */
export type ValueAddedLinkType = "h5" | "external" | "internal";
/** 状态 */
export type ValueAddedStatus = "draft" | "online" | "offline";

export interface ValueAddedItem {
  id: number;
  name: string;
  subtitle?: string | null;
  icon?: string | null;
  cover?: string | null;
  link_type: ValueAddedLinkType;
  link_url?: string | null;
  sort_order: number;
  status: ValueAddedStatus;
  creator_id?: number | null;
  remark?: string | null;
  create_time?: string | null;
  update_time?: string | null;
}

export interface ValueAddedPageQuery {
  page_no: number;
  page_size: number;
  keyword?: string;
  status?: string;
}

export interface ValueAddedForm {
  id?: number;
  name: string;
  subtitle?: string;
  icon?: string;
  cover?: string;
  link_type: string;
  link_url?: string;
  sort_order: number;
  remark?: string;
}

export const ValueAddedAPI = {
  list(query: ValueAddedPageQuery) {
    return request<ApiResponse<PageResult<ValueAddedItem>>>({ url: `${API_PATH}/list`, method: "get", params: query });
  },
  detail(id: number) {
    return request<ApiResponse<ValueAddedItem>>({ url: `${API_PATH}/detail/${id}`, method: "get" });
  },
  create(body: ValueAddedForm) {
    return request<ApiResponse>({ url: `${API_PATH}/create`, method: "post", data: body });
  },
  update(id: number, body: Partial<ValueAddedForm>) {
    return request<ApiResponse>({ url: `${API_PATH}/update/${id}`, method: "put", data: body });
  },
  online(id: number) {
    return request<ApiResponse>({ url: `${API_PATH}/online/${id}`, method: "put" });
  },
  offline(id: number) {
    return request<ApiResponse>({ url: `${API_PATH}/offline/${id}`, method: "put" });
  },
  remove(id: number) {
    return request<ApiResponse>({ url: `${API_PATH}/${id}`, method: "delete" });
  },
};

export default ValueAddedAPI;
