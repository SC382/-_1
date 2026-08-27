<!-- 数据分析（详细版）：时间筛选 + 统计卡片 + 趋势/病因/状态 + 随访 + 转诊 + 月度质控指标 -->
<script setup lang="ts">
import { ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import DoctorAPI, { type StatsOverview } from '@/api/module_cpx/doctor'

definePage({
  name: 'analysis',
  style: { navigationBarTitleText: '数据分析' },
})

const loading = ref(false)
const months = ref(6)
const data = ref<StatsOverview | null>(null)

const RANGE_TABS = [
  { label: '近3月', value: 3 },
  { label: '近6月', value: 6 },
  { label: '近1年', value: 12 },
]

const statusLabel: Record<string, string> = {
  draft: '填报中',
  submitted: '待审核',
  approved: '待归档',
  rejected: '已归档',
}

async function fetchData() {
  loading.value = true
  try {
    data.value = await DoctorAPI.statsOverview(months.value)
  }
  finally {
    loading.value = false
  }
}

function switchRange(m: number) {
  months.value = m
  fetchData()
}

function recentTrend() {
  return (data.value?.trend || []).slice(-7)
}
function maxTrend() {
  let m = 1
  ;(data.value?.trend || []).forEach((d) => { if (d.count > m) m = d.count })
  return m
}

onShow(fetchData)
</script>

<template>
  <view class="ana-page">
    <view v-if="loading" class="loading">加载中...</view>
    <template v-else-if="data">
      <!-- 时间筛选 -->
      <view class="range-bar">
        <view
          v-for="t in RANGE_TABS"
          :key="t.value"
          class="range-item"
          :class="{ active: months === t.value }"
          @click="switchRange(t.value)"
        >{{ t.label }}</view>
      </view>

      <!-- 统计卡片 -->
      <view class="stat-grid">
        <view class="stat-card"><text class="stat-num">{{ data.overview.total }}</text><text class="stat-label">累计填报</text></view>
        <view class="stat-card"><text class="stat-num">{{ data.overview.today_new }}</text><text class="stat-label">今日新增</text></view>
        <view class="stat-card"><text class="stat-num">{{ data.overview.yesterday_new }}</text><text class="stat-label">昨日新增</text></view>
        <view class="stat-card"><text class="stat-num">{{ data.overview.week_new }}</text><text class="stat-label">本周填报</text></view>
        <view class="stat-card"><text class="stat-num">{{ data.overview.month_new }}</text><text class="stat-label">本月填报</text></view>
      </view>

      <!-- 近7天趋势 -->
      <view class="card">
        <text class="card-title">高危胸痛填报趋势（近7天）</text>
        <view class="bar-chart">
          <view v-for="d in recentTrend()" :key="d.date" class="bar-col">
            <view class="bar-wrap">
              <view class="bar" :style="{ height: `${Math.max((d.count / maxTrend()) * 120, 8)}rpx` }" />
            </view>
            <text class="bar-val">{{ d.count }}</text>
            <text class="bar-date">{{ d.date.slice(5) }}</text>
          </view>
        </view>
      </view>

      <!-- 病因分布 -->
      <view class="card">
        <text class="card-title">病因分布</text>
        <view v-if="data.diagnose_dist.length">
          <view v-for="d in data.diagnose_dist" :key="d.type" class="dist-row">
            <text class="dist-type">{{ d.type }}</text>
            <view class="dist-track">
              <view class="dist-fill" :style="{ width: `${Math.min((d.count / Math.max(...data.diagnose_dist.map(x => x.count), 1)) * 100, 100)}%` }" />
            </view>
            <text class="dist-count">{{ d.count }}</text>
          </view>
        </view>
        <text v-else class="empty">暂无数据</text>
      </view>

      <!-- 状态分布 -->
      <view class="card">
        <text class="card-title">病例状态分布</text>
        <view class="status-grid">
          <view v-for="(count, key) in data.status_dist" :key="key" class="status-item">
            <text class="status-num">{{ count }}</text>
            <text class="status-name">{{ statusLabel[key] || key }}</text>
          </view>
        </view>
      </view>

      <!-- 随访统计 -->
      <view class="card">
        <text class="card-title">ACS 随访统计（1/3/6/12 月随访率）</text>
        <view class="fu-grid">
          <view v-for="f in data.followup_stats" :key="f.month" class="fu-item">
            <text class="fu-month">{{ f.month }}</text>
            <text class="fu-rate" :style="{ color: (f.rate ?? 0) >= 80 ? '#10b981' : '#f59e0b' }">{{ f.rate != null ? `${f.rate}%` : '—' }}</text>
            <text class="fu-meta">{{ f.done }}/{{ f.total }} 例</text>
          </view>
        </view>
      </view>

      <!-- 转诊统计 -->
      <view class="card">
        <text class="card-title">网络医院转诊（{{ data.transfer.total }} 例）</text>
        <view v-if="data.transfer.list.length">
          <view v-for="(t, i) in data.transfer.list.slice(0, 8)" :key="i" class="transfer-row">
            <text class="transfer-case">{{ t.case_no }}</text>
            <text class="transfer-name">{{ t.patient_name }}</text>
            <text class="transfer-diag">{{ t.diagnose_type || '-' }}</text>
            <text class="transfer-status">{{ statusLabel[t.status || ''] || t.status }}</text>
          </view>
        </view>
        <text v-else class="empty">暂无转诊记录</text>
      </view>

      <!-- 月度质控指标 -->
      <view class="card">
        <text class="card-title">月度质控指标达标率</text>
        <view class="mm-head">
          <text class="mm-cell">月份</text>
          <text class="mm-cell">病例数</text>
          <text class="mm-cell">D2W 达标率</text>
          <text class="mm-cell">FMC2ECG</text>
        </view>
        <view v-for="m in data.metrics_monthly" :key="m.month" class="mm-row">
          <text class="mm-cell">{{ m.month }}</text>
          <text class="mm-cell">{{ m.cases }}</text>
          <text class="mm-cell" :style="{ color: (m.D2W ?? 0) >= 80 ? '#10b981' : (m.D2W == null ? '#9ca3af' : '#ef4444') }">{{ m.D2W != null ? `${m.D2W}%` : '—' }}</text>
          <text class="mm-cell" :style="{ color: (m.FMC2ECG ?? 0) >= 80 ? '#10b981' : (m.FMC2ECG == null ? '#9ca3af' : '#ef4444') }">{{ m.FMC2ECG != null ? `${m.FMC2ECG}%` : '—' }}</text>
        </view>
      </view>
    </template>
  </view>
</template>

<style lang="scss" scoped>
.ana-page { min-height: 100vh; background: #f3f4f6; padding: 24rpx 32rpx 60rpx; }
.loading { text-align: center; padding-top: 200rpx; color: #9ca3af; }

.range-bar { display: flex; gap: 16rpx; margin-bottom: 24rpx; }
.range-item {
  flex: 1;
  text-align: center;
  padding: 14rpx 0;
  border-radius: 28rpx;
  background: #ffffff;
  font-size: 26rpx;
  color: #6b7280;
}
.range-item.active { background: #2563eb; color: #ffffff; }

.stat-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16rpx; margin-bottom: 24rpx; }
.stat-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 26rpx 12rpx;
  border-radius: 20rpx;
  background: #ffffff;
}
.stat-num { font-size: 42rpx; font-weight: 700; color: #2563eb; }
.stat-label { margin-top: 6rpx; font-size: 22rpx; color: #9ca3af; }

.card { margin-bottom: 24rpx; padding: 32rpx; border-radius: 24rpx; background: #ffffff; }
.card-title { display: block; font-size: 30rpx; font-weight: 600; color: #1f2937; margin-bottom: 24rpx; }

.bar-chart { display: flex; align-items: flex-end; justify-content: space-between; gap: 12rpx; }
.bar-col { flex: 1; display: flex; flex-direction: column; align-items: center; }
.bar-wrap { display: flex; align-items: flex-end; height: 140rpx; }
.bar { width: 32rpx; border-radius: 8rpx 8rpx 0 0; background: linear-gradient(180deg, #38bdf8, #2563eb); }
.bar-val { margin-top: 8rpx; font-size: 22rpx; color: #4b5563; }
.bar-date { margin-top: 4rpx; font-size: 20rpx; color: #9ca3af; }

.dist-row { display: flex; align-items: center; gap: 16rpx; margin-bottom: 20rpx; }
.dist-type { width: 160rpx; font-size: 26rpx; color: #4b5563; }
.dist-track { flex: 1; height: 24rpx; border-radius: 12rpx; background: #f3f4f6; overflow: hidden; }
.dist-fill { height: 100%; border-radius: 12rpx; background: linear-gradient(90deg, #f59e0b, #ef4444); }
.dist-count { width: 60rpx; text-align: right; font-size: 26rpx; color: #1f2937; font-weight: 600; }

.status-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16rpx; }
.status-item { display: flex; flex-direction: column; align-items: center; padding: 24rpx; border-radius: 16rpx; background: #f9fafb; }
.status-num { font-size: 36rpx; font-weight: 700; color: #1f2937; }
.status-name { margin-top: 6rpx; font-size: 22rpx; color: #9ca3af; }

.fu-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16rpx; }
.fu-item { display: flex; flex-direction: column; align-items: center; padding: 24rpx; border-radius: 16rpx; background: #f9fafb; }
.fu-month { font-size: 24rpx; color: #6b7280; }
.fu-rate { margin-top: 8rpx; font-size: 34rpx; font-weight: 700; }
.fu-meta { margin-top: 4rpx; font-size: 20rpx; color: #9ca3af; }

.transfer-row { display: flex; align-items: center; gap: 12rpx; padding: 16rpx 0; border-bottom: 2rpx solid #f3f4f6; }
.transfer-case { width: 200rpx; font-size: 24rpx; color: #2563eb; }
.transfer-name { flex: 1; font-size: 26rpx; color: #1f2937; }
.transfer-diag { width: 100rpx; font-size: 22rpx; color: #9ca3af; }
.transfer-status { width: 100rpx; text-align: right; font-size: 22rpx; color: #f59e0b; }

.mm-head, .mm-row { display: flex; align-items: center; padding: 12rpx 0; border-bottom: 2rpx solid #f3f4f6; }
.mm-head { background: #f9fafb; border-radius: 12rpx 12rpx 0 0; }
.mm-cell { flex: 1; text-align: center; font-size: 24rpx; color: #4b5563; }
.mm-head .mm-cell { font-weight: 600; color: #1f2937; }

.empty { display: block; text-align: center; padding: 30rpx 0; color: #c0c4cc; font-size: 26rpx; }
</style>
