<!-- 今日报告：今日病例统计 + 今日病例明细 -->
<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import DoctorAPI, { type CaseRecordItem } from '@/api/module_cpx/doctor'

definePage({
  name: 'daily-report',
  style: { navigationBarTitleText: '今日报告' },
})

const loading = ref(false)
const list = ref<CaseRecordItem[]>([])
const today = new Date()
const dateStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`

// 今日统计（从今日病例本地分组）
const stats = computed(() => {
  const s = { total: list.value.length, draft: 0, pending: 0, approved: 0, rejected: 0 }
  for (const c of list.value) {
    if (c.status === 'draft') s.draft++
    else if (c.status === 'submitted') s.pending++
    else if (c.status === 'approved') s.approved++
    else if (c.status === 'rejected') s.rejected++
  }
  return s
})

const STATUS_MAP: Record<string, { label: string; color: string }> = {
  draft: { label: '草稿', color: '#9ca3af' },
  submitted: { label: '待审核', color: '#f59e0b' },
  approved: { label: '已通过', color: '#10b981' },
  rejected: { label: '已驳回', color: '#ef4444' },
}

const statCards = computed(() => [
  { status: '', label: '今日新增', value: stats.value.total, color: '#2563eb' },
  { status: 'draft', label: '草稿', value: stats.value.draft, color: '#9ca3af' },
  { status: 'submitted', label: '待审核', value: stats.value.pending, color: '#f59e0b' },
  { status: 'approved', label: '已通过', value: stats.value.approved, color: '#10b981' },
  { status: 'rejected', label: '已驳回', value: stats.value.rejected, color: '#ef4444' },
])

async function fetchReport() {
  loading.value = true
  try {
    const res = await DoctorAPI.myCases({
      page_no: 1,
      page_size: 100,
      status: '',
      keyword: '',
      start_time: dateStr,
      end_time: dateStr,
    })
    list.value = res.items
  }
  catch {
    // http 层已 toast
  }
  finally {
    loading.value = false
  }
}

onShow(fetchReport)

// 点击统计卡 → 跳转数据直报页，按今日 + 对应状态筛选（storage + URL 双保险）
function goFilter(status: string) {
  uni.setStorageSync('workFilter', { range: 'today', status: status || '' })
  const url = status
    ? `/pages/work/index?range=today&status=${status}`
    : '/pages/work/index?range=today'
  uni.navigateTo({ url })
}

function goWork() {
  uni.setStorageSync('workFilter', { range: 'today', status: '' })
  uni.navigateTo({ url: '/pages/work/index?range=today' })
}
</script>

<template>
  <view class="report-page">
    <!-- 顶部摘要 -->
    <view class="report-header">
      <text class="report-date">{{ dateStr }}</text>
      <text class="report-sub">今日病例填报报告</text>
    </view>

    <!-- 统计卡（点击跳数据直报页按对应状态筛选） -->
    <view class="stat-grid">
      <view
        v-for="c in statCards"
        :key="c.label"
        class="stat-card"
        @click="goFilter(c.status)"
      >
        <text class="stat-num" :style="{ color: c.color }">{{ c.value }}</text>
        <text class="stat-label">{{ c.label }}</text>
      </view>
    </view>

    <!-- 今日病例明细 -->
    <view class="list-block">
      <view class="list-header">
        <text class="list-title">今日病例明细（{{ stats.total }}）</text>
        <text class="list-more" @click="goWork">全部 ></text>
      </view>

      <view v-if="loading" class="empty">加载中…</view>
      <view v-else-if="list.length === 0" class="empty">
        <text class="empty-main">今日暂无病例</text>
        <text class="empty-sub">医生尚未填报或审核完成</text>
      </view>
      <view v-else class="case-list">
        <view
          v-for="item in list"
          :key="item.id"
          class="case-item"
          @click="goWork"
        >
          <view class="case-left">
            <text class="case-name">{{ item.patient_name || '未命名' }}</text>
            <text class="case-meta">
              {{ item.diagnose_type || '待诊断' }}
              <text v-if="item.gender"> · {{ item.gender }}</text>
              <text v-if="item.age"> · {{ item.age }}岁</text>
            </text>
          </view>
          <view class="case-right">
            <text
              class="case-status"
              :style="{ color: STATUS_MAP[item.status || '']?.color || '#6b7280' }"
            >
              {{ STATUS_MAP[item.status || '']?.label || item.status }}
            </text>
            <text class="case-time">{{ (item.create_time || '').slice(11, 16) }}</text>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<style lang="scss" scoped>
.report-page {
  min-height: 100vh;
  background: #f3f4f6;
  padding-bottom: 40rpx;
}
.report-header {
  padding: 36rpx 32rpx 28rpx;
  background: linear-gradient(135deg, #0ea5e9 0%, #2563eb 100%);
}
.report-date {
  display: block;
  font-size: 40rpx;
  font-weight: 700;
  color: #ffffff;
  letter-spacing: 2rpx;
}
.report-sub {
  display: block;
  margin-top: 8rpx;
  font-size: 24rpx;
  color: rgba(255, 255, 255, 0.8);
}
.stat-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 12rpx;
  margin: 24rpx 24rpx 0;
}
.stat-card {
  background: #ffffff;
  border-radius: 16rpx;
  padding: 20rpx 4rpx;
  display: flex;
  flex-direction: column;
  align-items: center;
  box-shadow: 0 4rpx 12rpx rgba(15, 23, 42, 0.05);
}
.stat-num {
  font-size: 34rpx;
  font-weight: 700;
  line-height: 1;
}
.stat-label {
  margin-top: 10rpx;
  font-size: 22rpx;
  color: #6b7280;
}
.list-block {
  margin: 28rpx 32rpx 0;
}
.list-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16rpx;
}
.list-title {
  font-size: 30rpx;
  font-weight: 600;
  color: #1f2937;
}
.list-more {
  font-size: 24rpx;
  color: #2563eb;
}
.empty {
  padding: 80rpx 0;
  text-align: center;
}
.empty-main {
  display: block;
  font-size: 28rpx;
  color: #9ca3af;
}
.empty-sub {
  display: block;
  margin-top: 10rpx;
  font-size: 22rpx;
  color: #c0c4cc;
}
.case-list {
  background: #ffffff;
  border-radius: 20rpx;
  overflow: hidden;
  box-shadow: 0 4rpx 12rpx rgba(15, 23, 42, 0.05);
}
.case-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 24rpx 28rpx;
  border-bottom: 2rpx solid #f3f4f6;
}
.case-item:last-child {
  border-bottom: none;
}
.case-left {
  flex: 1;
  min-width: 0;
}
.case-name {
  display: block;
  font-size: 28rpx;
  font-weight: 600;
  color: #1f2937;
}
.case-meta {
  display: block;
  margin-top: 6rpx;
  font-size: 22rpx;
  color: #9ca3af;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.case-right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  margin-left: 16rpx;
}
.case-status {
  font-size: 24rpx;
  font-weight: 600;
}
.case-time {
  margin-top: 6rpx;
  font-size: 20rpx;
  color: #c0c4cc;
}
</style>
