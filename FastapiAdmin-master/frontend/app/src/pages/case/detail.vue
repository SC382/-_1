<!-- 病例详情（只读）：填报数据 + 病例时间轴 + 病例分析 + 审核反馈
     布局/组件/交互沿用填报页 fill.vue，但不提供任何输入控件与时间选择器。 -->
<script setup lang="ts">
import { computed, ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import DoctorAPI, {
  type AnalysisItem,
  type CaseDetailData,
  type FollowUpSubItem,
  type TemplateField,
  type TimelineMetric,
  type TimelineNode,
} from '@/api/module_cpx/doctor'
import { getApiBaseUrl } from '@/http'
import { safeBack } from '@/utils/back'

definePage({
  name: 'case-detail',
  style: { navigationStyle: 'custom' },
})

const statusBarHeight = uni.getSystemInfoSync().statusBarHeight || 0
const BASE_URL = getApiBaseUrl()

function goBack() {
  safeBack()
}

// ── 数据源（四个接口，统一由 caseId 驱动）────────────
const loading = ref(false)
const detail = ref<CaseDetailData | null>(null)
const tplFields = ref<TemplateField[]>([])
const timelineNodes = ref<TimelineNode[]>([])
const timelineMetrics = ref<TimelineMetric[]>([])
const analysisItems = ref<AnalysisItem[]>([])
const missingRequired = ref<{ field_code: string; field_name: string; tab: string }[]>([])
const followups = ref<FollowUpSubItem[]>([])
const activeTab = ref('')

// ── 病例状态 ───────────────────────────────────────
const statusLabel = (s?: string) => {
  if (s === 'draft') return '草稿'
  if (s === 'submitted') return '待审核'
  if (s === 'approved') return '审核通过'
  if (s === 'rejected') return '审核驳回'
  return s ?? '-'
}
const statusColor = (s?: string) => {
  if (s === 'draft') return '#9ca3af'
  if (s === 'submitted') return '#f59e0b'
  if (s === 'approved') return '#10b981'
  if (s === 'rejected') return '#ef4444'
  return '#6b7280'
}

// ── 填报数据分组（与填报页 fill.vue 完全一致）────────
const tabs = computed(() => {
  const map = new Map<string, { key: string; name: string; order: number }>()
  tplFields.value.forEach((f) => {
    const k = f.tab_name || '未分类'
    if (!map.has(k))
      map.set(k, { key: k, name: k, order: f.tab_order || 0 })
  })
  return Array.from(map.values()).sort((a, b) => a.order - b.order)
})

const fieldsByTab = computed(() => {
  const map: Record<string, TemplateField[]> = {}
  tplFields.value.forEach((f) => {
    const k = f.tab_name || '未分类'
    ;(map[k] = map[k] || []).push(f)
  })
  Object.values(map).forEach(arr => arr.sort((a, b) => (a.sort_num || 0) - (b.sort_num || 0)))
  return map
})

const currentFields = computed(() => fieldsByTab.value[activeTab.value] || [])

// ── 只读取值（无任何输入控件）──────────────────────
function options(f: TemplateField) {
  const opts = f.field_options
  if (!Array.isArray(opts))
    return []
  return opts.map((o: any) => (typeof o === 'string' ? { label: o, value: o } : { label: o.label, value: o.value }))
}

/** 取字段原始值：优先 form_data，回退病例基础字段（建档已填但未写入 form_data 的） */
function rawValue(f: TemplateField): unknown {
  const fd = detail.value?.form_data || {}
  const v = fd[f.field_code]
  if (v !== undefined && v !== null && v !== '')
    return v
  const d = detail.value
  if (!d)
    return ''
  const baseMap: Record<string, unknown> = {
    patient_name: d.patient_name,
    gender: d.gender,
    age: d.age,
    phone: d.phone,
    come_type: d.come_type,
    diagnose_type: d.diagnose_type,
    id_type: d.id_type,
    id_number: d.id_number,
    birth_date: d.birth_date,
    onset_address: d.onset_address,
    detail_address: d.detail_address,
    insurance_type: d.insurance_type,
    insurance_no: d.insurance_no,
    first_contact_time: d.first_contact_time,
  }
  return baseMap[f.field_code] ?? ''
}

/** 只读展示文本：select 转 label，其余原样（时间字段直接显示，无 picker） */
function displayValue(f: TemplateField): string {
  const raw = rawValue(f)
  if (raw === undefined || raw === null || raw === '')
    return ''
  if (f.field_type === 'select') {
    const opt = options(f).find(o => String(o.value) === String(raw))
    return opt ? String(opt.label) : String(raw)
  }
  return String(raw)
}

function imgSrc(url: unknown) {
  const s = String(url || '')
  if (!s)
    return ''
  if (s.startsWith('http'))
    return s
  return `${BASE_URL}${s}`
}

function previewImg(url: unknown) {
  const s = imgSrc(url)
  if (s)
    uni.previewImage({ urls: [s] })
}

// ── 模块一：病例时间轴 ─────────────────────────────
interface UnifiedNode {
  code: string
  name: string
  value: string
  time: string | null
  kind: 'create' | 'rescue' | 'followup'
}

/**
 * 时间轴 = 病例创建 + 后端救治节点 + 随访记录，统一按时间升序。
 * 后端 TIMELINE_NODES 仅含 10 个救治时间节点（发病→手术结束），
 * 不含「创建」「随访」，故由前端用 create_time 与 followupGroups 补齐。
 */
const unifiedTimeline = computed<UnifiedNode[]>(() => {
  const list: UnifiedNode[] = []

  // 1) 病例创建（来源：caseDetail.create_time）
  const ct = detail.value?.create_time
  if (ct)
    list.push({ code: '__created__', name: '病例创建', value: String(ct), time: String(ct), kind: 'create' })

  // 2) 救治时间节点（来源：GET /cpx/doctor/case/{id}/timeline）
  timelineNodes.value.forEach((n) => {
    const v = n.value === undefined || n.value === null || n.value === '' ? '' : String(n.value)
    list.push({ code: n.code, name: n.name, value: v, time: n.time ? String(n.time) : null, kind: 'rescue' })
  })

  // 3) 随访节点（来源：followupGroups，按 case_id 精确关联本病例）
  followups.value.forEach((f) => {
    const t = f.follow_date ? String(f.follow_date) : ''
    list.push({
      code: `followup_${f.id}`,
      name: f.plan_month ? `第 ${f.plan_month} 个月随访` : '随访',
      value: t || (f.due_date ? `计划 ${f.due_date}` : ''),
      time: t || null,
      kind: 'followup',
    })
  })

  // 已采集的按时间升序；未采集的保持原顺序排在末尾
  const filled = list.filter(n => n.time)
  const empty = list.filter(n => !n.time)
  filled.sort((a, b) => String(a.time).localeCompare(String(b.time)))
  return [...filled, ...empty]
})

const kindColor = (k: string) => {
  if (k === 'create') return '#10b981'
  if (k === 'followup') return '#8b5cf6'
  return '#2563eb'
}
const kindLabel = (k: string) => {
  if (k === 'create') return '建档'
  if (k === 'followup') return '随访'
  return '救治'
}

const metricColor = (s: string) => {
  if (s === 'pass') return '#10b981'
  if (s === 'fail') return '#ef4444'
  if (s === 'info') return '#2563eb'
  return '#9ca3af'
}
const metricText = (s: string) => {
  if (s === 'pass') return '达标'
  if (s === 'fail') return '不达标'
  if (s === 'info') return '已记录'
  return '未采集'
}

// ── 数据加载：一次并行拉取四个数据源 ───────────────
onLoad(async (query) => {
  const id = Number(query?.id || 0)
  if (!id)
    return
  loading.value = true
  try {
    // allSettled：任一辅助接口失败不阻断主详情渲染
    const [dRes, tlRes, anRes, fgRes] = await Promise.allSettled([
      DoctorAPI.caseDetail(id),
      DoctorAPI.timeline(id),
      DoctorAPI.analysis(id),
      DoctorAPI.followupGroups(),
    ])

    if (dRes.status === 'fulfilled') {
      detail.value = dRes.value
      tplFields.value = dRes.value.fields || []
      if (tabs.value.length)
        activeTab.value = tabs.value[0].key
    }
    if (tlRes.status === 'fulfilled') {
      timelineNodes.value = tlRes.value.nodes || []
      timelineMetrics.value = tlRes.value.metrics || []
    }
    if (anRes.status === 'fulfilled') {
      analysisItems.value = anRes.value.items || []
      missingRequired.value = anRes.value.missing_required || []
    }
    if (fgRes.status === 'fulfilled') {
      const group = (fgRes.value.items || []).find(g => g.case_id === id)
      followups.value = group?.followups || []
    }
  }
  finally {
    loading.value = false
  }
})

function goEdit() {
  if (!detail.value)
    return
  uni.navigateTo({ url: `/pages/case/fill?id=${detail.value.id}` })
}
</script>

<template>
  <view class="detail-page">
    <!-- 自定义蓝色导航栏（与填报页一致） -->
    <view class="nav-bar" :style="{ paddingTop: `${statusBarHeight}px` }">
      <view class="nav-back" @click="goBack">‹</view>
      <text class="nav-title">病例详情</text>
      <view class="nav-right" />
    </view>

    <view class="page-body">
      <view v-if="loading" class="loading">加载中...</view>

      <template v-else-if="detail">
        <!-- 概要 -->
        <view class="summary">
          <view class="summary-top">
            <text class="summary-name">{{ detail.patient_name || '-' }}</text>
            <text class="summary-status" :style="{ color: statusColor(detail.status) }">{{ statusLabel(detail.status) }}</text>
          </view>
          <text class="summary-no">病例号：{{ detail.case_no || '-' }}</text>
          <text class="summary-meta">{{ detail.hospital_name || '-' }} · 创建于 {{ detail.create_time || '-' }}</text>
          <text class="summary-meta">使用模板：{{ detail.template_name || '-' }}</text>
        </view>

        <!-- 模块一：病例时间轴 -->
        <view class="card">
          <text class="card-title">病例时间轴</text>

          <view v-if="timelineMetrics.length" class="metric-grid">
            <view v-for="m in timelineMetrics" :key="m.key" class="metric-card">
              <text class="metric-key">{{ m.name }}</text>
              <text class="metric-val" :style="{ color: metricColor(m.status) }">
                {{ m.minutes != null ? `${m.minutes} min` : '—' }}
              </text>
              <text class="metric-status" :style="{ color: metricColor(m.status) }">{{ metricText(m.status) }}</text>
            </view>
          </view>

          <view v-if="unifiedTimeline.length" class="timeline">
            <view v-for="(n, i) in unifiedTimeline" :key="n.code" class="tl-node">
              <view class="tl-left">
                <view class="tl-dot" :style="{ background: n.time ? kindColor(n.kind) : '#e5e7eb' }" />
                <view v-if="i < unifiedTimeline.length - 1" class="tl-line" />
              </view>
              <view class="tl-content">
                <view class="tl-head">
                  <text class="tl-name">{{ n.name }}</text>
                  <text class="tl-kind" :style="{ color: kindColor(n.kind) }">{{ kindLabel(n.kind) }}</text>
                </view>
                <text class="tl-time" :class="{ empty: !n.value }">{{ n.value || '未采集' }}</text>
              </view>
            </view>
          </view>
          <text v-else class="empty-text">暂无时间节点</text>
        </view>

        <!-- 模块二：病例分析 -->
        <view class="card">
          <text class="card-title">病例分析</text>

          <!-- 诊断结论 -->
          <view class="conclusion">
            <view class="conclusion-row">
              <text class="conclusion-label">诊断结论</text>
              <text class="conclusion-value">{{ detail.diagnose_type || '未填写' }}</text>
            </view>
            <view class="conclusion-row">
              <text class="conclusion-label">来院方式</text>
              <text class="conclusion-value">{{ detail.come_type || '未填写' }}</text>
            </view>
          </view>

          <!-- 分析依据 + 指标解读 -->
          <text v-if="analysisItems.length" class="sub-title">分析依据与指标解读</text>
          <view v-for="it in analysisItems" :key="it.key" class="metric-item" :style="{ borderLeftColor: metricColor(it.status) }">
            <view class="metric-head">
              <text class="metric-name">{{ it.name }}</text>
              <text class="metric-status" :style="{ color: metricColor(it.status) }">{{ metricText(it.status) }}</text>
            </view>
            <text class="metric-desc">{{ it.desc }}</text>
            <view class="metric-foot">
              <text class="metric-val">实际值：{{ it.minutes != null ? `${it.minutes} min` : '未采集' }}</text>
              <text v-if="it.limit != null" class="metric-limit">标准：≤{{ it.limit }} min</text>
            </view>
          </view>

          <!-- 缺失必填 -->
          <template v-if="missingRequired.length">
            <text class="sub-title warn">缺失必填字段</text>
            <view class="missing-box">
              <view v-for="m in missingRequired" :key="m.field_code" class="missing-item">
                <text class="missing-name">· {{ m.field_name }}</text>
              </view>
            </view>
          </template>
        </view>

        <!-- 填报数据（只读，分组与填报页一致） -->
        <view class="card">
          <text class="card-title">填报数据</text>

          <scroll-view v-if="tabs.length" scroll-x class="tab-bar">
            <view
              v-for="t in tabs"
              :key="t.key"
              class="tab-item"
              :class="{ active: activeTab === t.key }"
              @click="activeTab = t.key"
            >
              {{ t.name }}
            </view>
          </scroll-view>

          <view v-if="currentFields.length" class="field-list">
            <view v-for="f in currentFields" :key="f.id" class="field">
              <text class="field-label">{{ f.field_name }}</text>
              <image
                v-if="f.field_type === 'image' && displayValue(f)"
                :src="imgSrc(rawValue(f))"
                class="field-img"
                mode="aspectFit"
                @click="previewImg(rawValue(f))"
              />
              <view v-else-if="f.field_type === 'image'" class="field-value empty">未上传</view>
              <view v-else class="field-value" :class="{ empty: !displayValue(f) }">{{ displayValue(f) || '未填写' }}</view>
            </view>
          </view>
          <text v-else class="empty-text">该分类暂无字段</text>
        </view>

        <!-- 审核反馈 -->
        <view class="card">
          <text class="card-title">审核反馈</text>
          <view v-if="detail.audit_records.length">
            <view v-for="a in detail.audit_records" :key="a.id" class="audit-item">
              <view class="audit-head">
                <text class="audit-result" :style="{ color: a.audit_result === 'pass' ? '#10b981' : '#ef4444' }">
                  {{ a.audit_result === 'pass' ? '通过' : '驳回' }}
                </text>
                <text class="audit-time">{{ a.audit_time }}</text>
              </view>
              <text class="audit-auditor">审核员：{{ a.auditor_name || '-' }}</text>
              <text class="audit-comment">意见：{{ a.audit_comment || '（无）' }}</text>
            </view>
          </view>
          <text v-else class="empty-text">暂无审核记录</text>
        </view>

        <!-- 操作：仅草稿/驳回可继续编辑 -->
        <button
          v-if="detail.status === 'draft' || detail.status === 'rejected'"
          class="edit-btn"
          @click="goEdit"
        >{{ detail.status === 'rejected' ? '修改并重新提交' : '继续填报' }}</button>
      </template>

      <view v-else class="loading">病例不存在</view>
    </view>
  </view>
</template>

<style lang="scss" scoped>
.detail-page {
  min-height: 100vh;
  background: #ffffff;
  padding-bottom: 80rpx;
}

/* ── 自定义蓝色导航栏（与填报页一致）── */
.nav-bar {
  display: flex;
  align-items: center;
  height: 88rpx;
  padding-left: 24rpx;
  padding-right: 24rpx;
  background: linear-gradient(135deg, #2563eb, #1d4ed8);
}
.nav-back {
  width: 64rpx;
  height: 64rpx;
  line-height: 56rpx;
  font-size: 52rpx;
  color: #ffffff;
}
.nav-title {
  flex: 1;
  text-align: center;
  font-size: 34rpx;
  font-weight: 600;
  color: #ffffff;
  letter-spacing: 2rpx;
}
.nav-right { width: 120rpx; }

.page-body { padding-top: 24rpx; }

.loading {
  text-align: center;
  padding-top: 200rpx;
  color: #9ca3af;
}

/* ── 概要（与填报页一致）── */
.summary {
  margin: 0 32rpx 24rpx;
  padding: 32rpx;
  border-radius: 24rpx;
  background: linear-gradient(135deg, #2563eb, #1d4ed8);
}
.summary-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.summary-name {
  font-size: 38rpx;
  font-weight: 700;
  color: #ffffff;
}
.summary-status {
  font-size: 28rpx;
  font-weight: 600;
  padding: 8rpx 20rpx;
  border-radius: 28rpx;
  background: rgba(255, 255, 255, 0.92);
}
.summary-no {
  display: block;
  margin-top: 14rpx;
  font-size: 24rpx;
  color: rgba(255, 255, 255, 0.85);
}
.summary-meta {
  display: block;
  margin-top: 8rpx;
  font-size: 22rpx;
  color: rgba(255, 255, 255, 0.8);
}

/* ── 卡片（与填报页 form-card 一致）── */
.card {
  margin: 24rpx 32rpx;
  padding: 28rpx 32rpx;
  border-radius: 24rpx;
  background: #ffffff;
  border: 2rpx solid #f0f1f3;
}
.card-title {
  display: block;
  font-size: 30rpx;
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 20rpx;
}
.sub-title {
  display: block;
  margin-top: 24rpx;
  margin-bottom: 16rpx;
  font-size: 26rpx;
  font-weight: 600;
  color: #4b5563;
}
.sub-title.warn { color: #dc2626; }

.empty-text {
  display: block;
  text-align: center;
  padding: 40rpx 0;
  font-size: 26rpx;
  color: #c0c4cc;
}

/* ── 时间轴：关键指标 ── */
.metric-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20rpx;
  margin-bottom: 28rpx;
}
.metric-card {
  display: flex;
  flex-direction: column;
  padding: 24rpx;
  border-radius: 20rpx;
  background: #f9fafb;
  border: 2rpx solid #f0f1f3;
}
.metric-key {
  font-size: 24rpx;
  color: #9ca3af;
}
.metric-val {
  margin-top: 10rpx;
  font-size: 40rpx;
  font-weight: 700;
}
.metric-status {
  margin-top: 6rpx;
  font-size: 22rpx;
}

/* ── 时间轴：时间线 ── */
.timeline { padding-top: 8rpx; }
.tl-node { display: flex; }
.tl-left {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 40rpx;
  margin-right: 24rpx;
}
.tl-dot {
  width: 20rpx;
  height: 20rpx;
  border-radius: 50%;
  background: #e5e7eb;
  margin-top: 8rpx;
}
.tl-line {
  flex: 1;
  width: 4rpx;
  background: #e5e7eb;
  margin: 8rpx 0;
  min-height: 40rpx;
}
.tl-content {
  flex: 1;
  padding-bottom: 36rpx;
}
.tl-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.tl-name {
  font-size: 28rpx;
  color: #4b5563;
}
.tl-kind {
  font-size: 22rpx;
  padding: 4rpx 14rpx;
  border-radius: 20rpx;
  background: #f3f4f6;
}
.tl-time {
  display: block;
  margin-top: 8rpx;
  font-size: 30rpx;
  font-weight: 600;
  color: #1f2937;
}
.tl-time.empty {
  color: #c0c4cc;
  font-weight: 400;
}

/* ── 病例分析 ── */
.conclusion {
  padding: 24rpx;
  border-radius: 16rpx;
  background: #eff6ff;
  border: 2rpx solid #dbeafe;
}
.conclusion-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8rpx 0;
}
.conclusion-label {
  font-size: 26rpx;
  color: #6b7280;
}
.conclusion-value {
  font-size: 30rpx;
  font-weight: 600;
  color: #1d4ed8;
}

.metric-item {
  padding: 20rpx;
  border-left: 8rpx solid #e5e7eb;
  border-radius: 12rpx;
  background: #f9fafb;
  margin-bottom: 16rpx;
}
.metric-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.metric-name {
  flex: 1;
  font-size: 28rpx;
  font-weight: 600;
  color: #1f2937;
}
.metric-status {
  font-size: 26rpx;
  font-weight: 600;
}
.metric-desc {
  display: block;
  margin-top: 8rpx;
  font-size: 24rpx;
  color: #9ca3af;
}
.metric-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 12rpx;
}
.metric-val { font-size: 26rpx; color: #4b5563; }
.metric-limit { font-size: 24rpx; color: #9ca3af; }

.missing-box {
  padding: 16rpx 20rpx;
  border-radius: 12rpx;
  background: #fef2f2;
  border: 2rpx solid #fecaca;
}
.missing-item { padding: 6rpx 0; }
.missing-name { font-size: 26rpx; color: #dc2626; }

/* ── 填报数据（只读）── */
.tab-bar {
  white-space: nowrap;
  background: #ffffff;
  padding: 8rpx 0 16rpx;
  margin-bottom: 20rpx;
  border-bottom: 2rpx solid #f0f1f3;
}
.tab-item {
  display: inline-block;
  padding: 12rpx 28rpx;
  margin-right: 12rpx;
  border-radius: 32rpx;
  font-size: 26rpx;
  color: #6b7280;
  background: #f3f4f6;
}
.tab-item.active {
  background: #2563eb;
  color: #ffffff;
}

.field-list { padding-top: 8rpx; }
.field {
  margin-bottom: 28rpx;
}
.field-label {
  display: block;
  font-size: 26rpx;
  color: #4b5563;
  margin-bottom: 12rpx;
}
.field-value {
  padding: 20rpx 24rpx;
  border-radius: 16rpx;
  background: #f3f4f6;
  font-size: 30rpx;
  color: #1f2937;
  line-height: 1.5;
  word-break: break-all;
}
.field-value.empty {
  color: #9ca3af;
}
.field-img {
  width: 100%;
  height: 320rpx;
  border-radius: 16rpx;
  background: #f3f4f6;
}

/* ── 审核反馈 ── */
.audit-item {
  padding: 20rpx;
  border-radius: 16rpx;
  background: #f9fafb;
  margin-bottom: 16rpx;
}
.audit-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.audit-result {
  font-size: 28rpx;
  font-weight: 600;
}
.audit-time {
  font-size: 22rpx;
  color: #9ca3af;
}
.audit-auditor {
  display: block;
  margin-top: 12rpx;
  font-size: 24rpx;
  color: #6b7280;
}
.audit-comment {
  display: block;
  margin-top: 8rpx;
  font-size: 26rpx;
  color: #4b5563;
}

/* ── 操作按钮 ── */
.edit-btn {
  margin: 8rpx 32rpx 0;
  height: 100rpx;
  line-height: 100rpx;
  border-radius: 24rpx;
  background: #1d4ed8;
  color: #ffffff;
  font-size: 32rpx;
  font-weight: 600;
  letter-spacing: 2rpx;
}
.edit-btn::after {
  border: none;
}
</style>
