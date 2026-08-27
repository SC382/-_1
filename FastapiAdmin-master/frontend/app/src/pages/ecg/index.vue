<!-- 远程心电：上传/会诊记录列表（发起+接收合并） + 选病例发起 -->
<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { onPullDownRefresh, onShow } from '@dcloudio/uni-app'
import DoctorAPI, { type CaseRecordItem, type EcgConsultItem } from '@/api/module_cpx/doctor'

definePage({
  name: 'ecg',
  style: { navigationBarTitleText: '远程心电' },
})

const loading = ref(false)
const list = ref<EcgConsultItem[]>([])

type TabKey = 'all' | 'initiator' | 'receiver'
const activeTab = ref<TabKey>('all')
const TABS: { key: TabKey; label: string }[] = [
  { key: 'all', label: '全部' },
  { key: 'initiator', label: '我发起的' },
  { key: 'receiver', label: '我接收的' },
]

const STATUS_META: Record<string, { label: string; color: string; bg: string }> = {
  uploaded: { label: 'AI 已诊断', color: '#2563eb', bg: '#dbeafe' },
  consult_sent: { label: '已发送会诊', color: '#f59e0b', bg: '#fef3c7' },
  received: { label: '已接收', color: '#8b5cf6', bg: '#ede9fe' },
  closed: { label: '已完成', color: '#10b981', bg: '#d1fae5' },
}
function statusMeta(s?: string | null) {
  return STATUS_META[s || ''] || { label: s || '-', color: '#9ca3af', bg: '#f3f4f6' }
}

async function fetchList() {
  loading.value = true
  try {
    const r = await DoctorAPI.ecgList()
    list.value = r.items || []
  }
  finally {
    loading.value = false
  }
}

const filteredList = computed(() => {
  if (activeTab.value === 'initiator') return list.value.filter((i) => i.is_initiator)
  if (activeTab.value === 'receiver') return list.value.filter((i) => !i.is_initiator)
  return list.value
})

function goDetail(id: number) {
  uni.navigateTo({ url: `/pages/ecg/detail?id=${id}` })
}

// 选病例 popup
const showCasePicker = ref(false)
const caseList = ref<CaseRecordItem[]>([])
const caseLoading = ref(false)
const caseQuery = reactive({ keyword: '' })
async function openCasePicker() {
  showCasePicker.value = true
  caseQuery.keyword = ''
  caseList.value = []
  caseLoading.value = true
  try {
    const r = await DoctorAPI.myCases({ page_no: 1, page_size: 50, keyword: undefined })
    caseList.value = r.items || []
  }
  finally {
    caseLoading.value = false
  }
}
async function searchCases() {
  caseLoading.value = true
  try {
    const r = await DoctorAPI.myCases({ page_no: 1, page_size: 50, keyword: caseQuery.keyword || undefined })
    caseList.value = r.items || []
  }
  finally {
    caseLoading.value = false
  }
}
function pickCase(c: CaseRecordItem) {
  showCasePicker.value = false
  uni.navigateTo({ url: `/pages/ecg/upload?case_id=${c.id}` })
}

onShow(fetchList)
onPullDownRefresh(() => {
  fetchList().finally(() => uni.stopPullDownRefresh())
})
</script>

<template>
  <view class="ecg-page">
    <!-- Tab -->
    <view class="tab-bar">
      <view
        v-for="t in TABS"
        :key="t.key"
        class="tab-item"
        :class="{ active: activeTab === t.key }"
        @click="activeTab = t.key"
      >
        {{ t.label }}
      </view>
    </view>

    <!-- 列表 -->
    <view v-if="loading && !list.length" class="loading">加载中...</view>
    <view v-else-if="filteredList.length" class="ecg-list">
      <view
        v-for="c in filteredList"
        :key="c.id"
        class="ecg-card"
        @click="goDetail(c.id)"
      >
        <view class="card-head">
          <text class="card-patient">{{ c.patient_name || '-' }}</text>
          <text class="card-status" :style="{ color: statusMeta(c.status).color, background: statusMeta(c.status).bg }">
            {{ statusMeta(c.status).label }}
          </text>
        </view>
        <text class="card-case">病例：{{ c.case_no || '未关联' }}</text>
        <text v-if="c.ai_summary" class="card-summary">{{ c.ai_summary }}</text>
        <view class="card-foot">
          <text class="card-tag" v-if="!c.is_initiator">来自：{{ c.target_hospital_name || '外院' }}</text>
          <text class="card-tag" v-else>已发送会诊</text>
          <text class="card-time">{{ (c.create_time || '').slice(5, 16) }}</text>
        </view>
        <view v-if="c.feedback" class="card-feedback">
          <text class="fb-label">反馈：</text>
          <text class="fb-text">{{ c.feedback }}</text>
        </view>
      </view>
    </view>
    <view v-else class="empty">
      <text class="empty-icon">📋</text>
      <text class="empty-text">暂无记录，点击右下角"+ 新建"</text>
    </view>

    <!-- 浮动 + 新建 -->
    <view class="fab" @click="openCasePicker">
      <text class="fab-icon">+</text>
      <text class="fab-label">新建</text>
    </view>

    <!-- 选病例弹层 -->
    <view v-if="showCasePicker" class="picker-mask" @click="showCasePicker = false">
      <view class="picker-panel" @click.stop>
        <view class="picker-head">
          <text class="picker-title">选择病例</text>
          <text class="picker-close" @click="showCasePicker = false">×</text>
        </view>
        <view class="picker-search">
          <input
            v-model="caseQuery.keyword"
            class="picker-input"
            placeholder="患者姓名 / 病例编号"
            confirm-type="search"
            @confirm="searchCases"
          />
          <view class="picker-search-btn" @click="searchCases">搜索</view>
        </view>
        <scroll-view scroll-y class="picker-scroll">
          <view v-if="caseLoading" class="picker-loading">加载中...</view>
          <view v-else-if="!caseList.length" class="empty">暂无可用病例</view>
          <view v-else>
            <view
              v-for="c in caseList"
              :key="c.id"
              class="picker-item"
              @click="pickCase(c)"
            >
              <text class="picker-item-name">{{ c.patient_name || '-' }}</text>
              <text class="picker-item-case">{{ c.case_no }}</text>
            </view>
          </view>
        </scroll-view>
      </view>
    </view>
  </view>
