<!-- 三会模板：质量分析会/联合例会/典型病例讨论会 → 后台生成真实 PPT → 预览/下载 -->
<script setup lang="ts">
import { ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import DoctorAPI, { type CaseRecordItem } from '@/api/module_cpx/doctor'

definePage({
  name: 'meeting',
  style: { navigationBarTitleText: '三会模板' },
})

const BASE_URL = import.meta.env.VITE_API_BASE_URL || ''

const range = ref('1m')
const generating = ref(false)
const templates = ref<{ type: string; name: string; desc: string }[]>([])
const records = ref<{ id: number; meeting_type: string; title: string; start_date?: string; end_date?: string; file_url?: string; file_size?: number; create_time?: string }[]>([])

const RANGE_LABEL: Record<string, string> = { '1m': '近1月', '3m': '近3月', '6m': '近6月' }

function todayStr(offsetDays = 0) {
  const n = new Date()
  n.setDate(n.getDate() + offsetDays)
  const p = (x: number) => String(x).padStart(2, '0')
  return `${n.getFullYear()}-${p(n.getMonth() + 1)}-${p(n.getDate())}`
}
function rangeDates() {
  const days = range.value === '1m' ? 30 : range.value === '3m' ? 90 : 180
  return { start: todayStr(-days), end: todayStr() }
}

async function fetchData() {
  try {
    const [tpls, recs] = await Promise.all([DoctorAPI.meetingTemplates(), DoctorAPI.meetingList()])
    templates.value = tpls
    records.value = recs
  }
  catch { /* toast */ }
}

const statusLabel = (s?: string) => {
  if (s === 'approved') return '已通过'
  if (s === 'submitted') return '待审核'
  if (s === 'rejected') return '驳回'
  return '草稿'
}

async function handleGenerate(t: { type: string; name: string }) {
  // 典型病例讨论会：先选择病例再生成
  if (t.type === 'case') {
    openCasePicker()
    return
  }
  generating.value = true
  try {
    const { start, end } = rangeDates()
    const res = await DoctorAPI.meetingGenerate({ meeting_type: t.type, start, end })
    uni.showToast({ title: 'PPT 生成成功', icon: 'success' })
    fetchData()
  }
  catch { /* toast */ }
  finally { generating.value = false }
}

// ── 典型病例讨论会：选择病例 ──────────────────────────
const casePickerVisible = ref(false)
const caseList = ref<CaseRecordItem[]>([])
const caseLoading = ref(false)
const selectedCaseId = ref<number | null>(null)

async function openCasePicker() {
  casePickerVisible.value = true
  selectedCaseId.value = null
  caseLoading.value = true
  try {
    const res = await DoctorAPI.myCases({ page_no: 1, page_size: 50 })
    caseList.value = res.items || []
  }
  catch {
    caseList.value = []
  }
  finally {
    caseLoading.value = false
  }
}

function pickCase(id: number) {
  selectedCaseId.value = id
}

async function confirmGenerate() {
  if (!selectedCaseId.value) {
    uni.showToast({ title: '请先选择病例', icon: 'none' })
    return
  }
  generating.value = true
  try {
    await DoctorAPI.meetingGenerate({ meeting_type: 'case', case_id: selectedCaseId.value })
    uni.showToast({ title: 'PPT 生成成功', icon: 'success' })
    casePickerVisible.value = false
    fetchData()
  }
  catch { /* toast */ }
  finally { generating.value = false }
}

function goPreview(r: { id: number }) {
  uni.navigateTo({ url: `/pages/meeting/preview?id=${r.id}` })
}

function handleDownload(r: { file_url?: string }) {
  if (!r.file_url) {
    uni.showToast({ title: '文件不存在', icon: 'none' })
    return
  }
  const url = `${BASE_URL}${r.file_url}`
  // #ifdef H5
  window.open(url, '_blank')
  // #endif
  // #ifndef H5
  uni.showLoading({ title: '下载中...' })
  uni.downloadFile({
    url,
    success: (res) => {
      uni.hideLoading()
      if (res.statusCode === 200) {
        uni.openDocument({ filePath: res.tempFilePath, showMenu: true, fail: () => uni.showToast({ title: '已下载，请在文件目录查看', icon: 'none' }) })
      }
      else {
        uni.showToast({ title: '下载失败', icon: 'none' })
      }
    },
    fail: () => { uni.hideLoading(); uni.showToast({ title: '下载失败', icon: 'none' }) },
  })
  // #endif
}

function handleDelete(r: { id: number; title: string }) {
  uni.showModal({
    title: '删除记录',
    content: `确定删除「${r.title}」及对应 PPT 文件吗？`,
    confirmText: '删除',
    confirmColor: '#ef4444',
    success: async (res) => {
      if (!res.confirm) return
      try {
        await DoctorAPI.meetingDelete(r.id)
        // 乐观删除：立即从本地列表移除，避免 alova GET 缓存导致删除后列表不刷新
        records.value = records.value.filter(item => item.id !== r.id)
        uni.showToast({ title: '已删除', icon: 'success' })
        fetchData()
      }
      catch {
        uni.showToast({ title: '删除失败，请重试', icon: 'none' })
      }
    },
  })
}

onShow(fetchData)
</script>

<template>
  <view class="mt-page">
    <!-- 区间选择 -->
    <view class="card">
      <text class="title">统计时间区间</text>
      <view class="range-row">
        <view
          v-for="(label, key) in RANGE_LABEL"
          :key="key"
          class="range-item"
          :class="{ active: range === key }"
          @click="range = key"
        >{{ label }}</view>
      </view>
    </view>

    <!-- 模板列表 -->
    <view class="tpl-list">
      <view v-for="t in templates" :key="t.type" class="tpl-card" @click="handleGenerate(t)">
        <view class="tpl-icon">{{ t.type === 'quality' ? '📊' : t.type === 'joint' ? '🤝' : '📋' }}</view>
        <view class="tpl-info">
          <text class="tpl-title">{{ t.name }}</text>
          <text class="tpl-desc">{{ t.desc }}</text>
        </view>
        <view class="tpl-btn">{{ generating ? '生成中' : '生成' }}</view>
      </view>
    </view>

    <!-- 生成记录 -->
    <view v-if="records.length" class="card">
      <text class="title">生成记录</text>
      <view v-for="r in records" :key="r.id" class="rec-item">
        <view class="rec-info" @click="goPreview(r)">
          <text class="rec-title">{{ r.title }}</text>
          <text class="rec-meta">{{ r.create_time }} · {{ r.file_size ? `${(r.file_size / 1024).toFixed(0)}KB` : '' }}</text>
        </view>
        <view class="rec-ops">
          <text class="rec-btn" @click="goPreview(r)">预览</text>
          <text class="rec-btn primary" @click="handleDownload(r)">下载</text>
          <text class="rec-btn danger" @click="handleDelete(r)">删除</text>
        </view>
      </view>
    </view>

    <text class="tip">* PPT 由后台自动生成，内置本院指标、问题病历、改进意见，供胸痛中心质量改进会议使用</text>
    <text class="tip" style="color: #8b5cf6;">
      * 下载说明：手机端点击"下载"后可直接保存/转发；电脑浏览器点击"下载"将直接打开 PPT 文件（可另存为）
    </text>

    <!-- 典型病例讨论会：选择病例弹层 -->
    <view v-if="casePickerVisible" class="picker-mask" @click="casePickerVisible = false">
      <view class="picker-panel" @click.stop>
        <view class="picker-head">
          <text class="picker-title">选择典型病例</text>
          <text class="picker-close" @click="casePickerVisible = false">✕</text>
        </view>
        <scroll-view scroll-y class="picker-list">
          <view v-if="caseLoading" class="picker-empty">加载中...</view>
          <view v-else-if="!caseList.length" class="picker-empty">暂无可选病例，请先建档</view>
          <view
            v-for="c in caseList"
            :key="c.id"
            class="picker-item"
            :class="{ active: selectedCaseId === c.id }"
            @click="pickCase(c.id)"
          >
            <view class="pi-main">
              <text class="pi-name">{{ c.patient_name || '-' }}</text>
              <text class="pi-meta">{{ c.case_no || '无编号' }} · {{ c.diagnose_type || '未诊断' }}</text>
            </view>
            <view class="pi-status" :class="'st-' + (c.status || 'draft')">{{ statusLabel(c.status) }}</view>
          </view>
        </scroll-view>
        <view class="picker-foot">
          <view class="pf-btn cancel" @click="casePickerVisible = false">取消</view>
          <view class="pf-btn ok" :class="{ disabled: !selectedCaseId }" @click="confirmGenerate">{{ generating ? '生成中...' : '生成 PPT' }}</view>
        </view>
      </view>
    </view>
  </view>
</template>

<style lang="scss" scoped>
.mt-page { min-height: 100vh; background: #f3f4f6; padding: 24rpx 32rpx 60rpx; }
.card { margin-bottom: 24rpx; padding: 32rpx; border-radius: 24rpx; background: #ffffff; }
.title { display: block; font-size: 30rpx; font-weight: 600; color: #1f2937; margin-bottom: 20rpx; }

.range-row { display: flex; gap: 16rpx; }
.range-item {
  flex: 1;
  text-align: center;
  padding: 16rpx 0;
  border-radius: 16rpx;
  background: #f3f4f6;
  font-size: 26rpx;
  color: #4b5563;
}
.range-item.active { background: #8b5cf6; color: #ffffff; }

.tpl-list { display: flex; flex-direction: column; gap: 20rpx; margin-bottom: 24rpx; }
.tpl-card {
  display: flex;
  align-items: center;
  padding: 32rpx;
  border-radius: 20rpx;
  background: #ffffff;
}
.tpl-icon {
  width: 88rpx;
  height: 88rpx;
  border-radius: 20rpx;
  background: #f5f3ff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 44rpx;
  margin-right: 24rpx;
}
.tpl-info { flex: 1; display: flex; flex-direction: column; }
.tpl-title { font-size: 30rpx; font-weight: 600; color: #1f2937; }
.tpl-desc { margin-top: 6rpx; font-size: 24rpx; color: #9ca3af; }
.tpl-btn {
  padding: 12rpx 28rpx;
  border-radius: 28rpx;
  background: #8b5cf6;
  color: #ffffff;
  font-size: 26rpx;
}

.rec-item { display: flex; align-items: center; padding: 20rpx 0; border-bottom: 2rpx solid #f3f4f6; }
.rec-item:last-child { border-bottom: none; }
.rec-info { flex: 1; display: flex; flex-direction: column; }
.rec-title { font-size: 28rpx; font-weight: 500; color: #1f2937; }
.rec-meta { margin-top: 6rpx; font-size: 22rpx; color: #9ca3af; }
.rec-ops { display: flex; gap: 12rpx; }
.rec-btn { padding: 8rpx 20rpx; border-radius: 20rpx; font-size: 24rpx; color: #8b5cf6; background: #f5f3ff; }
.rec-btn.primary { color: #ffffff; background: #8b5cf6; }
.rec-btn.danger { color: #ef4444; background: #fef2f2; }

.tip { display: block; margin-top: 8rpx; font-size: 22rpx; color: #c0c4cc; line-height: 1.6; }

/* 病例选择弹层 */
.picker-mask {
  position: fixed;
  left: 0;
  top: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: center;
}
.picker-panel {
  width: 86%;
  max-height: 76vh;
  display: flex;
  flex-direction: column;
  background: #ffffff;
  border-radius: 24rpx;
  overflow: hidden;
}
.picker-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 28rpx 32rpx;
  border-bottom: 1rpx solid #f3f4f6;
}
.picker-title { font-size: 32rpx; font-weight: 600; color: #1f2937; }
.picker-close { font-size: 36rpx; color: #9ca3af; padding: 0 8rpx; }
.picker-list { flex: 1; min-height: 300rpx; max-height: 52vh; }
.picker-empty { text-align: center; padding: 80rpx 0; font-size: 26rpx; color: #9ca3af; }
.picker-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 24rpx 32rpx;
  border-bottom: 1rpx solid #f7f8fa;
}
.picker-item.active { background: #f5f3ff; }
.picker-item.active .pi-name { color: #7c3aed; }
.pi-main { display: flex; flex-direction: column; gap: 6rpx; }
.pi-name { font-size: 30rpx; font-weight: 600; color: #1f2937; }
.pi-meta { font-size: 24rpx; color: #9ca3af; }
.pi-status { font-size: 22rpx; padding: 6rpx 18rpx; border-radius: 16rpx; }
.pi-status.st-approved { color: #059669; background: #ecfdf5; }
.pi-status.st-submitted { color: #d97706; background: #fffbeb; }
.pi-status.st-rejected { color: #dc2626; background: #fef2f2; }
.pi-status.st-draft { color: #6b7280; background: #f3f4f6; }
.picker-foot {
  display: flex;
  gap: 20rpx;
  padding: 24rpx 32rpx calc(24rpx + env(safe-area-inset-bottom));
  border-top: 1rpx solid #f3f4f6;
}
.pf-btn {
  flex: 1;
  text-align: center;
  padding: 20rpx 0;
  border-radius: 16rpx;
  font-size: 30rpx;
  font-weight: 500;
}
.pf-btn.cancel { background: #f3f4f6; color: #4b5563; }
.pf-btn.ok { background: #8b5cf6; color: #ffffff; }
.pf-btn.ok.disabled { opacity: 0.5; }
</style>
