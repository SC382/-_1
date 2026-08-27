<!-- 智慧急诊预检分诊：症状勾选 + 体征 → 模拟分诊等级（外部云平台二期对接） -->
<script setup lang="ts">
import { ref } from 'vue'

definePage({
  name: 'triage',
  style: { navigationBarTitleText: '智慧急诊预检分诊' },
})

const symptoms = ref<string[]>([])
const heartRate = ref('')
const spo2 = ref('')
const result = ref<{ level: string; color: string; advice: string } | null>(null)

const SYMPTOM_OPTIONS = [
  { label: '胸痛', risk: 3 },
  { label: '呼吸困难', risk: 3 },
  { label: '大汗淋漓', risk: 3 },
  { label: '晕厥/意识改变', risk: 3 },
  { label: '上腹部不适', risk: 2 },
  { label: '恶心呕吐', risk: 1 },
  { label: '肩背放射痛', risk: 2 },
  { label: '持续胸闷 >20min', risk: 3 },
]

function toggle(sym: string) {
  const i = symptoms.value.indexOf(sym)
  if (i >= 0)
    symptoms.value.splice(i, 1)
  else
    symptoms.value.push(sym)
}

function handleAssess() {
  let risk = 0
  SYMPTOM_OPTIONS.forEach((s) => {
    if (symptoms.value.includes(s.label))
      risk += s.risk
  })
  const hr = Number(heartRate.value)
  const o2 = Number(spo2.value)
  if (hr > 120 || hr < 50 || (o2 && o2 < 90))
    risk += 3

  if (risk >= 5) {
    result.value = { level: 'Ⅰ级 立即抢救', color: '#ef4444', advice: '疑似高危胸痛（STEMI/主动脉夹层/肺栓塞），立即启动胸痛绿色通道，完成心电图并呼叫心内科会诊' }
  }
  else if (risk >= 3) {
    result.value = { level: 'Ⅱ级 紧急处置', color: '#f97316', advice: '高危胸痛待排查，10 分钟内完成心电图、肌钙蛋白检测，建立静脉通路，持续监护' }
  }
  else if (risk >= 1) {
    result.value = { level: 'Ⅲ级 优先就诊', color: '#f59e0b', advice: '中危胸痛，安排心内科就诊，完善心电图及心肌损伤标志物检查' }
  }
  else {
    result.value = { level: 'Ⅳ级 普通就诊', color: '#10b981', advice: '低危胸痛，常规就诊观察，若症状加重随时复评' }
  }
}
</script>

<template>
  <view class="tr-page">
    <view class="card">
      <text class="title">症状评估</text>
      <view class="sym-grid">
        <view
          v-for="s in SYMPTOM_OPTIONS"
          :key="s.label"
          class="sym-item"
          :class="{ active: symptoms.includes(s.label) }"
          @click="toggle(s.label)"
        >{{ s.label }}</view>
      </view>
    </view>

    <view class="card">
      <text class="title">生命体征</text>
      <view class="vital-row">
        <view class="vital-field">
          <text class="vital-label">心率（次/分）</text>
          <input v-model="heartRate" class="vital-input" type="number" placeholder="如 95" placeholder-class="ph" />
        </view>
        <view class="vital-field">
          <text class="vital-label">血氧 SpO₂（%）</text>
          <input v-model="spo2" class="vital-input" type="number" placeholder="如 96" placeholder-class="ph" />
        </view>
      </view>
      <button class="assess-btn" @click="handleAssess">AI 预检分诊评估</button>
    </view>

    <view v-if="result" class="result-card" :style="{ borderColor: result.color }">
      <text class="result-level" :style="{ color: result.color }">{{ result.level }}</text>
      <text class="result-advice">{{ result.advice }}</text>
    </view>

    <text class="tip">* 本地模拟分诊，二期对接「智慧急诊预检分诊云平台」</text>
  </view>
</template>

<style lang="scss" scoped>
.tr-page { min-height: 100vh; background: #f3f4f6; padding: 24rpx 32rpx 60rpx; }
.card { margin-bottom: 24rpx; padding: 32rpx; border-radius: 24rpx; background: #ffffff; }
.title { display: block; font-size: 30rpx; font-weight: 600; color: #1f2937; margin-bottom: 20rpx; }

.sym-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 16rpx; }
.sym-item {
  text-align: center;
  padding: 22rpx 0;
  border-radius: 16rpx;
  background: #f3f4f6;
  font-size: 26rpx;
  color: #4b5563;
}
.sym-item.active { background: #ef4444; color: #ffffff; }

.vital-row { display: flex; gap: 20rpx; }
.vital-field { flex: 1; }
.vital-label { display: block; font-size: 24rpx; color: #6b7280; margin-bottom: 10rpx; }
.vital-input {
  height: 80rpx;
  padding: 0 20rpx;
  border-radius: 14rpx;
  background: #f3f4f6;
  font-size: 28rpx;
}
.ph { color: #9ca3af; }

.assess-btn {
  margin-top: 24rpx;
  height: 88rpx;
  line-height: 88rpx;
  border-radius: 18rpx;
  background: linear-gradient(135deg, #ef4444, #f97316);
  color: #ffffff;
  font-size: 30rpx;
  font-weight: 600;
}
.assess-btn::after { border: none; }

.result-card {
  margin-bottom: 24rpx;
  padding: 32rpx;
  border-radius: 24rpx;
  background: #ffffff;
  border-left: 8rpx solid;
}
.result-level { font-size: 36rpx; font-weight: 700; }
.result-advice { display: block; margin-top: 14rpx; font-size: 26rpx; color: #4b5563; line-height: 1.7; }

.tip { display: block; text-align: center; font-size: 22rpx; color: #c0c4cc; }
</style>
