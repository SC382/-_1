<!-- 随访档案：紫色顶部功能区 + 详细患者卡片（参考截图完整还原） -->
<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { onLoad, onShow, onPullDownRefresh } from '@dcloudio/uni-app'
import DoctorAPI, { type FollowUpGroup, type FollowUpSubItem, type DoctorMe } from '@/api/module_cpx/doctor'

definePage({
  name: 'followup-archive',
  style: { navigationBarTitleText: '随访档案', enablePullDownRefresh: true },
})

const loading = ref(false)
const groups = ref<FollowUpGroup[]>([])
const me = ref<DoctorMe>({})
const activeTab = ref<'progress' | 'submitted' | 'overdue'>('progress')
const activeChip = ref<'due7' | 'expiring7' | 'all'>('due7')

const tabs = [
  { key: 'progress', label: '随访中' },
  { key: 'submitted', label: '已提交' },
  { key: 'overdue', label: '已过期' },
] as const

const chips = [
  { key: 'due7', label: '近7天需随访' },
  { key: 'expiring7', label: '近7天即将到期' },
  { key: 'all', label: '所有' },
] as const

async function loadMe() {
  try { me.value = await DoctorAPI.doctorMe() } catch { /* ignore */ }
}

async function fetchData() {
  loading.value = true
  try {
    const res = await DoctorAPI.followupGroups()
    groups.value = res.items || []
  } finally { loading.value = false }
}

const today = () => new Date().toISOString().slice(0, 10)
function addDays(s: string, n: number) {
  const d = new Date(s); d.setDate(d.getDate() + n); return d.toISOString().slice(0, 10)
}
function computeDisplay(s: string | undefined, due: string | undefined, td: string) {
  if (s === 'submitted') return '已随访'
  if (due && due < td) return '已过期'
  if (due && due >= td && due <= addDays(td, 7)) return '需随访'
  if (due && due > addDays(td, 7)) return '未开始'
  return '未随访'
}
function displayStatus(t: FollowUpSubItem) {
  return t.display_status || computeDisplay(t.status, t.due_date, today())
}

const filteredGroups = computed(() => {
  const td = today()
  let list = groups.value
  if (activeTab.value === 'progress') {
    list = list.filter((g) => g.followups.some((t) => t.status === 'pending') && !g.followups.every((t) => t.status === 'submitted'))
  } else if (activeTab.value === 'submitted') {
    list = list.filter((g) => g.followups.every((t) => t.status === 'submitted'))
  } else if (activeTab.value === 'overdue') {
    list = list.filter((g) => g.followups.some((t) => displayStatus(t) === '已过期'))
  }
  if (activeChip.value === 'due7') {
    list = list.filter((g) => g.followups.some((t) => displayStatus(t) === '需随访'))
  } else if (activeChip.value === 'expiring7') {
    const end7 = addDays(td, 7)
    list = list.filter((g) => g.valid_end && g.valid_end >= td && g.valid_end <= end7)
  }
  return list
})

function switchTab(k: typeof tabs[number]['key']) { activeTab.value = k }
function switchChip(k: typeof chips[number]['key']) { activeChip.value = k }

// ── 电话：显示号码，点击可拨打/复制/编辑 ──────────────
function phoneAction(g: FollowUpGroup) {
  if (!g.phone) {
    uni.showToast({ title: '该患者暂无电话', icon: 'none' })
    return
  }
  uni.showActionSheet({
    itemList: ['拨打电话', '复制号码', '编辑电话'],
    success: (res) => {
      if (res.tapIndex === 0) callPhone(g.phone!)
      else if (res.tapIndex === 1) copyPhone(g.phone!)
      else if (res.tapIndex === 2) editPhone(g)
    },
  })
}
function callPhone(phone: string) {
  uni.makePhoneCall({ phoneNumber: phone, fail: () => {} })
}
function copyPhone(phone: string) {
  uni.setClipboardData({ data: phone })
}
function editPhone(g: FollowUpGroup) {
  uni.showModal({
    title: '编辑电话',
    editable: true,
    placeholderText: '请输入新电话号码',
    content: g.phone || '',
    success: async (res) => {
      if (!res.confirm) return
      const val = (res.content || '').trim()
      if (!val) {
        uni.showToast({ title: '电话不能为空', icon: 'none' })
        return
      }
      try {
        await DoctorAPI.updateCase(g.case_id, { phone: val })
        uni.showToast({ title: '电话已更新', icon: 'success' })
        fetchData()
      }
      catch {
        uni.showToast({ title: '更新失败', icon: 'none' })
      }
    },
  })
}

