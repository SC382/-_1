<!-- 随访管理：紫色顶部功能区（Tabs + Chips + 搜索 + 筛选） + 患者卡片 + 可点击随访时间线 -->
<script setup lang="ts">
import { computed, ref } from 'vue'
import { onLoad, onShow, onPullDownRefresh } from '@dcloudio/uni-app'
import DoctorAPI, { type FollowUpGroup, type FollowUpSubItem, type DoctorMe } from '@/api/module_cpx/doctor'

definePage({
  name: 'followup-archive',
  style: { navigationBarTitleText: '随访管理', enablePullDownRefresh: true },
})

const loading = ref(false)
const groups = ref<FollowUpGroup[]>([])
const me = ref<DoctorMe>({})
const activeTab = ref<'progress' | 'submitted' | 'overdue'>('progress')
const activeChip = ref<'due7' | 'expiring7' | 'all'>('due7')

// 搜索与高级筛选
const keyword = ref('')
const showFilter = ref(false)
const filterComeType = ref('')
const filterDiagnose = ref('')

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

  // ① 顶部 Tab（按组判定）
  if (activeTab.value === 'progress') {
    list = list.filter((g) => g.followups.some((t) => t.status === 'pending') && !g.followups.every((t) => t.status === 'submitted'))
  } else if (activeTab.value === 'submitted') {
    list = list.filter((g) => g.followups.every((t) => t.status === 'submitted'))
  } else if (activeTab.value === 'overdue') {
    list = list.filter((g) => g.followups.some((t) => displayStatus(t) === '已过期'))
  }

  // ② Chips 仅对「随访中」生效（其余 Tab 下 chips 与 Tab 语义互斥，会造成空列表）
  if (activeTab.value === 'progress') {
    if (activeChip.value === 'due7') {
      list = list.filter((g) => g.followups.some((t) => displayStatus(t) === '需随访'))
    } else if (activeChip.value === 'expiring7') {
      const end7 = addDays(td, 7)
      list = list.filter((g) => g.valid_end && g.valid_end >= td && g.valid_end <= end7)
    }
  }

  // ③ 高级筛选（来院方式 / 诊断类型）
  if (filterComeType.value) {
    list = list.filter((g) => (g.come_type || '其他') === filterComeType.value)
  }
  if (filterDiagnose.value) {
    list = list.filter((g) => (g.diagnose_type || '其他') === filterDiagnose.value)
  }

  // ④ 关键词搜索（患者姓名 / 病例号）
  const kw = keyword.value.trim().toLowerCase()
  if (kw) {
    list = list.filter(
      (g) =>
        (g.patient_name || '').toLowerCase().includes(kw) ||
        (g.case_no || '').toLowerCase().includes(kw),
    )
  }
  return list
})

// 筛选面板可选项（从当前数据动态提取）
const comeTypeOptions = computed(() => {
  const s = new Set<string>()
  groups.value.forEach((g) => s.add(g.come_type || '其他'))
  return [...s]
})
const diagnoseOptions = computed(() => {
  const s = new Set<string>()
  groups.value.forEach((g) => s.add(g.diagnose_type || '其他'))
  return [...s]
})
const filterCount = computed(
  () => (filterComeType.value ? 1 : 0) + (filterDiagnose.value ? 1 : 0),
)
const hasFilter = computed(() => filterCount.value > 0 || !!keyword.value.trim())

function switchTab(k: typeof tabs[number]['key']) {
  activeTab.value = k
  // 切 Tab 时重置 chips，避免非「随访中」Tab 下残留互斥条件
  activeChip.value = k === 'progress' ? 'due7' : 'all'
}
function switchChip(k: typeof chips[number]['key']) { activeChip.value = k }

function openFilter() { showFilter.value = true }
function closeFilter() { showFilter.value = false }
function resetFilter() {
  filterComeType.value = ''
  filterDiagnose.value = ''
}
function clearAllFilter() {
  keyword.value = ''
  resetFilter()
  showFilter.value = false
}

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

