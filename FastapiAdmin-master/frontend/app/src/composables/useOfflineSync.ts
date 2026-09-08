/**
 * 离线填报同步（病例填报专用，任务书 4.5 离线队列）：
 * - 断网时「保存草稿 / 提交审核」写入本地队列 + 本地快照，联网后按序自动重放（同一病例合并为：最后一次 save + submit）
 * - 网络错误保留在队列中（联网后继续重试）；业务/认证错误出队并记录原因，避免队列卡死
 * - App 启动（App.vue onLaunch）挂全局网络监听；网络恢复 / 页面进入（fill.vue onShow）时自动触发重放
 */
import { computed, ref } from 'vue'
import DoctorAPI, { type TemplateField } from '@/api/module_cpx/doctor'

export type OfflineOpType = 'save' | 'submit'

export interface OfflineOp {
  id: string
  caseId: number
  type: OfflineOpType
  templateId: number
  formData: Record<string, unknown>
  ts: number
  /** 出队原因（业务错误等），保留供提示 */
  error?: string
}

/** 本地表单快照：离线编辑内容 + 页面上下文，用于离线重开页面时回填继续编辑 */
export interface CaseSnapshot {
  caseId: number
  templateId: number
  templateName: string
  status?: string
  caseNo?: string
  patientName?: string
  formData: Record<string, unknown>
  ts: number
}

/** 模板字段缓存：离线渲染动态表单所需的字段定义（随模板存，跨病例复用） */
export interface TplCacheData {
  templateId: number
  templateName: string
  fields: TemplateField[]
}

const QUEUE_KEY = 'cpx_offline_queue'
const SNAPSHOT_PREFIX = 'cpx_offline_form_'
const TPL_PREFIX = 'cpx_offline_tpl_'

const queue = ref<OfflineOp[]>([])
const networkOnline = ref(true)
const flushing = ref(false)
let initialized = false

/** 待同步操作数（响应式，供页面提示条使用） */
const pendingCount = computed(() => queue.value.length)

/* ── 错误分类 ─────────────────────────────── */

/** 网络/超时类错误：可重试，保留队列；业务/认证错误：出队 */
export function isNetworkError(err: unknown): boolean {
  const e = err as { name?: string; message?: string; msg?: string } | null | undefined
  const name = e?.name || ''
  const msg = `${e?.message || ''} ${e?.msg || ''}`
  if (name === 'NetworkError' || name === 'TimeoutError')
    return true
  return /网络错误|网络异常|网络连接|请求超时|已取消|timeout|timed ?out|failed to fetch|fetch failed|network request failed|socket|connection|离线/i.test(msg)
}

/** 认证失效类错误：保留队列，待重新登录后再同步（避免误出队丢数据） */
export function isAuthError(err: unknown): boolean {
  const e = err as { message?: string; msg?: string } | null | undefined
  const msg = `${e?.message || ''} ${e?.msg || ''}`
  return /认证失效|登录已过期|未登录|401|token/i.test(msg)
}

/* ── 队列持久化 ───────────────────────────── */

