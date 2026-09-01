<!-- 病例详情：基础信息 + 动态字段 + 审核反馈（只读） -->
<script setup lang="ts">
import { getApiBaseUrl } from '@/http'
import { safeBack } from '@/utils/back'
import { computed, ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import DoctorAPI, { type CaseDetailData, type FieldDef } from '@/api/module_cpx/doctor'

definePage({
  name: 'case-detail',
  style: { navigationStyle: 'custom' },
})

const statusBarHeight = uni.getSystemInfoSync().statusBarHeight || 0

function goBack() {
  safeBack()
}

const loading = ref(false)
const detail = ref<CaseDetailData | null>(null)
const fieldDict = ref<Record<string, FieldDef>>({})

const statusLabel = (s?: string) => {
  if (s === 'draft') return '草稿'
  if (s === 'submitted') return '待审核'
  if (s === 'approved') return '审核通过'
  if (s === 'rejected') return '审核驳回'
  return s ?? '-'
}
const statusColor = (s?: string) => {
  if (s === 'draft') return '#9ca3af'
  if (s === 'submitted') return '#f59e0b'
  if (s === 'approved') return '#10b981'
  if (s === 'rejected') return '#ef4444'
  return '#6b7280'
}

/** 按字段字典渲染 form_data 的非空字段（三端统一展示） */
const filledData = computed(() => {
  const fd = detail.value?.form_data || {}
  const rows: { name: string; value: string; type: string }[] = []
  Object.keys(fd).forEach((code) => {
    const v = fd[code]
    if (v === undefined || v === null || v === '') return
    const def = fieldDict.value[code]
    const name = def?.name || code
    let val = String(v)
    // select 选项转 label
    if (def?.type === 'select' && def.options) {
      const opt = def.options.find((o) => o.value === String(v))
      if (opt) val = opt.label
    }
    rows.push({ name, value: val, type: def?.type || 'text' })
  })
  return rows
})

function imgSrc(url: string) {
  const s = String(url || '')
  if (!s) return ''
  if (s.startsWith('http'))
    return s
  return `${getApiBaseUrl()}${s}`
}

function previewImg(url: string) {
  uni.previewImage({ urls: [imgSrc(url)] })
}

function goEdit() {
  if (!detail.value) return
  uni.navigateTo({ url: `/pages/case/fill?id=${detail.value.id}` })
}

onLoad(async (query) => {
  const id = Number(query?.id || 0)
  if (!id) return
  loading.value = true
  try {
    const [d, detailData] = await Promise.all([
      DoctorAPI.fieldDict(),
      DoctorAPI.caseDetail(id),
    ])
    const map: Record<string, FieldDef> = {}
    d.fields.forEach((f) => { map[f.code] = f })
    fieldDict.value = map
    detail.value = detailData
  }
  catch {
    // http 层 toast
  }
  finally {
    loading.value = false
  }
})
</script>

<template>
  <view class="detail-page">
    <!-- 自定义蓝色导航栏 -->
    <view class="nav-bar" :style="{ paddingTop: `${statusBarHeight}px` }">
      <view class="nav-back" @click="goBack">‹</view>
      <text class="nav-title">病例详情</text>
      <view class="nav-right" />
    </view>

    <view class="page-body">
    <view v-if="loading" class="loading">加载中...</view>

    <template v-else-if="detail">
      <!-- 概要 -->
      <view class="summary">
        <view class="summary-top">
          <text class="summary-name">{{ detail.patient_name || '-' }}</text>
          <text class="summary-status" :style="{ color: statusColor(detail.status) }">{{ statusLabel(detail.status) }}</text>
        </view>
        <text class="summary-no">{{ detail.case_no }}</text>
        <text class="summary-meta">{{ detail.hospital_name }} · {{ detail.create_time }}</text>
      </view>

      <!-- 基础信息 -->
      <view class="card">
        <text class="card-title">患者信息</text>
        <view class="kv-row">
          <text class="kv-label">姓名</text>
          <text class="kv-value">{{ detail.patient_name || '-' }}</text>
        </view>
        <view class="kv-row">
          <text class="kv-label">性别</text>
          <text class="kv-value">{{ detail.gender || '-' }}</text>
        </view>
        <view class="kv-row">
          <text class="kv-label">年龄</text>
          <text class="kv-value">{{ detail.age != null ? `${detail.age} 岁` : '-' }}</text>
        </view>
        <view class="kv-row">
          <text class="kv-label">联系电话</text>
          <text class="kv-value">{{ detail.phone || '-' }}</text>
        </view>
        <view class="kv-row">
          <text class="kv-label">填报模板</text>
          <text class="kv-value">{{ detail.template_name || '-' }}</text>
        </view>
      </view>

      <!-- 填报数据 -->
      <view class="card">
        <text class="card-title">填报数据</text>
        <view v-if="filledData.length">
          <view v-for="(row, idx) in filledData" :key="idx" class="kv-row">
            <text class="kv-label">{{ row.name }}</text>
            <image v-if="row.type === 'image'" :src="imgSrc(row.value)" class="kv-img" mode="aspectFit" @click="previewImg(row.value)" />
            <text v-else class="kv-value">{{ row.value }}</text>
          </view>
        </view>
        <text v-else class="empty-text">暂无填报数据</text>
      </view>

      <!-- 审核反馈 -->
      <view class="card">
        <text class="card-title">审核反馈</text>
        <view v-if="detail.audit_records.length">
          <view v-for="a in detail.audit_records" :key="a.id" class="audit-item">
            <view class="audit-head">
              <text class="audit-result" :style="{ color: a.audit_result === 'pass' ? '#10b981' : '#ef4444' }">
                {{ a.audit_result === 'pass' ? '通过' : '驳回' }}
              </text>
              <text class="audit-time">{{ a.audit_time }}</text>
            </view>
            <text class="audit-auditor">审核员：{{ a.auditor_name || '-' }}</text>
            <text class="audit-comment">意见：{{ a.audit_comment || '（无）' }}</text>
          </view>
        </view>
        <text v-else class="empty-text">暂无审核记录</text>
      </view>

      <!-- 操作 -->
      <button
        v-if="detail.status === 'draft' || detail.status === 'rejected'"
        class="edit-btn"
        @click="goEdit"
      >{{ detail.status === 'rejected' ? '修改并重新提交' : '继续填报' }}</button>
    </template>

    <view v-else class="loading">病例不存在</view>
    </view>
  </view>
</template>

<style lang="scss" scoped>
.detail-page {
  min-height: 100vh;
  background: #ffffff;
  padding-bottom: 80rpx;
}

/* ── 自定义蓝色导航栏 ── */
.nav-bar {
  display: flex;
  align-items: center;
  height: 88rpx;
  padding-left: 24rpx;
  padding-right: 24rpx;
  background: linear-gradient(135deg, #2563eb, #1d4ed8);
}
.nav-back {
  width: 64rpx;
  height: 64rpx;
  line-height: 56rpx;
  font-size: 52rpx;
  color: #ffffff;
}
.nav-title {
  flex: 1;
  text-align: center;
  font-size: 34rpx;
  font-weight: 600;
  color: #ffffff;
  letter-spacing: 2rpx;
}
.nav-right { width: 120rpx; }

.page-body { padding: 24rpx 32rpx 0; }

.loading {
  text-align: center;
  padding-top: 200rpx;
  color: #9ca3af;
}

.summary {
  padding: 32rpx;
  border-radius: 24rpx;
  background: linear-gradient(135deg, #2563eb, #1d4ed8);
  margin-bottom: 24rpx;
}
.summary-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.summary-name {
  font-size: 38rpx;
  font-weight: 700;
  color: #ffffff;
}
.summary-status {
  font-size: 28rpx;
  font-weight: 600;
  padding: 8rpx 20rpx;
  border-radius: 28rpx;
  background: rgba(255, 255, 255, 0.92);
}
.summary-no {
  display: block;
  margin-top: 14rpx;
  font-size: 24rpx;
  color: rgba(255, 255, 255, 0.85);
}
.summary-meta {
  display: block;
  margin-top: 8rpx;
  font-size: 22rpx;
  color: rgba(255, 255, 255, 0.8);
}

.card {
  margin-bottom: 24rpx;
  padding: 28rpx 32rpx;
  border-radius: 24rpx;
  background: #ffffff;
  border: 2rpx solid #f0f1f3;
}
.card-title {
  display: block;
  font-size: 30rpx;
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 20rpx;
}
.kv-row {
  display: flex;
  padding: 14rpx 0;
  border-bottom: 2rpx solid #f3f4f6;
}
.kv-label {
  width: 200rpx;
  font-size: 26rpx;
  color: #9ca3af;
}
.kv-value {
  flex: 1;
  font-size: 28rpx;
  color: #1f2937;
  word-break: break-all;
}
.kv-img {
  flex: 1;
  max-width: 300rpx;
  height: 160rpx;
  border-radius: 12rpx;
  background: #f3f4f6;
}

.audit-item {
  padding: 20rpx;
  border-radius: 16rpx;
  background: #f9fafb;
  margin-bottom: 16rpx;
}
.audit-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.audit-result {
  font-size: 28rpx;
  font-weight: 600;
}
.audit-time {
  font-size: 22rpx;
  color: #9ca3af;
}
.audit-auditor {
  display: block;
  margin-top: 12rpx;
  font-size: 24rpx;
  color: #6b7280;
}
.audit-comment {
  display: block;
  margin-top: 8rpx;
  font-size: 26rpx;
  color: #4b5563;
}

.empty-text {
  display: block;
  text-align: center;
  padding: 40rpx 0;
  font-size: 26rpx;
  color: #c0c4cc;
}

.edit-btn {
  height: 100rpx;
  line-height: 100rpx;
  border-radius: 24rpx;
  background: #1d4ed8;
  color: #ffffff;
  font-size: 32rpx;
  font-weight: 600;
  letter-spacing: 2rpx;
}
.edit-btn::after {
  border: none;
}
</style>
