import { request } from "@utils";

const API_PATH = "/cpx/template";

/** 模板字段类型（支持：文本/数字/日期/时间/日期时间/选择/图片） */
export type FieldType = "text" | "number" | "date" | "time" | "datetime" | "select" | "image";

export interface TemplateField {
  id: number;
  field_name: string;
  field_code: string;
  field_type: string;
  field_options?: string[] | unknown;
  required_flag?: number;
  sort_num?: number;
  tab_name?: string | null;
  tab_order?: number;
}

export interface TemplateTable {
  id: number;
  template_name: string;
  version?: string;
  status?: number;
  /** 发布状态 0未发布 1已发布 */
  published?: number;
  creator_id?: number;
  field_count?: number;
  create_time?: string;
}

export interface TemplateForm {
  id?: number;
  template_name: string;
  version?: string;
  status?: number;
}

export interface TemplateDetail extends TemplateTable {
  fields: TemplateField[];
}

export interface TemplatePageQuery {
  page_no: number;
  page_size: number;
  keyword?: string;
  status?: number;
}

export interface TemplateOption {
  id: number;
  template_name: string;
  version?: string;
}

export interface TemplateFieldForm {
  id?: number;
  template_id: number;
  tab_name?: string | null;
  tab_order?: number;
  field_name: string;
  field_code: string;
  field_type: string;
  field_options?: string[] | unknown;
  required_flag?: number;
  sort_num?: number;
}

export const TemplateAPI = {
  list(query: TemplatePageQuery) {
    return request<ApiResponse<PageResult<TemplateTable>>>({ url: `${API_PATH}/list`, method: "get", params: query });
  },
  all() {
    return request<ApiResponse<TemplateOption[]>>({ url: `${API_PATH}/all`, method: "get" });
  },
  detail(id: number) {
    return request<ApiResponse<TemplateDetail>>({ url: `${API_PATH}/detail/${id}`, method: "get" });
  },
  create(body: TemplateForm) {
    return request<ApiResponse>({ url: `${API_PATH}/create`, method: "post", data: body });
  },
  update(id: number, body: TemplateForm) {
    return request<ApiResponse>({ url: `${API_PATH}/update/${id}`, method: "put", data: body });
  },
  publish(id: number) {
    return request<ApiResponse>({ url: `${API_PATH}/publish/${id}`, method: "put" });
  },
  unpublish(id: number) {
    return request<ApiResponse>({ url: `${API_PATH}/unpublish/${id}`, method: "put" });
  },
  remove(id: number) {
    return request<ApiResponse>({ url: `${API_PATH}/${id}`, method: "delete" });
  },
  addField(body: TemplateFieldForm) {
    return request<ApiResponse>({ url: `${API_PATH}/fields`, method: "post", data: body });
  },
  updateField(id: number, body: Partial<TemplateFieldForm>) {
    return request<ApiResponse>({ url: `${API_PATH}/field/${id}`, method: "put", data: body });
  },
  deleteField(id: number) {
    return request<ApiResponse>({ url: `${API_PATH}/field/${id}`, method: "delete" });
  },
  copyStandard(id: number) {
    return request<ApiResponse<{ id: number; copied: number; tabs: number }>>({
      url: `${API_PATH}/copy-standard/${id}`,
      method: "post",
    });
  },
  renameTab(body: { template_id: number; old_name: string; new_name: string; tab_order?: number }) {
    return request<ApiResponse>({ url: `${API_PATH}/tab-rename`, method: "post", data: body });
  },
  deleteTab(body: { template_id: number; tab_name: string }) {
    return request<ApiResponse>({ url: `${API_PATH}/tab-delete`, method: "post", data: body });
  },
};

export default TemplateAPI;
