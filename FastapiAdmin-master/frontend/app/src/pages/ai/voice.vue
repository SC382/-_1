<!-- AI 语音录入（模拟）：文本转写 → 关键词解析 → 回填病例 -->
<script setup lang="ts">
import { ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import DoctorAPI, { type CaseRecordItem } from '@/api/module_cpx/doctor'

definePage({
  name: 'ai-voice',
  style: { navigationBarTitleText: 'AI语音录入' },
})

const cases = ref<CaseRecordItem[]>([])
const caseId = ref(0)
const templateId = ref(0)
const text = ref('')
const parsing = ref(false)
const saving = ref(false)
const parsed = ref<Record<string, string>>({})

const FIELDS_LABEL: Record<string, string> = {
  chief_complaint: '主诉',
  onset_time: '发病时间',
  pre_medication: '院前用药',
  triage_result: '分诊结果',
  discharge_medication: '出院用药',
}

onLoad(async () => {
  try {
    const res = await DoctorAPI.myCases({ page_no: 1, page_size: 50 })
    cases.value = res.items
  }
  catch { /* toast */ }
})

/** 模拟语音转写 + 关键词解析（真实环境接入语音识别 + NLP） */
function parseText() {
  const t = text.value.trim()
  if (!t) {
    uni.showToast({ title: '请输入语音转写文本', icon: 'none' })
    return
  }
  parsing.value = true
  setTimeout(() => {
    const result: Record<string, string> = {}
    if (t.includes('胸痛'))
      result.chief_complaint = t
    const timeMatch = t.match(/(\d{1,2})[:：](\d{2})/)
    if (timeMatch)
      result.onset_time = `2026-08-21 ${timeMatch[1]}:${timeMatch[2]}`
    if (t.includes('阿司匹林') || t.includes('替格瑞洛'))
      result.pre_medication = t
    if (t.includes('高危') || t.includes('中危') || t.includes('低危'))
      result.triage_result = t.includes('低危') ? '低危' : t.includes('中危') ? '中危' : '高危'
    parsed.value = result
    parsing.value = false
  }, 1000)
}

async function handleFill() {
  if (!caseId.value) {
    uni.showToast({ title: '请选择病例', icon: 'none' })
    return
  }
  saving.value = true
  try {
    const detail = await DoctorAPI.caseDetail(caseId.value)
    templateId.value = detail.template_id || 0
    await DoctorAPI.saveForm(caseId.value, { template_id: templateId.value, form_data: { ...parsed.value } })
    uni.showToast({ title: '已回填病例', icon: 'success' })
  }
  catch { /* toast */ }
  finally { saving.value = false }
}
</script>

<template>
  <view class="voice-page">
    <view class="card">
      <text class="label">目标病例</text>
      <picker
        :range="cases"
        range-key="case_no"
        @change="(e) => { caseId = cases[e.detail.value].id }"
      >
        <view class="picker-box" :class="{ empty: !caseId }">
          {{ cases.find((c) => c.id === caseId)?.case_no || '请选择病例' }}
        </view>
      </picker>
    </view>

    <view class="card">
      <text class="label">语音转写文本</text>
      <textarea v-model="text" class="voice-input" placeholder="如：患者胸痛2小时，8点发病，已给予阿司匹林，分诊为高危" placeholder-class="ph" />
      <button class="parse-btn" :disabled="parsing" @click="parseText">
        {{ parsing ? '解析中...' : 'AI 解析录入' }}
      </button>
      <text class="mic-tip">🎙️ 真实环境：长按录音 → 语音转文字 → 自动解析</text>
    </view>

    <view v-if="Object.keys(parsed).length" class="card">
      <text class="label">解析结果（可修改）</text>
      <view v-for="(v, k) in parsed" :key="k" class="result-row">
        <text class="result-key">{{ FIELDS_LABEL[k] || k }}</text>
        <input v-model="parsed[k]" class="result-input" />
      </view>
      <button class="fill-btn" :disabled="saving" @click="handleFill">
        {{ saving ? '回填中...' : '确认回填病例' }}
      </button>
    </view>
  </view>
</template>

<style lang="scss" scoped>
.voice-page { min-height: 100vh; background: #f3f4f6; padding: 24rpx 32rpx 60rpx; }
.card { margin-bottom: 24rpx; padding: 32rpx; border-radius: 24rpx; background: #ffffff; }
.label { display: block; font-size: 26rpx; color: #4b5563; margin-bottom: 16rpx; }

.picker-box {
  height: 88rpx;
  line-height: 88rpx;
  padding: 0 24rpx;
  border-radius: 16rpx;
  background: #f3f4f6;
  font-size: 28rpx;
  color: #1f2937;
}
.picker-box.empty { color: #9ca3af; }

.voice-input {
  width: 100%;
  min-height: 160rpx;
  padding: 20rpx 24rpx;
  border-radius: 16rpx;
  background: #f3f4f6;
  font-size: 28rpx;
  box-sizing: border-box;
}
.ph { color: #9ca3af; }

.parse-btn {
  margin-top: 20rpx;
  height: 88rpx;
  line-height: 88rpx;
  border-radius: 18rpx;
  background: linear-gradient(135deg, #7c3aed, #6366f1);
  color: #ffffff;
  font-size: 30rpx;
  font-weight: 600;
}
.parse-btn::after { border: none; }
.mic-tip { display: block; margin-top: 16rpx; font-size: 22rpx; color: #c0c4cc; }

.result-row { display: flex; align-items: center; gap: 16rpx; margin-bottom: 16rpx; }
.result-key {
  width: 200rpx;
  font-size: 26rpx;
  color: #4b5563;
  background: #f3f4f6;
  padding: 0 16rpx;
  border-radius: 12rpx;
  height: 80rpx;
  line-height: 80rpx;
}
.result-input {
  flex: 1;
  height: 80rpx;
  padding: 0 20rpx;
  border-radius: 12rpx;
  background: #f3f4f6;
  font-size: 28rpx;
}

.fill-btn {
  margin-top: 24rpx;
  height: 88rpx;
  line-height: 88rpx;
  border-radius: 18rpx;
  background: linear-gradient(135deg, #10b981, #0ea5e9);
  color: #ffffff;
  font-size: 30rpx;
  font-weight: 600;
}
.fill-btn::after { border: none; }
</style>
