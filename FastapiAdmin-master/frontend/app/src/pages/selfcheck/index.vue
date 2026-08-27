<!-- AI 模拟再认证自评：选区间 → 指标达标率 → 评分与建议 -->
<script setup lang="ts">
import { ref } from 'vue'
import DoctorAPI from '@/api/module_cpx/doctor'

definePage({
  name: 'selfcheck',
  style: { navigationBarTitleText: 'AI模拟再认证自评' },
})

const loading = ref(false)
const range = ref<'3m' | '6m' | '1y' | 'custom'>('6m')
const dateRange = ref<[string, string]>(['', ''])
const result = ref<{ case_count: number; score: number; items: any[]; suggestions: string[] } | null>(null)

const RANGE_LABEL: Record<string, string> = { '3m': '近3月', '6m': '近6月', '1y': '近1年' }

function todayStr(offsetDays = 0) {
  const n = new Date()
  n.setDate(n.getDate() + offsetDays)
  const p = (x: number) => String(x).padStart(2, '0')
  return `${n.getFullYear()}-${p(n.getMonth() + 1)}-${p(n.getDate())}`
}

function rangeDates(): [string, string] {
  if (range.value === '3m') return [todayStr(-90), todayStr()]
  if (range.value === '6m') return [todayStr(-180), todayStr()]
  if (range.value === '1y') return [todayStr(-365), todayStr()]
  return [dateRange.value[0] || todayStr(-180), dateRange.value[1] || todayStr()]
}

async function handleRun() {
  const [s, e] = rangeDates()
  loading.value = true
  try {
    result.value = await DoctorAPI.selfcheck(s, e)
  }
  catch { /* toast */ }
  finally { loading.value = false }
}

function scoreColor(score: number) {
  if (score >= 90) return '#10b981'
  if (score >= 80) return '#f59e0b'
  return '#ef4444'
}
</script>

<template>
  <view class="sc-page">
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
      <button class="run-btn" :disabled="loading" @click="handleRun">
        {{ loading ? '评估中...' : '开始 AI 自评' }}
      </button>
    </view>

    <!-- 结果 -->
    <template v-if="result">
      <view class="card score-card">
        <text class="score-num" :style="{ color: scoreColor(result.score) }">{{ result.score }}</text>
        <text class="score-label">模拟自评得分（满分100）</text>
        <text class="score-meta">统计病例：{{ result.case_count }} 例</text>
      </view>

      <!-- 指标达标率 -->
      <view class="card">
        <text class="title">认证指标达标情况</text>
        <view v-for="it in result.items" :key="it.key" class="metric">
          <view class="metric-head">
            <text class="metric-name">{{ it.name }}</text>
            <text class="metric-rate" :style="{ color: it.ok ? '#10b981' : '#ef4444' }">
              {{ it.rate != null ? `${it.rate}%` : '无数据' }}
            </text>
          </view>
          <text class="metric-detail">{{ it.pass }}/{{ it.total }} 例达标</text>
        </view>
      </view>

      <!-- 改进建议 -->
      <view class="card">
        <text class="title">AI 改进意见</text>
        <view v-for="(s, i) in result.suggestions" :key="i" class="suggest">
          <text class="suggest-dot">·</text>
          <text class="suggest-text">{{ s }}</text>
        </view>
      </view>
    </template>

    <view v-else class="hint">选择时间区间后点击"开始 AI 自评"</view>
  </view>
</template>

<style lang="scss" scoped>
.sc-page { min-height: 100vh; background: #f3f4f6; padding: 24rpx 32rpx 60rpx; }
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
.range-item.active { background: #7c3aed; color: #ffffff; }

.run-btn {
  margin-top: 24rpx;
  height: 88rpx;
  line-height: 88rpx;
  border-radius: 18rpx;
  background: linear-gradient(135deg, #7c3aed, #6366f1);
  color: #ffffff;
  font-size: 30rpx;
  font-weight: 600;
}
.run-btn::after { border: none; }

.score-card { display: flex; flex-direction: column; align-items: center; }
.score-num { font-size: 96rpx; font-weight: 700; }
.score-label { margin-top: 8rpx; font-size: 28rpx; color: #1f2937; }
.score-meta { margin-top: 10rpx; font-size: 24rpx; color: #9ca3af; }

.metric { padding: 20rpx; border-radius: 16rpx; background: #f9fafb; margin-bottom: 16rpx; }
.metric-head { display: flex; align-items: center; justify-content: space-between; }
.metric-name { font-size: 28rpx; font-weight: 600; color: #1f2937; }
.metric-rate { font-size: 30rpx; font-weight: 700; }
.metric-detail { display: block; margin-top: 8rpx; font-size: 24rpx; color: #9ca3af; }

.suggest { display: flex; gap: 12rpx; margin-bottom: 14rpx; }
.suggest-dot { color: #7c3aed; }
.suggest-text { flex: 1; font-size: 26rpx; color: #4b5563; line-height: 1.6; }

.hint { text-align: center; padding-top: 120rpx; color: #9ca3af; font-size: 26rpx; }
</style>
