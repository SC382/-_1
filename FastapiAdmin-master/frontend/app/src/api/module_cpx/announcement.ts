/**
 * 公告 API（cpx/announcement）：App 端只读已发布公告
 */
import { http } from '@/http'

export interface AnnouncementItem {
  id: number
  title: string
  subtitle?: string | null
  content?: string | null
  cover?: string | null
  type?: string
  sort_order: number
  status?: string
  published_at?: string | null
  expires_at?: string | null
  create_time?: string | null
  update_time?: string | null
}

export const AnnouncementAPI = {
  /** 当前生效公告列表（仅 published 且未过期） */
  active(limit = 10) {
    return http.Get<AnnouncementItem[]>('/cpx/announcement/active', { limit })
  },
  /** 公告详情（仅 published 且未过期） */
  detail(id: number) {
    return http.Get<AnnouncementItem>(`/cpx/announcement/active/${id}`)
  },
}

export default AnnouncementAPI