function comeTypeClass(ct?: string) {
  if (ct === '120') return 'come-120'
  if (ct === '转诊') return 'come-transfer'
  if (ct === '自行') return 'come-self'
  return 'come-default'
}
function comeTypeText(ct?: string) { return ct || '-' }
function timelineTypeClass(s: string) {
  if (s === '已随访') return 'tl-done'
  if (s === '已过期') return 'tl-overdue'
  if (s === '需随访') return 'tl-active'
  if (s === '未开始') return 'tl-future'
  return 'tl-default'
}

// ── 随访档案：展开该患者 4 个日期的随访，点击进入详情 ──
const expandedArchive = reactive<Record<number, boolean>>({})
function toggleArchive(caseId: number) {
  expandedArchive[caseId] = !expandedArchive[caseId]
}
function goFollowupDetail(t: FollowUpSubItem) {
  uni.navigateTo({ url: `/pages/followup/detail?id=${t.id}` })
}

onLoad(async () => { await loadMe(); await fetchData() })
onShow(fetchData)
onPullDownRefresh(async () => {
  await Promise.all([loadMe(), fetchData()])
  uni.stopPullDownRefresh()
})
</script>
<template>
  <view class="fu-page">
    <!-- 顶部紫色功能区：Tabs + Chips -->
    <view class="top-header">
      <view class="tabs-row">
        <view class="tabs">
          <view v-for="t in tabs" :key="t.key" class="tab" :class="{ active: activeTab === t.key }" @click="switchTab(t.key)">{{ t.label }}</view>
        </view>
        <view class="filter-icon">▼</view>
      </view>
      <view class="chips">
        <view v-for="c in chips" :key="c.key" class="chip" :class="{ active: activeChip === c.key }" @click="switchChip(c.key)">{{ c.label }}</view>
      </view>
    </view>

    <view class="refresh-tip">下拉即可刷新...</view>

    <view v-if="filteredGroups.length" class="card-list">
      <view v-for="g in filteredGroups" :key="g.case_id" class="card">
        <view class="card-top">
          <view class="come-badge" :class="comeTypeClass(g.come_type)">{{ comeTypeText(g.come_type) }}</view>
          <view class="validity">随访有效期:{{ g.valid_start || '-' }} 至 {{ g.valid_end || '-' }}</view>
        </view>

        <view class="card-main">
          <view class="main-left">
            <text class="name">{{ g.patient_name || '-' }}</text>
            <view class="meta-row">
              <text class="gender">{{ g.gender === '女' ? '♀' : '♂' }}</text>
              <text class="age">{{ g.age || '-' }}岁</text>
              <text v-if="g.diagnose_type" class="diag-badge">{{ g.diagnose_type }}</text>
            </view>
          </view>
          <view class="main-right">
            <view class="phone-edit" @click="phoneAction(g)">
              <text class="phone-icon">📞</text>
              <text class="edit-text">{{ g.phone || '暂无电话' }}</text>
            </view>
          </view>
        </view>

        <view class="info-row">
          <view class="info-item"><text class="info-label">填报编号:</text><text class="info-val">{{ g.case_no || '-' }}</text></view>
          <view class="info-item"><text class="info-label">住院号:</text><text class="info-val">{{ g.inpatient_no || '-' }}</text></view>
        </view>
        <view class="info-row">
          <view class="info-item"><text class="info-label">出院日期:</text><text class="info-val">{{ g.discharge_date || '-' }}</text></view>
        </view>

        <view class="timeline">
          <view class="tl-track">
            <view v-for="(t, idx) in g.followups" :key="t.id" class="tl-node">
              <view v-if="idx > 0" class="tl-line" />
              <view class="tl-month">{{ t.plan_month }}月</view>
              <view class="tl-pill" :class="timelineTypeClass(displayStatus(t))">{{ displayStatus(t) }}</view>
            </view>
          </view>
        </view>

        <view class="card-footer">
          <text class="foot-label">随访人:</text>
          <text class="foot-val">{{ g.doctor_name || '-' }}</text>
        </view>

        <!-- 随访档案：点击展开该患者 4 个日期的随访 -->
        <view class="archive-entry" @click="toggleArchive(g.case_id)">
          <text class="archive-label">随访档案</text>
          <text class="archive-arrow">{{ expandedArchive[g.case_id] ? '收起 ▲' : '展开 ▼' }}</text>
        </view>
        <view v-if="expandedArchive[g.case_id]" class="archive-list">
          <view
            v-for="t in g.followups"
            :key="t.id"
            class="archive-item"
            @click="goFollowupDetail(t)"
          >
            <text class="ai-month">{{ t.plan_month }}月随访</text>
            <text class="ai-due">应随访：{{ t.due_date || '-' }}</text>
            <text class="ai-status" :class="timelineTypeClass(displayStatus(t))">{{ displayStatus(t) }}</text>
            <text class="ai-go">›</text>
          </view>
        </view>
      </view>
    </view>
    <view v-else-if="!loading" class="empty">
      <text class="empty-icon">📅</text>
      <text class="empty-text">暂无随访任务</text>
    </view>
  </view>
