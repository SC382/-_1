<!-- 远程心电：选完病例后上传心电图 → 自动 AI 诊断 → 跳详情 -->
<script setup lang="ts">
import { getApiBaseUrl } from '@/http'
import { safeBack } from '@/utils/back'
import { ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import DoctorAPI, { type CaseDetailData } from '@/api/module_cpx/doctor'
import { useUserStore } from '@/store/userStore'

definePage({
  name: 'ecg-upload',
  style: { navigationBarTitleText: '上传心电图' },
})

const BASE_URL = getApiBaseUrl()
const userStore = useUserStore()

const caseId = ref(0)
const loading = ref(false)
const detail = ref<CaseDetailData | null>(null)
const imagePath = ref('')
const uploadedUrl = ref('')
const submitting = ref(false)

onLoad(async (q) => {
  caseId.value = Number(q?.case_id || 0)
  if (!caseId.value) {
    uni.showToast({ title: '请先从病例列表选择', icon: 'none' })
    setTimeout(() => safeBack(), 800)
    return
  }
  loading.value = true
  try {
    detail.value = await DoctorAPI.caseDetail(caseId.value)
  }
  catch {
    uni.showToast({ title: '病例加载失败', icon: 'none' })
  }
  finally {
    loading.value = false
  }
})

function chooseImage() {
  uni.chooseImage({
    count: 1,
    sizeType: ['original', 'compressed'],
    sourceType: ['camera', 'album'],
    success: (res) => {
      imagePath.value = res.tempFilePaths[0]
    },
  })
}

/** 选完后：上传图片 → 拿 URL → 调 ecgUpload → 跳详情 */
async function submitAi() {
  if (!imagePath.value) {
    uni.showToast({ title: '请先选择心电图', icon: 'none' })
    return
  }
  submitting.value = true
  uni.showLoading({ title: 'AI 诊断中...' })
  try {
    // 1) 上传图片到后端拿到 URL
    const fileUrl: string = await new Promise((resolve, reject) => {
      uni.uploadFile({
        url: `${BASE_URL}/api/v1/cpx/doctor/upload/image`,
        filePath: imagePath.value,
        name: 'file',
        header: { Authorization: `Bearer ${userStore.getAccessToken() || ''}` },
        success: (r) => {
          try {
            const d = JSON.parse(r.data)
            if (d.code === 0 && d.data?.url) resolve(d.data.url)
            else reject(new Error(d.msg || '图片上传失败'))
          }
          catch (e) { reject(e) }
        },
        fail: () => reject(new Error('图片上传失败')),
      })
    })
    uploadedUrl.value = fileUrl
    // 2) 调 ecg/upload 触发 AI 诊断
    const r = await DoctorAPI.ecgUpload({ case_id: caseId.value, image_path: fileUrl })
    uni.hideLoading()
    uni.showToast({ title: 'AI 诊断完成', icon: 'success' })
    setTimeout(() => {
      uni.redirectTo({ url: `/pages/ecg/detail?id=${r.id}` })
    }, 600)
  }
  catch (e: any) {
    uni.hideLoading()
    uni.showToast({ title: e?.message || '提交失败', icon: 'none' })
  }
  finally {
    submitting.value = false
  }
}
</script>

<template>
  <view class="upload-page">
    <view v-if="loading" class="loading">加载病例中...</view>
    <template v-else-if="detail">
      <!-- 患者信息卡 -->
      <view class="patient-card">
        <text class="card-title">患者信息</text>
        <view class="info-row"><text class="info-label">姓名</text><text class="info-value">{{ detail.patient_name || '-' }}</text></view>
        <view class="info-row"><text class="info-label">性别 / 年龄</text><text class="info-value">{{ detail.gender || '-' }} / {{ detail.age ?? '-' }}岁</text></view>
        <view class="info-row"><text class="info-label">病例编号</text><text class="info-value mono">{{ detail.case_no }}</text></view>
        <view class="info-row"><text class="info-label">诊断类型</text><text class="info-value">{{ detail.diagnose_type || '-' }}</text></view>
        <view class="info-row"><text class="info-label">来院方式</text><text class="info-value">{{ detail.come_type || '-' }}</text></view>
        <view class="info-row"><text class="info-label">所属医院</text><text class="info-value">{{ detail.hospital_name || '-' }}</text></view>
      </view>

      <!-- 图片上传区 -->
      <view class="upload-card">
        <text class="card-title">心电图</text>
        <view v-if="!imagePath" class="upload-box" @click="chooseImage">
          <text class="upload-icon">📷</text>
          <text class="upload-text">点击拍照 / 从相册选择</text>
        </view>
        <view v-else class="preview-wrap">
          <image :src="imagePath" class="preview" mode="aspectFit" @click="chooseImage" />
          <view class="rechoose" @click="chooseImage">重新选择</view>
        </view>
      </view>

      <button class="submit-btn" :disabled="submitting || !imagePath" @click="submitAi">
        {{ submitting ? 'AI 诊断中...' : '保存并 AI 辅助诊断' }}
      </button>
      <view class="tip">提交后将自动生成 AI 诊断与协同意见总结，可在「详情」中申请会诊上级医院</view>
    </template>
  </view>
</template>

<style lang="scss" scoped>
.upload-page { min-height: 100vh; background: #f3f4f6; padding: 24rpx 32rpx 80rpx; }
.loading { text-align: center; padding: 200rpx 0; color: #9ca3af; }

.patient-card, .upload-card {
  padding: 28rpx;
  border-radius: 20rpx;
  background: #ffffff;
  margin-bottom: 24rpx;
}
.card-title { display: block; font-size: 30rpx; font-weight: 600; color: #1f2937; margin-bottom: 20rpx; }

.info-row { display: flex; padding: 14rpx 0; border-bottom: 1rpx solid #f3f4f6; }
.info-row:last-child { border-bottom: none; }
.info-label { width: 200rpx; font-size: 26rpx; color: #9ca3af; }
.info-value { flex: 1; font-size: 26rpx; color: #1f2937; }
.info-value.mono { font-family: monospace; }

.upload-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 100rpx 0;
  border-radius: 16rpx;
  border: 2rpx dashed #d1d5db;
  background: #fafbfc;
}
.upload-icon { font-size: 80rpx; }
.upload-text { margin-top: 20rpx; font-size: 26rpx; color: #9ca3af; }

.preview-wrap { display: flex; flex-direction: column; align-items: center; gap: 16rpx; }
.preview { width: 100%; height: 500rpx; border-radius: 16rpx; background: #f3f4f6; }
.rechoose { padding: 12rpx 32rpx; border-radius: 16rpx; background: #eff6ff; color: #2563eb; font-size: 24rpx; }

.submit-btn {
  width: 100%;
  height: 100rpx;
  line-height: 100rpx;
  border-radius: 24rpx;
  background: linear-gradient(135deg, #2563eb, #38bdf8);
  color: #ffffff;
  font-size: 30rpx;
  font-weight: 600;
  border: none;
  margin-top: 16rpx;
}
.submit-btn[disabled] { opacity: 0.5; }
.tip { margin-top: 16rpx; text-align: center; font-size: 22rpx; color: #9ca3af; }
</style>