</template>

<style lang="scss" scoped>
.ecg-page { min-height: 100vh; background: #f3f4f6; padding-bottom: 200rpx; }
.loading { text-align: center; padding: 80rpx 0; color: #9ca3af; }
.empty { display: flex; flex-direction: column; align-items: center; padding: 200rpx 0 0; color: #9ca3af; }
.empty-icon { font-size: 80rpx; }
.empty-text { margin-top: 20rpx; font-size: 26rpx; }

.tab-bar {
  display: flex;
  background: #ffffff;
  padding: 20rpx 24rpx;
  border-bottom: 2rpx solid #f3f4f6;
  gap: 12rpx;
}
.tab-item {
  flex: 1;
  text-align: center;
  padding: 16rpx 0;
  border-radius: 16rpx;
  font-size: 26rpx;
  color: #6b7280;
  background: #f3f4f6;
}
.tab-item.active { background: #2563eb; color: #ffffff; font-weight: 600; }

.ecg-list { display: flex; flex-direction: column; gap: 20rpx; padding: 24rpx 32rpx; }
.ecg-card {
  display: flex;
  flex-direction: column;
  gap: 10rpx;
  padding: 28rpx;
  border-radius: 20rpx;
  background: #ffffff;
  box-shadow: 0 6rpx 20rpx rgba(15, 23, 42, 0.05);
}
.card-head { display: flex; align-items: center; justify-content: space-between; }
.card-patient { font-size: 30rpx; font-weight: 600; color: #1f2937; }
.card-status { font-size: 22rpx; padding: 4rpx 16rpx; border-radius: 12rpx; font-weight: 500; }
.card-case { font-size: 24rpx; color: #6b7280; }
.card-summary { font-size: 26rpx; color: #374151; line-height: 1.5; }
.card-foot { display: flex; align-items: center; justify-content: space-between; }
.card-tag { font-size: 22rpx; color: #9ca3af; }
.card-time { font-size: 22rpx; color: #c0c4cc; }
.card-feedback {
  margin-top: 8rpx;
  padding: 16rpx;
  border-radius: 12rpx;
  background: #f0fdf4;
}
.fb-label { font-size: 22rpx; color: #059669; font-weight: 600; }
.fb-text { font-size: 24rpx; color: #064e3b; }

.fab {
  position: fixed;
  right: 40rpx;
  bottom: 80rpx;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 130rpx;
  height: 130rpx;
  border-radius: 50%;
  background: linear-gradient(135deg, #2563eb, #38bdf8);
  color: #ffffff;
  box-shadow: 0 10rpx 30rpx rgba(37, 99, 235, 0.4);
}
.fab-icon { font-size: 50rpx; line-height: 1; }
.fab-label { font-size: 22rpx; margin-top: -4rpx; }

/* 选病例弹层 */
.picker-mask {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 1000;
  display: flex;
  align-items: flex-end;
}
.picker-panel {
  width: 100%;
  max-height: 80vh;
  background: #ffffff;
  border-radius: 24rpx 24rpx 0 0;
  display: flex;
  flex-direction: column;
}
.picker-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 24rpx 32rpx;
  border-bottom: 2rpx solid #f3f4f6;
}
.picker-title { font-size: 32rpx; font-weight: 600; color: #1f2937; }
.picker-close { font-size: 48rpx; color: #9ca3af; line-height: 1; padding: 0 16rpx; }
.picker-search { display: flex; gap: 12rpx; padding: 20rpx 32rpx; }
.picker-input {
  flex: 1;
  height: 72rpx;
  padding: 0 24rpx;
  border-radius: 16rpx;
  background: #f3f4f6;
  font-size: 26rpx;
}
.picker-search-btn {
  padding: 0 28rpx;
  height: 72rpx;
  line-height: 72rpx;
  border-radius: 16rpx;
  background: #2563eb;
  color: #ffffff;
  font-size: 26rpx;
}
.picker-scroll { max-height: 60vh; }
.picker-loading { padding: 80rpx 0; text-align: center; color: #9ca3af; }
.picker-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 28rpx 32rpx;
  border-bottom: 2rpx solid #f3f4f6;
}
.picker-item-name { font-size: 30rpx; color: #1f2937; }
.picker-item-case { font-size: 24rpx; color: #9ca3af; }
</style>
