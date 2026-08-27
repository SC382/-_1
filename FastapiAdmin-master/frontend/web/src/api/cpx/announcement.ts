import { request } from "@utils";

const API_PATH = "/cpx/announcement";

/** 公告类型 */
export type AnnouncementType = "system" | "version" | "activity" | "notice";
/** 公告状态 */
export type AnnouncementStatus = "draft" | "published" | "offline";

export interface AnnouncementItem {
  id: number;
  title: string;
  subtitle?: string | null;
  content?: string | null;
  cover?: string | null;
  type: AnnouncementType;
  sort_order: number;
  status: AnnouncementStatus;
  published_at?: string | null;
  expires_at?: string | null;
  creator_id?: number | null;
  remark?: string | null;
  create_time?: string | null;
  update_time?: string | null;
}

export interface AnnouncementPageQuery {
  page_no: number;
  page_size: number;
  keyword?: string;
  status?: string;
  type?: string;
}

export interface AnnouncementForm {
  id?: number;
  title: string;
  subtitle?: string;
  content?: string;
  cover?: string;
  type: string;
  sort_order: number;
  expires_at?: string | null;
  remark?: string;
}

export const AnnouncementAPI = {
  list(query: AnnouncementPageQuery) {
    return request<ApiResponse<PageResult<AnnouncementItem>>>({ url: `${API_PATH}/list`, method: "get", params: query });
  },
  detail(id: number) {
    return request<ApiResponse<AnnouncementItem>>({ url: `${API_PATH}/detail/${id}`, method: "get" });
  },
  create(body: AnnouncementForm) {
    return request<ApiResponse>({ url: `${API_PATH}/create`, method: "post", data: body });
  },
  update(id: number, body: Partial<AnnouncementForm>) {
    return request<ApiResponse>({ url: `${API_PATH}/update/${id}`, method: "put", data: body });
  },
  publish(id: number) {
    return request<ApiResponse>({ url: `${API_PATH}/publish/${id}`, method: "put" });
  },
  offline(id: number) {
    return request<ApiResponse>({ url: `${API_PATH}/offline/${id}`, method: "put" });
  },
  remove(id: number) {
    return request<ApiResponse>({ url: `${API_PATH}/${id}`, method: "delete" });
  },
};

export default AnnouncementAPI;
