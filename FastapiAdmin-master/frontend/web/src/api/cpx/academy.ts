import { request } from "@utils";

const API_PATH = "/cpx/academy";

/** 学院内容类型 */
export type AcademyType = "video" | "ppt" | "doc" | "pdf" | "other";

export interface AcademyItem {
  id: number;
  title: string;
  content_type: AcademyType;
  category?: string | null;
  summary?: string | null;
  file_path: string;
  file_name?: string | null;
  file_size?: number | null;
  cover_path?: string | null;
  published: number;
  sort_num: number;
  view_count: number;
  download_count: number;
  create_time?: string;
}

export interface AcademyPageQuery {
  page_no: number;
  page_size: number;
  keyword?: string;
  content_type?: string;
  category?: string;
  published?: number;
}

export interface AcademyForm {
  id?: number;
  title: string;
  content_type: string;
  category?: string;
  summary?: string;
  file_path: string;
  file_name?: string;
  file_size?: number;
  published: number;
  sort_num: number;
}

export interface AcademyUploadResult {
  url: string;
  file_path: string;
  file_name: string;
  file_size: number;
  content_type: string;
}

export const AcademyAPI = {
  list(query: AcademyPageQuery) {
    return request<ApiResponse<PageResult<AcademyItem>>>({ url: `${API_PATH}/list`, method: "get", params: query });
  },
  detail(id: number) {
    return request<ApiResponse<AcademyItem>>({ url: `${API_PATH}/detail/${id}`, method: "get" });
  },
  create(body: AcademyForm) {
    return request<ApiResponse>({ url: `${API_PATH}/create`, method: "post", data: body });
  },
  update(id: number, body: Partial<AcademyForm>) {
    return request<ApiResponse>({ url: `${API_PATH}/update/${id}`, method: "put", data: body });
  },
  remove(id: number) {
    return request<ApiResponse>({ url: `${API_PATH}/${id}`, method: "delete" });
  },
  publish(id: number) {
    return request<ApiResponse<{ id: number; published: number }>>({ url: `${API_PATH}/publish/${id}`, method: "put" });
  },
  upload(file: File) {
    const formData = new FormData();
    formData.append("file", file);
    return request<ApiResponse<AcademyUploadResult>>({
      url: `${API_PATH}/upload`,
      method: "post",
      data: formData,
      headers: { "Content-Type": "multipart/form-data" },
    });
  },
};

export default AcademyAPI;
