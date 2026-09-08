<!-- AI 语音录入：录音 → 真实语音转写 → 关键词解析 → 回填病例 -->
<script setup lang="ts">
import { ref } from 'vue'
import { onLoad, onUnload } from '@dcloudio/uni-app'
import DoctorAPI, { type CaseRecordItem } from '@/api/module_cpx/doctor'

definePage({
  name: 'ai-voice',
  style: { navigationBarTitleText: 'AI语音录入' },
})

const cases = ref<CaseRecordItem[]>([])
const caseId = ref(0)
const templateId = ref(0)
const text = ref('')
const recording = ref(false)
const transcribing = ref(false)
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

/** 选择目标病例：picker 下标 → caseId */
function onCaseChange(e: { detail: { value: number } }) {
  caseId.value = cases.value[e.detail.value].id
}

onLoad(async () => {
  try {
    const res = await DoctorAPI.myCases({ page_no: 1, page_size: 50 })
    cases.value = res.items
  }
  catch { /* toast */ }
})

onUnload(() => {
  if (recording.value && recorderManager) recorderManager.stop()
})

// 原生录音 → base64 → 后端 ASR 转写（仅 app-plus 支持原生录音，H5 降级提示）
let recorderManager: any = null

function ensureRecorder() {
  if (recorderManager) return recorderManager
  const rm: any = uni.getRecorderManager()
  if (!rm) return null
  rm.onStop((res: any) => {
    recording.value = false
    const fs = uni.getFileSystemManager()
    fs.readFile({
      filePath: res.tempFilePath,
      encoding: 'base64',
      success: async (r: any) => {
        transcribing.value = true
        try {
          const data = await DoctorAPI.asr({ audio_base64: r.data as string, format: 'mp3' })
          text.value = data.text || ''
          uni.showToast({ title: '转写完成', icon: 'success' })
        }
        catch (e: any) {
          uni.showToast({ title: e?.msg || '语音识别失败', icon: 'none' })
        }
        finally {
          transcribing.value = false
        }
      },
      fail: () => {
        uni.showToast({ title: '读取录音失败', icon: 'none' })
      },
    })
  })
  rm.onError(() => {
    recording.value = false
    uni.showToast({ title: '录音失败', icon: 'none' })
  })
  recorderManager = rm
  return rm
}

function toggleRecord() {
  // 仅 App 端（真机 / 自定义基座）支持原生录音
  if ((uni.getSystemInfoSync() as any).platform !== 'app-plus') {
    uni.showToast({ title: '请在 App 端使用录音', icon: 'none' })
    return
  }
  const rm = ensureRecorder()
  if (!rm) {
    uni.showToast({ title: '当前环境不支持录音', icon: 'none' })
    return
  }
  if (recording.value) {
    rm.stop()
  }
  else {
    recording.value = true
    rm.start({ format: 'mp3', sampleRate: 16000 })
  }
}

/** 关键词解析（基于已转写文本提取结构化字段） */
function parseText() {
  const t = text.value.trim()
  if (!t) {
    uni.showToast({ title: '请先录音转写或输入文本', icon: 'none' })
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
  }, 600)
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
        @change="onCaseChange"
      >
        <view class="picker-box" :class="{ empty: !caseId }">
          {{ cases.find((c) => c.id === caseId)?.case_no || '请选择病例' }}
        </view>
      </picker>
    </view>

    <view class="card">
      <text class="label">语音转写</text>
      <button class="mic-btn" :class="{ recording }" :disabled="transcribing" @click="toggleRecord">
        {{ recording ? '⏹ 停止录音' : (transcribing ? '转写中...' : '🎙️ 点击开始录音') }}
      </button>
      <textarea v-model="text" class="voice-input" :disabled="recording" placeholder="录音自动转写为文字，也可手动输入：如 患者胸痛2小时，8点发病，已给予阿司匹林，分诊为高危" placeholder-class="ph" />
      <button class="parse-btn" :disabled="parsing || !text.trim()" @click="parseText">
        {{ parsing ? '解析中...' : 'AI 解析录入' }}
      </button>
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

.mic-btn {
  height: 88rpx;
  line-height: 88rpx;
  border-radius: 18rpx;
  background: linear-gradient(135deg, #10b981, #0ea5e9);
  color: #ffffff;
  font-size: 30rpx;
  font-weight: 600;
}
.mic-btn::after { border: none; }
.mic-btn.recording {
  background: linear-gradient(135deg, #ef4444, #f97316);
  animation: pulse 1s infinite;
}
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}

.voice-input {
  width: 100%;
  min-height: 160rpx;
  margin-top: 20rpx;
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
