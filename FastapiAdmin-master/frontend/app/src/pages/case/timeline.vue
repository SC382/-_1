<!-- 时间轴：可视化救治时间线 + 关键指标（S2FMC/FMC2ECG/D2W/FMC2W/D2N） -->
<script setup lang="ts">
import { ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import DoctorAPI, { type TimelineMetric, type TimelineNode } from '@/api/module_cpx/doctor'

definePage({
  name: 'case-timeline',
  style: { navigationBarTitleText: '救治时间轴' },
})

const loading = ref(false)
const nodes = ref<TimelineNode[]>([])
const metrics = ref<TimelineMetric[]>([])
const caseInfo = ref<{ case_no?: string; patient_name?: string }>({})

const metricColor = (s: string) => {
  if (s === 'pass') return '#10b981'
  if (s === 'fail') return '#ef4444'
  return '#9ca3af'
}
const metricText = (s: string) => {
  if (s === 'pass') return '达标'
  if (s === 'fail') return '不达标'
  return '未采集'
}

onLoad(async (query) => {
  const id = Number(query?.id || 0)
  if (!id) return
  loading.value = true
  try {
    const res = await DoctorAPI.timeline(id)
    nodes.value = res.nodes
    metrics.value = res.metrics
    caseInfo.value = { case_no: res.case_no, patient_name: res.patient_name }
  }
  finally {
    loading.value = false
  }
})
</script>

<template>
  <view class="timeline-page">
    <view v-if="loading" class="loading">加载中...</view>
    <template v-else>
      <!-- 关键指标 -->
      <view class="metric-grid">
        <view v-for="m in metrics" :key="m.key" class="metric-card">
          <text class="metric-key">{{ m.key }}</text>
          <text class="metric-val" :style="{ color: metricColor(m.status) }">
            {{ m.minutes != null ? `${m.minutes} min` : '—' }}
          </text>
          <text class="metric-status" :style="{ color: metricColor(m.status) }">{{ metricText(m.status) }}</text>
        </view>
      </view>

      <!-- 时间线 -->
      <view class="timeline">
        <view v-for="(n, i) in nodes" :key="n.code" class="tl-node">
          <view class="tl-left">
            <view class="tl-dot" :class="{ filled: n.value }" />
            <view v-if="i < nodes.length - 1" class="tl-line" />
          </view>
          <view class="tl-content">
            <text class="tl-name">{{ n.name }}</text>
            <text class="tl-time" :class="{ empty: !n.value }">{{ n.value || '未采集' }}</text>
          </view>
        </view>
      </view>
    </template>
  </view>
</template>

<style lang="scss" scoped>
.timeline-page {
  min-height: 100vh;
  background: #f3f4f6;
  padding: 24rpx 32rpx 60rpx;
}
.loading { text-align: center; padding-top: 200rpx; color: #9ca3af; }

.metric-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20rpx;
  margin-bottom: 24rpx;
}
.metric-card {
  display: flex;
  flex-direction: column;
  padding: 28rpx;
  border-radius: 20rpx;
  background: #ffffff;
}
.metric-key { font-size: 24rpx; color: #9ca3af; }
.metric-val { margin-top: 10rpx; font-size: 40rpx; font-weight: 700; }
.metric-status { margin-top: 6rpx; font-size: 22rpx; }

.timeline { padding: 32rpx; border-radius: 24rpx; background: #ffffff; }
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
.tl-dot.filled { background: #2563eb; }
.tl-line {
  flex: 1;
  width: 4rpx;
  background: #e5e7eb;
  margin: 8rpx 0;
  min-height: 40rpx;
}
.tl-content {
  flex: 1;
  padding-bottom: 40rpx;
}
.tl-name { font-size: 28rpx; color: #4b5563; }
.tl-time { display: block; margin-top: 8rpx; font-size: 30rpx; font-weight: 600; color: #1f2937; }
.tl-time.empty { color: #c0c4cc; font-weight: 400; }
</style>
