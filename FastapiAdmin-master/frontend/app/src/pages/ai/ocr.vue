<!-- AI 拍照识别（真实）：选图 → 智谱视觉识别结构化字段 → 确认回填病例 -->
<script setup lang="ts">
import { ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import DoctorAPI, { type CaseRecordItem, type FieldDict } from '@/api/module_cpx/doctor'

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
// AI 识别结果（真实接口返回）
const result = ref<Record<string, string>>({})
// 字段编码 → 中文名 映射（用于识别结果标签本地化）
const fieldNameMap = ref<Record<string, string>>({})

onLoad(async () => {
  try {
    const [listRes, dictRes] = await Promise.all([
      DoctorAPI.myCases({ page_no: 1, page_size: 50 }),
      DoctorAPI.fieldDict(),
    ])
    cases.value = listRes.items
    buildFieldNameMap(dictRes)
  }
  catch { /* toast */ }
})

function buildFieldNameMap(dict: FieldDict) {
  const map: Record<string, string> = {}
  for (const f of dict.fields) {
    if (f.field_code) map[f.field_code] = f.field_name || f.field_code
  }
  fieldNameMap.value = map
}

function labelOf(key: string): string {
  return fieldNameMap.value[key] || key
}

function chooseImage() {
  uni.chooseImage({
    count: 1,
    success: (res) => {
      imagePath.value = res.tempFilePaths[0]
      realRecognize()
    },
  })
}

/** 真实 AI 识别：本地图片转 base64 data URI 内联 → 调后端 /cpx/doctor/ai/recognize */
async function realRecognize() {
  if (!imagePath.value) return
  recognizing.value = true
  try {
    const base64 = await readFileAsBase64(imagePath.value)
    const res = await DoctorAPI.recognize({ image_url: base64 })
    if (res.raw_text) {
      // 结构化解析失败，回退展示原文，提示用户手动整理
      result.value = { raw_text: res.raw_text }
      uni.showToast({ title: '未提取到结构化字段，请手动整理', icon: 'none' })
    }
    else {
      result.value = res
    }
  }
  catch {
    uni.showToast({ title: '识别失败，请重试', icon: 'none' })
  }
  finally {
    recognizing.value = false
  }
}

/** 用 uni 文件系统读取本地图片为 base64 data URI（按扩展名推断 mime） */
function readFileAsBase64(filePath: string): Promise<string> {
  return new Promise((resolve, reject) => {
    const ext = filePath.split('.').pop()?.toLowerCase() || 'jpg'
    const mime = ext === 'png' ? 'image/png' : ext === 'bmp' ? 'image/bmp' : 'image/jpeg'
    uni.getFileSystemManager().readFile({
      filePath,
      encoding: 'base64',
      success: (r) => resolve(`data:${mime};base64,${r.data as string}`),
      fail: (e) => reject(e),
    })
  })
}

async function handleFill() {
  if (!caseId.value) {
    uni.showToast({ title: '请选择病例', icon: 'none' })
    return
  }
  // 排除非结构化原文，避免污染病例数据
  const form: Record<string, string> = {}
  for (const [k, v] of Object.entries(result.value)) {
    if (k === 'raw_text') continue
    form[k] = v
  }
  if (!Object.keys(form).length) {
    uni.showToast({ title: '没有可回填的字段', icon: 'none' })
    return
  }
  saving.value = true
  try {
    const detail = await DoctorAPI.caseDetail(caseId.value)
    templateId.value = detail.template_id || 0
    await DoctorAPI.saveForm(caseId.value, { template_id: templateId.value, form_data: form })
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
        <text class="result-key">{{ labelOf(k) }}</text>
        <input v-model="result[k]" class="result-input" />
      </view>
      <button class="fill-btn" :disabled="saving || recognizing" @click="handleFill">
        {{ saving ? '回填中...' : '确认回填病例' }}
      </button>
    </view>

    <text class="tip">* 图片经 AI（智谱视觉）识别后自动提取字段，可修改后回填病例</text>
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
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
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