// ── 点击时间线节点直接进入该条随访详情 ──
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
    <!-- 顶部紫色功能区：Tabs + Chips + 搜索 -->
    <view class="top-header">
      <view class="tabs-row">
        <view class="tabs">
          <view v-for="t in tabs" :key="t.key" class="tab" :class="{ active: activeTab === t.key }" @click="switchTab(t.key)">{{ t.label }}</view>
        </view>
        <view class="filter-btn" :class="{ 'filter-btn-on': filterCount > 0 }" @click="openFilter">
          <text class="filter-text">筛选</text>
          <text class="filter-icon">▼</text>
          <text v-if="filterCount > 0" class="filter-dot">{{ filterCount }}</text>
        </view>
      </view>

      <view v-if="activeTab === 'progress'" class="chips">
        <view v-for="c in chips" :key="c.key" class="chip" :class="{ active: activeChip === c.key }" @click="switchChip(c.key)">{{ c.label }}</view>
      </view>

      <view class="search-row">
        <text class="search-icon">🔍</text>
        <input
          v-model="keyword"
          class="search-input"
          placeholder="搜索患者姓名或病例号"
          placeholder-class="search-ph"
          confirm-type="search"
        />
        <text v-if="keyword" class="search-clear" @click="keyword = ''">✕</text>
      </view>
    </view>

    <view class="refresh-tip">下拉即可刷新...</view>

    <!-- 加载中 -->
    <view v-if="loading && !groups.length" class="loading">加载中...</view>

    <view v-else-if="filteredGroups.length" class="card-list">
      <view class="result-tip">共 {{ filteredGroups.length }} 位患者</view>
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
            <view v-for="(t, idx) in g.followups" :key="t.id" class="tl-node" @click="goFollowupDetail(t)">
              <view v-if="idx > 0" class="tl-line" />
              <view class="tl-month">{{ t.plan_month }}月</view>
              <view class="tl-pill" :class="timelineTypeClass(displayStatus(t))">{{ displayStatus(t) }}</view>
            </view>
          </view>
          <view class="tl-hint">点击节点查看该条随访详情</view>
        </view>

        <view class="card-footer">
          <text class="foot-label">随访人:</text>
          <text class="foot-val">{{ g.doctor_name || '-' }}</text>
        </view>
      </view>
    </view>

    <!-- 空态：区分「无任何数据」与「筛选无结果」 -->
    <view v-else-if="!loading" class="empty">
      <template v-if="!groups.length">
        <text class="empty-icon">📅</text>
        <text class="empty-text">暂无随访任务</text>
      </template>
      <template v-else>
        <text class="empty-icon">🔍</text>
        <text class="empty-text">当前筛选条件下无随访记录</text>
        <view class="empty-btn" @click="clearAllFilter">清除筛选条件</view>
      </template>
    </view>

    <!-- 高级筛选面板 -->
    <view v-if="showFilter" class="filter-mask" @click="closeFilter">
      <view class="filter-panel" @click.stop>
        <view class="fp-title">筛选条件</view>

        <view class="fp-group">
          <view class="fp-label">来院方式</view>
          <view class="fp-options">
            <view class="fp-option" :class="{ active: !filterComeType }" @click="filterComeType = ''">全部</view>
            <view
              v-for="o in comeTypeOptions"
              :key="o"
              class="fp-option"
              :class="{ active: filterComeType === o }"
              @click="filterComeType = o"
            >{{ o }}</view>
          </view>
        </view>

        <view class="fp-group">
          <view class="fp-label">诊断类型</view>
          <view class="fp-options">
            <view class="fp-option" :class="{ active: !filterDiagnose }" @click="filterDiagnose = ''">全部</view>
            <view
              v-for="o in diagnoseOptions"
              :key="o"
              class="fp-option"
              :class="{ active: filterDiagnose === o }"
              @click="filterDiagnose = o"
            >{{ o }}</view>
          </view>
        </view>

        <view class="fp-actions">
          <view class="fp-btn reset" @click="resetFilter">重置</view>
          <view class="fp-btn confirm" @click="closeFilter">确定</view>
        </view>
      </view>
    </view>
  </view>
