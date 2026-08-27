<!-- AI 拍照识别（模拟）：选图 → 模拟识别结构化字段 → 确认回填病例 -->
<script setup lang="ts">
import { ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import DoctorAPI, { type CaseRecordItem } from '@/api/module_cpx/doctor'

definePage({
  name: 'ai-ocr',
  style: { navigationBarTitleText: '拍照识别录入' },
})

const cases = ref<CaseRecordItem[]>([])
const caseId = ref(0)
const imagePath = ref('')
const recognizing = ref(false)
const saving = ref(false)
const templateId = ref(0)
// 模拟识别结果（真实环境由 AI OCR 返回）
const result = ref<Record<string, string>>({})

onLoad(async () => {
  try {
    const res = await DoctorAPI.myCases({ page_no: 1, page_size: 50 })
    cases.value = res.items
  }
  catch { /* toast */ }
})

function chooseImage() {
  uni.chooseImage({
    count: 1,
    success: (res) => {
      imagePath.value = res.tempFilePaths[0]
      mockRecognize()
    },
  })
}

/** 模拟 AI 识别（真实环境调用 OCR 接口） */
function mockRecognize() {
  recognizing.value = true
  setTimeout(() => {
    result.value = {
      patient_name: '识别-患者姓名',
      diagnose_type: 'STEMI',
      onset_time: '2026-08-21 08:00',
      chief_complaint: '胸痛伴大汗2小时',
    }
    recognizing.value = false
  }, 1200)
}

async function handleFill() {
  if (!caseId.value) {
    uni.showToast({ title: '请选择病例', icon: 'none' })
    return
  }
  // 读取病例所用模板
  saving.value = true
  try {
    const detail = await DoctorAPI.caseDetail(caseId.value)
    templateId.value = detail.template_id || 0
    await DoctorAPI.saveForm(caseId.value, { template_id: templateId.value, form_data: { ...result.value } })
    uni.showToast({ title: '已回填病例', icon: 'success' })
  }
  catch { /* toast */ }
  finally { saving.value = false }
}
</script>

<template>
  <view class="ocr-page">
    <!-- 选择病例 -->
    <view class="card">
      <text class="label">目标病例</text>
      <picker
        :range="cases"
        range-key="case_no"
        @change="(e) => { caseId = cases[e.detail.value].id }"
      >
        <view class="picker-box" :class="{ empty: !caseId }">
          {{ cases.find((c) => c.id === caseId)?.case_no || '请选择病例（草稿/驳回可回填）' }}
        </view>
      </picker>
    </view>

    <!-- 选图 -->
    <view class="card">
      <text class="label">上传识别图片</text>
      <view v-if="!imagePath" class="upload-box" @click="chooseImage">
        <text class="upload-icon">📷</text>
        <text class="upload-text">点击拍照 / 从相册选择</text>
      </view>
      <view v-else class="preview-box">
        <image :src="imagePath" class="preview-img" mode="aspectFit" />
        <view class="re-upload" @click="chooseImage">重新选择</view>
      </view>
    </view>

    <!-- 识别结果 -->
    <view v-if="Object.keys(result).length" class="card">
      <text class="label">{{ recognizing ? '识别中...' : '识别结果（可修改）' }}</text>
      <view v-for="(v, k) in result" :key="k" class="result-row">
        <text class="result-key">{{ k }}</text>
        <input v-model="result[k]" class="result-input" />
      </view>
      <button class="fill-btn" :disabled="saving" @click="handleFill">
        {{ saving ? '回填中...' : '确认回填病例' }}
      </button>
    </view>

    <text class="tip">* 当前为模拟识别，接入真实 OCR 服务后自动提取字段</text>
  </view>
</template>

<style lang="scss" scoped>
.ocr-page { min-height: 100vh; background: #f3f4f6; padding: 24rpx 32rpx 60rpx; }
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

.upload-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 60rpx 0;
  border-radius: 16rpx;
  border: 2rpx dashed #d1d5db;
}
.upload-icon { font-size: 60rpx; }
.upload-text { margin-top: 16rpx; font-size: 26rpx; color: #9ca3af; }

.preview-box { position: relative; }
.preview-img { width: 100%; height: 400rpx; border-radius: 16rpx; }
.re-upload { margin-top: 16rpx; text-align: center; font-size: 26rpx; color: #2563eb; }

.result-row { display: flex; align-items: center; gap: 16rpx; margin-bottom: 16rpx; }
.result-key {
  width: 220rpx;
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
  background: linear-gradient(135deg, #7c3aed, #6366f1);
  color: #ffffff;
  font-size: 30rpx;
  font-weight: 600;
}
.fill-btn::after { border: none; }

.tip { display: block; text-align: center; font-size: 22rpx; color: #c0c4cc; }
</style>
