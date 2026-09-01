<!-- 随访详情表单：随访日期/状态/生存状态/危险因素/用药 -->
<script setup lang="ts">
import { ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import DoctorAPI, { type FollowUpItem } from '@/api/module_cpx/doctor'
import { safeBack } from '@/utils/back'

definePage({
  name: 'followup-detail',
  style: { navigationBarTitleText: '随访详情' },
})

const followId = ref(0)
const loading = ref(false)
const submitting = ref(false)
const detail = ref<FollowUpItem | null>(null)
const form = ref({
  follow_date: '',
  follow_status: 'followed',
  survival_status: 'alive',
  risk_control: '',
  medication: '',
  remark: '',
})

const followStatusOptions = [
  { label: '已随访', value: 'followed' },
  { label: '未随访', value: 'unfollowed' },
]
const survivalOptions = [
  { label: '存活', value: 'alive' },
  { label: '死亡', value: 'dead' },
  { label: '未知', value: 'unknown' },
]

onLoad(async (query) => {
  followId.value = Number(query?.id || 0)
  if (!followId.value) return
  loading.value = true
  try {
    const res = await DoctorAPI.followupList({ page_no: 1, page_size: 100 })
    const item = res.items.find((f) => f.id === followId.value)
    if (item) {
      detail.value = item
      form.value = {
        follow_date: item.follow_date || '',
        follow_status: item.follow_status || 'followed',
        survival_status: item.survival_status || 'alive',
        risk_control: item.risk_control || '',
        medication: item.medication || '',
        remark: item.remark || '',
      }
    }
  }
  finally {
    loading.value = false
  }
})

const isSubmitted = () => detail.value?.status === 'submitted'

async function handleSubmit() {
  if (!form.value.follow_date) {
    uni.showToast({ title: '请选择随访日期', icon: 'none' })
    return
  }
  submitting.value = true
  try {
    await DoctorAPI.followupSubmit(followId.value, { ...form.value })
    uni.showToast({ title: '随访已提交', icon: 'success' })
    setTimeout(() => safeBack(), 700)
  }
  catch { /* toast */ }
  finally { submitting.value = false }
}
</script>

<template>
  <view class="fd-page">
    <view v-if="loading" class="loading">加载中...</view>
    <template v-else-if="detail">
      <!-- 概要 -->
      <view class="summary">
        <text class="sum-name">{{ detail.patient_name || '-' }}</text>
        <text class="sum-case">{{ detail.case_no }} · {{ detail.plan_month }} 月随访</text>
        <text class="sum-due">应随访日期：{{ detail.due_date || '-' }}</text>
      </view>

      <!-- 表单 -->
      <view class="card">
        <view class="field">
          <text class="label">随访日期 <text class="req">*</text></text>
          <picker mode="date" :value="form.follow_date" @change="(e) => { form.follow_date = e.detail.value }">
            <view class="input" :class="{ empty: !form.follow_date }">{{ form.follow_date || '请选择随访日期' }}</view>
          </picker>
        </view>

        <view class="field">
          <text class="label">随访状态</text>
          <view class="option-row">
            <view
              v-for="o in followStatusOptions"
              :key="o.value"
              class="option"
              :class="{ active: form.follow_status === o.value }"
              @click="form.follow_status = o.value"
            >{{ o.label }}</view>
          </view>
        </view>

        <view class="field">
          <text class="label">生存状态</text>
          <view class="option-row">
            <view
              v-for="o in survivalOptions"
              :key="o.value"
              class="option"
              :class="{ active: form.survival_status === o.value }"
              @click="form.survival_status = o.value"
            >{{ o.label }}</view>
          </view>
        </view>

        <view class="field">
          <text class="label">危险因素控制</text>
          <textarea v-model="form.risk_control" class="textarea" placeholder="如：戒烟、血压控制情况" placeholder-class="ph" />
        </view>

        <view class="field">
          <text class="label">用药情况</text>
          <textarea v-model="form.medication" class="textarea" placeholder="出院后用药及依从性" placeholder-class="ph" />
        </view>

        <view class="field">
          <text class="label">备注</text>
          <textarea v-model="form.remark" class="textarea" placeholder="其他随访记录" placeholder-class="ph" />
        </view>
      </view>

      <button v-if="!isSubmitted()" class="submit-btn" :disabled="submitting" @click="handleSubmit">
        {{ submitting ? '提交中...' : '提交随访' }}
      </button>
      <view v-else class="submitted-tip">该随访已提交，不可重复提交</view>
    </template>
    <view v-else class="loading">随访记录不存在</view>
  </view>
</template>

<style lang="scss" scoped>
.fd-page { min-height: 100vh; background: #f3f4f6; padding: 24rpx 32rpx 60rpx; }
.loading { text-align: center; padding-top: 200rpx; color: #9ca3af; }

.summary {
  padding: 32rpx;
  border-radius: 24rpx;
  background: linear-gradient(135deg, #10b981, #0ea5e9);
  margin-bottom: 24rpx;
  display: flex;
  flex-direction: column;
}
.sum-name { font-size: 38rpx; font-weight: 700; color: #ffffff; }
.sum-case { margin-top: 10rpx; font-size: 24rpx; color: rgba(255, 255, 255, 0.85); }
.sum-due { margin-top: 8rpx; font-size: 26rpx; color: #ffffff; }

.card { padding: 32rpx; border-radius: 24rpx; background: #ffffff; }
.field { margin-bottom: 28rpx; }
.label { display: block; font-size: 26rpx; color: #4b5563; margin-bottom: 12rpx; }
.req { color: #ef4444; }
.input {
  height: 88rpx;
  line-height: 88rpx;
  padding: 0 24rpx;
  border-radius: 16rpx;
  background: #f3f4f6;
  font-size: 30rpx;
  color: #1f2937;
}
.input.empty { color: #9ca3af; }
.textarea {
  width: 100%;
  min-height: 140rpx;
  padding: 20rpx 24rpx;
  border-radius: 16rpx;
  background: #f3f4f6;
  font-size: 28rpx;
  box-sizing: border-box;
}
.ph { color: #9ca3af; }

.option-row { display: flex; gap: 16rpx; flex-wrap: wrap; }
.option {
  padding: 14rpx 32rpx;
  border-radius: 16rpx;
  background: #f3f4f6;
  font-size: 26rpx;
  color: #4b5563;
}
.option.active { background: #10b981; color: #ffffff; }

.submit-btn {
  margin-top: 32rpx;
  height: 92rpx;
  line-height: 92rpx;
  border-radius: 20rpx;
  background: linear-gradient(135deg, #10b981, #0ea5e9);
  color: #ffffff;
  font-size: 30rpx;
  font-weight: 600;
}
.submit-btn::after { border: none; }
.submitted-tip { text-align: center; margin-top: 40rpx; font-size: 26rpx; color: #9ca3af; }
</style>