</template>
<style lang="scss" scoped>
.fu-page { min-height: 100vh; background: #f3f4f6; padding-bottom: 40rpx; }

/* 顶部紫色功能区 */
.top-header { background: linear-gradient(135deg, #5b5bd6, #6d6de0); padding: 24rpx 32rpx 24rpx; }
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

.filter-btn {
  position: relative;
  display: flex;
  align-items: center;
  gap: 6rpx;
  padding: 10rpx 20rpx;
  border-radius: 24rpx;
  background: rgba(255, 255, 255, 0.2);
}
.filter-btn-on { background: #ffffff; }
.filter-text { font-size: 26rpx; color: #ffffff; }
.filter-btn-on .filter-text { color: #5b5bd6; font-weight: 500; }
.filter-icon { font-size: 20rpx; color: #ffffff; }
.filter-btn-on .filter-icon { color: #5b5bd6; }
.filter-dot {
  position: absolute;
  top: -6rpx;
  right: -6rpx;
  min-width: 32rpx;
  height: 32rpx;
  line-height: 32rpx;
  text-align: center;
  border-radius: 16rpx;
  background: #f97316;
  color: #ffffff;
  font-size: 20rpx;
}

.chips { display: flex; gap: 16rpx; margin-bottom: 20rpx; }
.chip {
  padding: 12rpx 24rpx;
  border-radius: 28rpx;
  background: rgba(255, 255, 255, 0.2);
  font-size: 26rpx;
  color: #ffffff;
}
.chip.active { background: #ffffff; color: #5b5bd6; font-weight: 500; }

.search-row {
  display: flex;
  align-items: center;
  gap: 12rpx;
  padding: 0 24rpx;
  height: 72rpx;
  border-radius: 36rpx;
  background: #ffffff;
}
.search-icon { font-size: 26rpx; }
.search-input { flex: 1; font-size: 27rpx; color: #1f2937; }
.search-ph { color: #9ca3af; }
.search-clear { font-size: 26rpx; color: #9ca3af; padding: 0 8rpx; }

/* 下拉提示 */
.refresh-tip { text-align: center; padding: 28rpx 0 8rpx; font-size: 26rpx; color: #9ca3af; }
.result-tip { padding: 4rpx 8rpx 12rpx; font-size: 24rpx; color: #9ca3af; }
.loading { text-align: center; padding-top: 160rpx; font-size: 28rpx; color: #9ca3af; }

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
.tl-node:active .tl-pill { transform: scale(0.95); }
.tl-pill { transition: transform 0.1s; }
.tl-hint { text-align: center; font-size: 22rpx; color: #9ca3af; margin-top: 12rpx; }

/* 卡片底部 */
.card-footer { display: flex; align-items: center; gap: 10rpx; margin-top: 20rpx; padding-top: 16rpx; }
.foot-label { font-size: 26rpx; color: #9ca3af; }
.foot-val { font-size: 26rpx; color: #1f2937; }

/* 空 */
.empty { display: flex; flex-direction: column; align-items: center; padding-top: 120rpx; }
.empty-icon { font-size: 80rpx; }
.empty-text { margin-top: 20rpx; font-size: 26rpx; color: #9ca3af; }
.empty-btn {
  margin-top: 28rpx;
  padding: 16rpx 40rpx;
  border-radius: 32rpx;
  background: #5b5bd6;
  color: #ffffff;
  font-size: 26rpx;
}

/* 筛选面板 */
.filter-mask {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.45);
  z-index: 100;
  display: flex;
  align-items: flex-end;
}
.filter-panel {
  width: 100%;
  background: #ffffff;
  border-radius: 24rpx 24rpx 0 0;
  padding: 32rpx 32rpx 40rpx;
}
.fp-title { font-size: 30rpx; font-weight: 600; color: #1f2937; margin-bottom: 24rpx; }
.fp-group { margin-bottom: 28rpx; }
.fp-label { font-size: 26rpx; color: #6b7280; margin-bottom: 16rpx; }
.fp-options { display: flex; flex-wrap: wrap; gap: 16rpx; }
.fp-option {
  padding: 14rpx 28rpx;
  border-radius: 28rpx;
  background: #f3f4f6;
  font-size: 26rpx;
  color: #4b5563;
}
.fp-option.active { background: #5b5bd6; color: #ffffff; font-weight: 500; }
.fp-actions { display: flex; gap: 20rpx; margin-top: 12rpx; }
.fp-btn {
  flex: 1;
  height: 84rpx;
  line-height: 84rpx;
  text-align: center;
  border-radius: 16rpx;
  font-size: 28rpx;
}
.fp-btn.reset { background: #f3f4f6; color: #4b5563; }
.fp-btn.confirm { background: #5b5bd6; color: #ffffff; font-weight: 500; }
</style>
