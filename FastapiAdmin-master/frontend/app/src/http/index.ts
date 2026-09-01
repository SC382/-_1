// 导出类型
import type { CustomRequestOptions, IResponse } from './types'
// 导出请求适配器
import { http as alovaHttp, getApiBaseUrl } from './adapters/alova'

// 导出默认请求实例
export const http = alovaHttp

// 导出动态 API 基地址解析（H5 开发期自动适配当前主机，任何网络可用）
export { getApiBaseUrl }

// 导出所有类型
export type { CustomRequestOptions, IResponse }

// 导出请求适配器
export { alovaHttp }
