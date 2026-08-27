/**
 * 增值服务 API（cpx/value-added）：App 端只读已上线服务
 */
import { http } from '@/http'

export interface ValueAddedItem {
  id: number
  name: string
  subtitle?: string | null
  icon?: string | null
  cover?: string | null
  link_type?: 'h5' | 'external' | 'internal'
  link_url?: string | null
  sort_order: number
  status?: string
  create_time?: string | null
}

export const ValueAddedAPI = {
  /** 已上线增值服务列表 */
  active(limit = 20) {
    return http.Get<ValueAddedItem[]>('/cpx/value-added/active', { limit })
  },
}

export default ValueAddedAPI
