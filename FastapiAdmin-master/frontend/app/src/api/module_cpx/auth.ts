/**
 * 业务（胸痛中心 cpx）登录 API —— APP 端医生/审核员/管理员共用
 * 与 web 端 src/api/cpx/auth.ts 对齐
 */
import { http } from '@/http'

export interface CpxUserInfo {
  session_id: string
  user_id: number
  username: string
  real_name?: string
  role_id?: number
  role_name?: string
  role_code?: string
  hospital_id?: number
  hospital_name?: string
  user_status?: number
}

export interface CpxLoginResult {
  access_token: string
  token_type?: string
  expires_in?: number
  userinfo?: CpxUserInfo
}

const CpxAuthAPI = {
  /**
   * 业务登录
   * @param username 登录账号
   * @param password 密码
   */
  login(username: string, password: string): Promise<CpxLoginResult> {
    return http.Post('/cpx/auth/login', { username, password }, {
      meta: { ignoreAuth: true, authRole: 'login' },
    })
  },
}

export default CpxAuthAPI