</template>
<style lang="scss" scoped>
.fu-page { min-height: 100vh; background: #f3f4f6; padding-bottom: 40rpx; }

/* 顶部紫色功能区 */
.top-header { background: linear-gradient(135deg, #5b5bd6, #6d6de0); padding: 24rpx 32rpx 20rpx; }
.tabs-row { display: flex; align-items: center; margin-bottom: 20rpx; }
.tabs { flex: 1; display: flex; gap: 60rpx; }
.tab {
  position: relative;
  padding: 16rpx 0 18rpx;
  font-size: 30rpx;
  color: rgba(255, 255, 255, 0.7);
  font-weight: 500;
}
.tab.active { color: #ffffff; font-weight: 600; }
.tab.active::after {
  content: '';
  position: absolute;
  left: 50%;
  bottom: -4rpx;
  transform: translateX(-50%);
  width: 56rpx;
  height: 6rpx;
  background: #ffffff;
  border-radius: 6rpx;
}
.filter-icon { font-size: 28rpx; color: #ffffff; padding: 8rpx 12rpx; }

.chips { display: flex; gap: 16rpx; }
.chip {
  padding: 12rpx 24rpx;
  border-radius: 28rpx;
  background: rgba(255, 255, 255, 0.2);
  font-size: 26rpx;
  color: #ffffff;
}
.chip.active { background: #ffffff; color: #5b5bd6; font-weight: 500; }

/* 下拉提示 */
.refresh-tip { text-align: center; padding: 28rpx 0 8rpx; font-size: 26rpx; color: #9ca3af; }

/* 卡片列表 */
.card-list { display: flex; flex-direction: column; gap: 20rpx; padding: 8rpx 24rpx 24rpx; }
.card { background: #ffffff; border-radius: 16rpx; padding: 24rpx; }

/* 卡片顶部：直角矩形来院徽标 + 有效期 */
.card-top { display: flex; align-items: center; gap: 20rpx; margin-bottom: 24rpx; }
.come-badge {
  padding: 10rpx 20rpx;
  border-radius: 6rpx;
  font-size: 26rpx;
  color: #ffffff;
  font-weight: 500;
  min-width: 60rpx;
  text-align: center;
}
.come-120 { background: #ef4444; }
.come-transfer { background: #f59e0b; }
.come-self { background: #10b981; }
.come-default { background: #9ca3af; }
.validity { font-size: 26rpx; color: #6b7280; }

/* 主信息 */
.card-main { display: flex; align-items: center; justify-content: space-between; margin-bottom: 20rpx; }
.main-left { display: flex; flex-direction: column; gap: 10rpx; }
.name { font-size: 48rpx; font-weight: 700; color: #1f2937; }
.meta-row { display: flex; align-items: center; gap: 14rpx; }
.gender { font-size: 32rpx; color: #2563eb; font-weight: 600; }
.age { font-size: 28rpx; color: #4b5563; }
.diag-badge { background: #2563eb; color: #ffffff; padding: 6rpx 16rpx; border-radius: 12rpx; font-size: 22rpx; font-weight: 500; }

.phone-edit { display: flex; align-items: center; gap: 8rpx; padding: 10rpx 16rpx; }
.phone-icon { font-size: 30rpx; }
.edit-text { font-size: 28rpx; color: #2563eb; font-weight: 500; }

/* 信息行 */
.info-row { display: flex; justify-content: space-between; margin-top: 10rpx; }
.info-item { display: flex; align-items: center; gap: 10rpx; }
.info-label { font-size: 26rpx; color: #9ca3af; }
.info-val { font-size: 26rpx; color: #1f2937; }

/* 时间线 */
.timeline { margin-top: 32rpx; padding: 20rpx 0; }
.tl-track { display: flex; align-items: flex-start; justify-content: space-between; position: relative; }
.tl-node { flex: 1; display: flex; flex-direction: column; align-items: center; position: relative; }
.tl-line {
  position: absolute;
  top: 32rpx;
  left: -50%;
  right: 50%;
  height: 2rpx;
  background: #e5e7eb;
}
.tl-node:first-child .tl-line { display: none; }
.tl-month { font-size: 28rpx; color: #6b7280; margin-bottom: 14rpx; position: relative; z-index: 1; }
.tl-pill {
  padding: 8rpx 20rpx;
  border-radius: 20rpx;
  font-size: 24rpx;
  font-weight: 500;
  position: relative;
  z-index: 1;
}
.tl-done { background: #d1fae5; color: #059669; }
.tl-overdue { background: #e5e7eb; color: #6b7280; }
.tl-active { background: #f97316; color: #ffffff; }
.tl-future { background: #f3f4f6; color: #9ca3af; }
.tl-default { background: #f3f4f6; color: #6b7280; }

/* 卡片底部 */
.card-footer { display: flex; align-items: center; gap: 10rpx; margin-top: 20rpx; padding-top: 16rpx; }
.foot-label { font-size: 26rpx; color: #9ca3af; }
.foot-val { font-size: 26rpx; color: #1f2937; }

/* 随访档案入口与展开列表 */
.archive-entry {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 16rpx;
  padding: 18rpx 20rpx;
  border-radius: 12rpx;
  background: #f8f9fb;
  border: 1rpx solid #eef0f4;
}
.archive-label { font-size: 28rpx; font-weight: 500; color: #2563eb; }
.archive-arrow { font-size: 26rpx; color: #6b7280; }
.archive-list { margin-top: 12rpx; border: 1rpx solid #eef0f4; border-radius: 12rpx; overflow: hidden; }
.archive-item {
  display: flex;
  align-items: center;
  gap: 16rpx;
  padding: 22rpx 20rpx;
  background: #ffffff;
  border-bottom: 1rpx solid #f3f4f6;
}
.archive-item:last-child { border-bottom: none; }
.ai-month { font-size: 28rpx; font-weight: 500; color: #1f2937; min-width: 150rpx; }
.ai-due { flex: 1; font-size: 24rpx; color: #6b7280; }
.ai-status { font-size: 22rpx; padding: 6rpx 16rpx; border-radius: 18rpx; font-weight: 500; }
.ai-go { font-size: 32rpx; color: #c3c8d2; }

/* 空 */
.empty { display: flex; flex-direction: column; align-items: center; padding-top: 120rpx; }
.empty-icon { font-size: 80rpx; }
.empty-text { margin-top: 20rpx; font-size: 26rpx; color: #9ca3af; }
</style>