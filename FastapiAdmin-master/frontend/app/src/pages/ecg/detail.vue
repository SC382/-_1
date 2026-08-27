<!-- 远程心电详情：发起方查看 AI 诊断与反馈 / 接收方写反馈 / 双方可申请协同 -->
<script setup lang="ts">
import { computed, ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import DoctorAPI, { type EcgConsultDetail, type HospitalOpenItem } from '@/api/module_cpx/doctor'

definePage({
  name: 'ecg-detail',
  style: { navigationBarTitleText: '心电详情' },
})

const id = ref(0)
const loading = ref(false)
const detail = ref<EcgConsultDetail | null>(null)

const STATUS_META: Record<string, { label: string; color: string; bg: string }> = {
  uploaded: { label: 'AI 已诊断', color: '#2563eb', bg: '#dbeafe' },
  consult_sent: { label: '已发送会诊', color: '#f59e0b', bg: '#fef3c7' },
  received: { label: '已接收', color: '#8b5cf6', bg: '#ede9fe' },
  closed: { label: '已完成', color: '#10b981', bg: '#d1fae5' },
}
function statusMeta(s?: string | null) {
  return STATUS_META[s || ''] || { label: s || '-', color: '#9ca3af', bg: '#f3f4f6' }
}

const isInitiator = computed(() => detail.value?.is_initiator === true)
const canSendConsult = computed(
  () => isInitiator.value && (detail.value?.status === 'uploaded' || detail.value?.status === 'consult_sent'),
)
const canFeedback = computed(
  () => !isInitiator.value && (detail.value?.status === 'consult_sent' || detail.value?.status === 'received'),
)

onLoad(async (q) => {
  id.value = Number(q?.id || 0)
  if (!id.value) return
  loading.value = true
  try {
    detail.value = await DoctorAPI.ecgDetail(id.value)
  }
  catch {
    uni.showToast({ title: '加载失败', icon: 'none' })
  }
  finally {
    loading.value = false
  }
})

// 申请协同：选医院
const showHospitalPicker = ref(false)
const hospitals = ref<HospitalOpenItem[]>([])
const hospitalLoading = ref(false)
const hospitalQ = reactive({ keyword: '' })
async function openHospitalPicker() {
  if (!detail.value) return
  showHospitalPicker.value = true
  hospitalQ.keyword = ''
  hospitalLoading.value = true
  try {
    hospitals.value = await DoctorAPI.units()
  }
  finally {
    hospitalLoading.value = false
  }
}
async function searchHospitals() {
  hospitalLoading.value = true
  try {
    const all = await DoctorAPI.units()
    hospitals.value = hospitalQ.keyword
      ? all.filter((h) => h.hospital_name.includes(hospitalQ.keyword))
      : all
  }
  finally {
    hospitalLoading.value = false
  }
}
const sending = ref(false)
async function pickHospital(h: HospitalOpenItem) {
  if (!detail.value) return
  if (h.hospital_id === detail.value.target_hospital_id) {
    uni.showToast({ title: '已发送给该医院', icon: 'none' })
    return
  }
  sending.value = true
  showHospitalPicker.value = false
  try {
    await DoctorAPI.ecgSendConsult(detail.value.id, { target_hospital_id: h.hospital_id })
    uni.showToast({ title: '协同申请已发送', icon: 'success' })
    detail.value = await DoctorAPI.ecgDetail(id.value)
  }
  catch (e: any) {
    uni.showToast({ title: e?.message || '发送失败', icon: 'none' })
  }
  finally {
    sending.value = false
  }
}

// 反馈
const feedbackText = ref('')
const submitting = ref(false)
async function submitFeedback() {
  if (!detail.value) return
  const t = feedbackText.value.trim()
  if (!t) {
    uni.showToast({ title: '请填写反馈意见', icon: 'none' })
    return
  }
  submitting.value = true
  try {
    await DoctorAPI.ecgFeedback(detail.value.id, { feedback: t })
    uni.showToast({ title: '反馈已提交', icon: 'success' })
    detail.value = await DoctorAPI.ecgDetail(id.value)
    feedbackText.value = ''
  }
  catch (e: any) {
    uni.showToast({ title: e?.message || '提交失败', icon: 'none' })
  }
  finally {
    submitting.value = false
  }
}

// 病例信息（从 patient_info_json 解析）
const patientInfo = computed(() => {
  if (!detail.value?.patient_info_json) return null
  try {
    return JSON.parse(detail.value.patient_info_json)
  }
  catch {
    return null
  }
})
</script>

<template>
  <view class="detail-page">
    <view v-if="loading" class="loading">加载中...</view>
    <template v-else-if="detail">
      <!-- 状态徽标 -->
      <view class="status-bar">
        <text class="status-tag" :style="{ color: statusMeta(detail.status).color, background: statusMeta(detail.status).bg }">
          {{ statusMeta(detail.status).label }}
        </text>
        <text v-if="isInitiator" class="role-tip">我发起的</text>
        <text v-else class="role-tip">来自：{{ detail.target_hospital_name || detail.target_hospital_id || '外院' }}</text>
      </view>

      <!-- 患者信息 -->
      <view v-if="patientInfo" class="patient-card">
        <text class="card-title">患者信息</text>
        <view class="info-row"><text class="info-label">姓名</text><text class="info-value">{{ patientInfo.patient_name || '-' }}</text></view>
        <view class="info-row"><text class="info-label">性别 / 年龄</text><text class="info-value">{{ patientInfo.gender || '-' }} / {{ patientInfo.age ?? '-' }}岁</text></view>
        <view class="info-row"><text class="info-label">诊断类型</text><text class="info-value">{{ patientInfo.diagnose_type || '-' }}</text></view>
        <view class="info-row"><text class="info-label">病例编号</text><text class="info-value mono">{{ detail.case_no || '-' }}</text></view>
      </view>

      <!-- 心电图 -->
      <view v-if="detail.image_path" class="image-card">
        <text class="card-title">心电图</text>
        <image :src="detail.image_path" class="ecg-image" mode="aspectFit" />
      </view>

      <!-- AI 诊断 -->
      <view v-if="detail.ai_diagnosis" class="ai-card">
        <view class="ai-head">
          <text class="ai-icon">🤖</text>
          <text class="card-title">AI 辅助诊断</text>
        </view>
        <text class="ai-text">{{ detail.ai_diagnosis }}</text>
      </view>

      <!-- AI 协同意见（发给接收方） -->
      <view v-if="detail.ai_summary" class="ai-card summary-card">
        <view class="ai-head">
          <text class="ai-icon">📋</text>
          <text class="card-title">AI 协同意见（已随会诊发送）</text>
        </view>
        <text class="ai-text">{{ detail.ai_summary }}</text>
      </view>

      <!-- 接收方反馈 -->
      <view v-if="detail.feedback" class="ai-card feedback-card">
        <view class="ai-head">
          <text class="ai-icon">💬</text>
          <text class="card-title">会诊反馈</text>
        </view>
        <text class="ai-text">{{ detail.feedback }}</text>
        <text v-if="detail.feedback_time" class="fb-time">反馈时间：{{ detail.feedback_time }}</text>
      </view>

      <!-- 操作：发起方申请协同 -->
      <view v-if="canSendConsult" class="ops">
        <button class="op-btn op-consult" :disabled="sending" @click="openHospitalPicker">
          {{ detail.status === 'consult_sent' ? '重新选择接收医院' : '申请协同（选医院）' }}
        </button>
        <text v-if="detail.target_hospital_name" class="op-hint">已发送至：{{ detail.target_hospital_name }}</text>
      </view>

      <!-- 操作：接收方写反馈 -->
      <view v-if="canFeedback" class="ops">
        <textarea
          v-model="feedbackText"
          class="feedback-input"
          placeholder="请填写会诊反馈意见（例：同意 AI 诊断，建议尽快 PCI）"
          maxlength="500"
        />
        <button class="op-btn op-feedback" :disabled="submitting" @click="submitFeedback">
          {{ submitting ? '提交中...' : '提交反馈' }}
        </button>
      </view>

      <view v-if="detail.status === 'closed'" class="ops">
        <view class="done-tag">✅ 本次会诊已完成</view>
      </view>
    </template>

    <!-- 选医院弹层 -->
    <view v-if="showHospitalPicker" class="picker-mask" @click="showHospitalPicker = false">
      <view class="picker-panel" @click.stop>
        <view class="picker-head">
          <text class="picker-title">选择接收医院</text>
          <text class="picker-close" @click="showHospitalPicker = false">×</text>
        </view>
        <view class="picker-search">
          <input
            v-model="hospitalQ.keyword"
            class="picker-input"
            placeholder="医院名称"
            confirm-type="search"
            @confirm="searchHospitals"
          />
          <view class="picker-search-btn" @click="searchHospitals">搜索</view>
        </view>
        <scroll-view scroll-y class="picker-scroll">
          <view v-if="hospitalLoading" class="picker-loading">加载中...</view>
          <view v-else-if="!hospitals.length" class="empty">暂无可选医院</view>
          <view v-else>
            <view
              v-for="h in hospitals"
              :key="h.hospital_id"
              class="picker-item"
              @click="pickHospital(h)"
            >
              <view>
                <text class="picker-item-name">{{ h.hospital_name }}</text>
                <text class="picker-item-level">{{ h.hospital_level || '' }}</text>
              </view>
              <text v-if="h.hospital_id === detail?.target_hospital_id" class="picker-item-cur">当前</text>
            </view>
          </view>
        </scroll-view>
      </view>
    </view>
  </view>
</template>

<style lang="scss" scoped>
.detail-page { min-height: 100vh; background: #f3f4f6; padding: 24rpx 32rpx 80rpx; }
.loading { text-align: center; padding: 200rpx 0; color: #9ca3af; }

.status-bar { display: flex; align-items: center; gap: 16rpx; margin-bottom: 24rpx; }
.status-tag { font-size: 26rpx; padding: 8rpx 20rpx; border-radius: 16rpx; font-weight: 600; }
.role-tip { font-size: 24rpx; color: #6b7280; }

.patient-card, .image-card, .ai-card, .ops {
  padding: 28rpx;
  border-radius: 20rpx;
  background: #ffffff;
  margin-bottom: 24rpx;
}
.card-title { display: block; font-size: 30rpx; font-weight: 600; color: #1f2937; margin-bottom: 16rpx; }

.info-row { display: flex; padding: 12rpx 0; }
.info-label { width: 200rpx; font-size: 26rpx; color: #9ca3af; }
.info-value { flex: 1; font-size: 26rpx; color: #1f2937; }
.info-value.mono { font-family: monospace; }

.ecg-image { width: 100%; height: 600rpx; border-radius: 12rpx; background: #f3f4f6; }

.ai-card .ai-head { display: flex; align-items: center; gap: 12rpx; margin-bottom: 12rpx; }
.ai-icon { font-size: 32rpx; }
.ai-text { font-size: 28rpx; color: #374151; line-height: 1.7; white-space: pre-wrap; }
.summary-card { background: #fffbeb; }
.feedback-card { background: #f0fdf4; }
.fb-time { display: block; margin-top: 12rpx; font-size: 22rpx; color: #6b7280; }

.ops { background: #ffffff; }
.op-btn {
  width: 100%;
  height: 100rpx;
  line-height: 100rpx;
  border-radius: 24rpx;
  font-size: 30rpx;
  font-weight: 600;
  border: none;
}
.op-consult { background: linear-gradient(135deg, #f59e0b, #fbbf24); color: #ffffff; }
.op-feedback { background: linear-gradient(135deg, #10b981, #34d399); color: #ffffff; margin-top: 20rpx; }
.op-btn[disabled] { opacity: 0.5; }
.op-hint { display: block; margin-top: 16rpx; text-align: center; font-size: 24rpx; color: #6b7280; }
.feedback-input {
  width: 100%;
  min-height: 180rpx;
  padding: 20rpx;
  border-radius: 16rpx;
  background: #f3f4f6;
  font-size: 26rpx;
  margin-bottom: 16rpx;
  box-sizing: border-box;
}
.done-tag { text-align: center; font-size: 28rpx; color: #10b981; font-weight: 600; }

/* 选医院弹层 */
.picker-mask { position: fixed; inset: 0; background: rgba(0,0,0,0.5); z-index: 1000; display: flex; align-items: flex-end; }
.picker-panel { width: 100%; max-height: 80vh; background: #ffffff; border-radius: 24rpx 24rpx 0 0; display: flex; flex-direction: column; }
.picker-head { display: flex; align-items: center; justify-content: space-between; padding: 24rpx 32rpx; border-bottom: 2rpx solid #f3f4f6; }
.picker-title { font-size: 32rpx; font-weight: 600; color: #1f2937; }
.picker-close { font-size: 48rpx; color: #9ca3af; line-height: 1; padding: 0 16rpx; }
.picker-search { display: flex; gap: 12rpx; padding: 20rpx 32rpx; }
.picker-input { flex: 1; height: 72rpx; padding: 0 24rpx; border-radius: 16rpx; background: #f3f4f6; font-size: 26rpx; }
.picker-search-btn { padding: 0 28rpx; height: 72rpx; line-height: 72rpx; border-radius: 16rpx; background: #2563eb; color: #ffffff; font-size: 26rpx; }
.picker-scroll { max-height: 60vh; }
.picker-loading { padding: 80rpx 0; text-align: center; color: #9ca3af; }
.empty { padding: 80rpx 0; text-align: center; color: #9ca3af; font-size: 26rpx; }
.picker-item { display: flex; align-items: center; justify-content: space-between; padding: 28rpx 32rpx; border-bottom: 2rpx solid #f3f4f6; }
.picker-item-name { font-size: 30rpx; color: #1f2937; }
.picker-item-level { display: block; margin-top: 6rpx; font-size: 22rpx; color: #9ca3af; }
.picker-item-cur { font-size: 24rpx; color: #f59e0b; }
</style>