function uid() {
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`
}

function loadQueue() {
  try {
    const raw = uni.getStorageSync(QUEUE_KEY)
    const arr = raw ? (typeof raw === 'string' ? JSON.parse(raw) : raw) : []
    queue.value = Array.isArray(arr) ? arr : []
  }
  catch {
    queue.value = []
  }
}

function persistQueue() {
  try {
    uni.setStorageSync(QUEUE_KEY, JSON.stringify(queue.value))
  }
  catch {
    /* 本地存储写满等：忽略，队列仅保留内存态 */
  }
}

/* ── 入队（合并策略：同病例仅保留 最后一次 save + submit） ── */

/** 离线保存：同病例 save 合并为最新一条；若已有该病例 submit，保证 submit 仍在其后 */
export function enqueueSave(caseId: number, templateId: number, formData: Record<string, unknown>): void {
  const others = queue.value.filter((o) => o.caseId !== caseId)
  const saveOp: OfflineOp = { id: uid(), caseId, type: 'save', templateId, formData: { ...formData }, ts: Date.now() }
  const hadSubmit = queue.value.some((o) => o.caseId === caseId && o.type === 'submit')
  queue.value = [...others, saveOp]
  if (hadSubmit)
    queue.value = [...queue.value, { id: uid(), caseId, type: 'submit', templateId, formData: {}, ts: Date.now() }]
  persistQueue()
}

/** 离线提交：该病例整体压缩为 [最后一次 save, submit]，保证顺序 */
export function enqueueSubmit(caseId: number, templateId: number, formData: Record<string, unknown>): void {
  const others = queue.value.filter((o) => o.caseId !== caseId)
  queue.value = [
    ...others,
    { id: uid(), caseId, type: 'save', templateId, formData: { ...formData }, ts: Date.now() },
    { id: uid(), caseId, type: 'submit', templateId, formData: {}, ts: Date.now() },
  ]
  persistQueue()
}

/* ── 本地快照 / 模板缓存 ───────────────────── */

export function writeSnapshot(caseId: number, snap: CaseSnapshot): void {
  try {
    uni.setStorageSync(`${SNAPSHOT_PREFIX}${caseId}`, JSON.stringify(snap))
  }
  catch {
    /* ignore */
  }
}

export function readSnapshot(caseId: number): CaseSnapshot | null {
  try {
    const raw = uni.getStorageSync(`${SNAPSHOT_PREFIX}${caseId}`)
    if (!raw)
      return null
    return typeof raw === 'string' ? (JSON.parse(raw) as CaseSnapshot) : (raw as CaseSnapshot)
  }
  catch {
    return null
  }
}

export function clearSnapshot(caseId: number): void {
  try {
    uni.removeStorageSync(`${SNAPSHOT_PREFIX}${caseId}`)
  }
  catch {
    /* ignore */
  }
}

export function cacheTpl(tpl: TplCacheData): void {
  if (!tpl.templateId)
    return
  try {
    uni.setStorageSync(`${TPL_PREFIX}${tpl.templateId}`, JSON.stringify(tpl))
  }
  catch {
    /* ignore */
  }
}

export function readTplCache(templateId: number): TplCacheData | null {
  try {
    const raw = uni.getStorageSync(`${TPL_PREFIX}${templateId}`)
    if (!raw)
      return null
    return typeof raw === 'string' ? (JSON.parse(raw) as TplCacheData) : (raw as TplCacheData)
  }
  catch {
    return null
  }
}

/** 队列中已无未完成项的病例，清理其快照（保持本地无残留） */
function cleanupSnapshots() {
  try {
    const info = uni.getStorageInfoSync()
    const keys: string[] = info.keys || []
    const active = new Set(queue.value.map((o) => o.caseId))
    keys.forEach((k) => {
      if (k.startsWith(SNAPSHOT_PREFIX)) {
        const cid = Number(k.slice(SNAPSHOT_PREFIX.length))
        if (!active.has(cid))
          uni.removeStorageSync(k)
      }
    })
  }
  catch {
    /* ignore */
  }
}

/* ── 网络探测 / 全局监听 ───────────────────── */

function probeNetwork(): Promise<boolean> {
  return new Promise((resolve) => {
    uni.getNetworkType({
      success: (res) => {
        networkOnline.value = res.networkType !== 'none'
        resolve(networkOnline.value)
      },
      fail: () => {
        // 拿不到网络状态（H5 安全上下文等）→ 视为在线，让请求结果兜底判断
        networkOnline.value = true
        resolve(true)
      },
    })
  })
}

/**
 * 初始化全局监听（App.vue onLaunch 调用一次）：
 * 1) 启动时探测网络，在线且有遗留队列 → 自动重放；
 * 2) 注册 uni.onNetworkStatusChange，网络恢复即触发重放。
 */
export function initOfflineSync(): void {
  if (initialized)
    return
  initialized = true
  probeNetwork().then((online) => {
    if (online && queue.value.length)
      void flushQueue()
  })
  uni.onNetworkStatusChange((res) => {
    networkOnline.value = res.isConnected
    if (res.isConnected)
      void flushQueue()
  })
}

/* ── 重放 ─────────────────────────────────── */

/**
 * 按序重放离线队列：save 成功/业务失败出队；网络/认证错误保留（保留下次）；
 * 若队列仍有其他病例则继续尝试（网络错误才中断本轮）。
 */
export async function flushQueue(): Promise<void> {
  if (flushing.value || !queue.value.length)
    return
  const online = await probeNetwork()
  if (!online)
    return
  flushing.value = true
  try {
    let guard = 0
    while (queue.value.length && guard++ < 100) {
      const op = queue.value[0]
      try {
        if (op.type === 'save')
          await DoctorAPI.saveForm(op.caseId, { template_id: op.templateId, form_data: op.formData })
        else
          await DoctorAPI.submitCase(op.caseId)
        queue.value.shift()
        persistQueue()
      }
      catch (err) {
        if (isNetworkError(err) || isAuthError(err))
          break // 网络不可达 / 登录态失效 → 保留下次重试，本轮停止
        op.error = (err as Error)?.message || '服务处理失败'
        queue.value.shift()
        persistQueue()
      }
    }
  }
  finally {
    flushing.value = false
    cleanupSnapshots()
  }
}

/** 对外暴露响应式状态（页面级） */
export function useOfflineSync() {
  return { networkOnline, pendingCount, queue, flushing }
}
