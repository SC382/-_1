/**
 * 胸痛学院 API（医生端只读）：在线查看 / 下载学习资源
 */
import { http } from '@/http'

export interface AcademyItem {
  id: number
  title: string
  content_type: string
  category?: string | null
  summary?: string | null
  file_path: string
  file_name?: string | null
  file_size?: number | null
  published: number
  view_count: number
  download_count: number
  create_time?: string
}

export const AcademyAPI = {
  /** 已发布内容列表（禁用缓存，保证发布/下架后即时同步） */
  list(params: { page_no?: number; page_size?: number; content_type?: string; category?: string }) {
    return http.Get<PageData<AcademyItem>>('/cpx/academy/doctor/list', { ...params, cacheFor: 0 })
  },
  /** 内容详情（浏览量+1） */
  detail(id: number) {
    return http.Get<AcademyItem>(`/cpx/academy/doctor/detail/${id}`, { cacheFor: 0 })
  },
}

export default AcademyAPI
