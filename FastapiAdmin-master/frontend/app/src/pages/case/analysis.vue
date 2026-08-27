<!-- 单病例分析：对照质控标准逐项校验，蓝达标/红不达标/灰不适用 -->
<script setup lang="ts">
import { ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import DoctorAPI, { type AnalysisItem } from '@/api/module_cpx/doctor'

definePage({
  name: 'case-analysis',
  style: { navigationBarTitleText: '单病例分析' },
})

const loading = ref(false)
const items = ref<AnalysisItem[]>([])
const missing = ref<{ field_code: string; field_name: string; tab: string }[]>([])
const caseInfo = ref<{ case_no?: string; patient_name?: string }>({})

const statusColor = (s: string) => {
  if (s === 'pass') return '#2563eb'
  if (s === 'fail') return '#ef4444'
  if (s === 'info') return '#10b981'
  return '#9ca3af'
}
const statusLabel = (s: string) => {
  if (s === 'pass') return '达标'
  if (s === 'fail') return '不达标'
  if (s === 'info') return '已记录'
  return '未采集/不适用'
}

onLoad(async (query) => {
  const id = Number(query?.id || 0)
  if (!id) return
  loading.value = true
  try {
    const res = await DoctorAPI.analysis(id)
    items.value = res.items
    missing.value = res.missing_required
    caseInfo.value = { case_no: res.case_no, patient_name: res.patient_name }
  }
  finally {
    loading.value = false
  }
})
</script>

<template>
  <view class="analysis-page">
    <view v-if="loading" class="loading">加载中...</view>
    <template v-else>
      <!-- 指标 -->
      <view class="card">
        <text class="card-title">质控指标</text>
        <view v-for="m in items" :key="m.key" class="metric-item" :style="{ borderLeftColor: statusColor(m.status) }">
          <view class="metric-head">
            <text class="metric-name">{{ m.name }}</text>
            <text class="metric-status" :style="{ color: statusColor(m.status) }">{{ statusLabel(m.status) }}</text>
          </view>
          <text class="metric-desc">{{ m.desc }}</text>
          <view class="metric-foot">
            <text class="metric-val">实际值：{{ m.minutes != null ? `${m.minutes} min` : '未采集' }}</text>
            <text v-if="m.limit != null" class="metric-limit">标准：≤{{ m.limit }} min</text>
          </view>
        </view>
      </view>

      <!-- 缺失必填 -->
      <view v-if="missing.length" class="card">
        <text class="card-title">缺失必填字段（请补录）</text>
        <view v-for="m in missing" :key="m.field_code" class="missing-item">
          <text class="missing-name">· {{ m.field_name }}</text>
        </view>
      </view>
    </template>
  </view>
</template>

<style lang="scss" scoped>
.analysis-page {
  min-height: 100vh;
  background: #f3f4f6;
  padding: 24rpx 32rpx 60rpx;
}
.loading { text-align: center; padding-top: 200rpx; color: #9ca3af; }

.card {
  margin-bottom: 24rpx;
  padding: 32rpx;
  border-radius: 24rpx;
  background: #ffffff;
}
.card-title { display: block; font-size: 30rpx; font-weight: 600; color: #1f2937; margin-bottom: 20rpx; }

.metric-item {
  padding: 20rpx;
  border-left: 8rpx solid #e5e7eb;
  border-radius: 12rpx;
  background: #f9fafb;
  margin-bottom: 16rpx;
}
.metric-head { display: flex; align-items: center; justify-content: space-between; }
.metric-name { font-size: 28rpx; font-weight: 600; color: #1f2937; }
.metric-status { font-size: 26rpx; font-weight: 600; }
.metric-desc { display: block; margin-top: 8rpx; font-size: 24rpx; color: #9ca3af; }
.metric-foot { display: flex; align-items: center; justify-content: space-between; margin-top: 12rpx; }
.metric-val { font-size: 26rpx; color: #4b5563; }
.metric-limit { font-size: 24rpx; color: #9ca3af; }

.missing-item { padding: 10rpx 0; }
.missing-name { font-size: 26rpx; color: #dc2626; }
</style>
