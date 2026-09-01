<!-- 三会 PPT 预览：封面/本院指标/时间指标/问题病历/改进意见 + 下载 -->
<script setup lang="ts">
import { getApiBaseUrl } from '@/http'
import { ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import DoctorAPI, { type MeetingStat } from '@/api/module_cpx/doctor'

definePage({
  name: 'meeting-preview',
  style: { navigationBarTitleText: '会议预览' },
})

const BASE_URL = getApiBaseUrl()
const loading = ref(false)
const record = ref<{ id: number; title: string; meeting_type: string; start_date?: string; end_date?: string; file_url?: string; create_time?: string; stat: MeetingStat } | null>(null)

const statusLabel: Record<string, string> = { draft: '填报中', submitted: '待审核', approved: '已通过', rejected: '驳回' }

onLoad(async (query) => {
  const id = Number(query?.id || 0)
  if (!id) return
  loading.value = true
  try {
    record.value = await DoctorAPI.meetingPreview(id)
  }
  catch { /* toast */ }
  finally { loading.value = false }
})

function handleDownload() {
  if (!record.value?.file_url) return
  const url = `${BASE_URL}${record.value.file_url}`
  // #ifdef H5
  window.open(url, '_blank')
  // #endif
  // #ifndef H5
  uni.showLoading({ title: '下载中...' })
  uni.downloadFile({
    url,
    success: (res) => {
      uni.hideLoading()
      if (res.statusCode === 200)
        uni.openDocument({ filePath: res.tempFilePath, showMenu: true, fail: () => uni.showToast({ title: '已下载，请在文件目录查看', icon: 'none' }) })
      else
        uni.showToast({ title: '下载失败', icon: 'none' })
    },
    fail: () => { uni.hideLoading(); uni.showToast({ title: '下载失败', icon: 'none' }) },
  })
  // #endif
}
</script>

<template>
  <view class="pv-page">
    <view v-if="loading" class="loading">加载中...</view>
    <template v-else-if="record">
      <!-- 封面 -->
      <view class="cover">
        <text class="cover-title">{{ record.title }}</text>
        <text class="cover-range">统计区间：{{ record.start_date || '全部' }} 至 {{ record.end_date || '至今' }}</text>
        <text class="cover-time">生成时间：{{ record.create_time }}</text>
        <view class="cover-download" @click="handleDownload">⬇ 下载 PPT</view>
        <text class="cover-hint">手机端点击后可直接保存/转发；电脑浏览器点击将直接打开 PPT 文件</text>
      </view>

      <!-- 本院指标 -->
      <view class="card">
        <text class="card-title">一、本院指标</text>
        <view class="kv"><text class="kv-l">统计病例</text><text class="kv-v">{{ record.stat.total }} 例</text></view>
        <view class="kv"><text class="kv-l">填报中 / 待审核</text><text class="kv-v">{{ record.stat.status_dist.draft || 0 }} / {{ record.stat.status_dist.submitted || 0 }} 例</text></view>
        <view class="kv"><text class="kv-l">已通过 / 驳回</text><text class="kv-v">{{ record.stat.status_dist.approved || 0 }} / {{ record.stat.status_dist.rejected || 0 }} 例</text></view>
        <view class="kv"><text class="kv-l">诊断分布</text><text class="kv-v">{{ Object.entries(record.stat.diagnose_dist).map(([k, v]) => `${k} ${v}`).join('、') || '暂无' }}</text></view>
      </view>

      <!-- 时间指标 -->
      <view class="card">
        <text class="card-title">二、质控时间指标</text>
        <view v-for="m in record.stat.metrics" :key="m.key" class="metric">
          <view class="metric-head">
            <text class="metric-name">{{ m.name }}</text>
            <text class="metric-rate" :style="{ color: (m.rate ?? 0) >= 80 ? '#10b981' : '#ef4444' }">{{ m.rate != null ? `${m.rate}%` : '无数据' }}</text>
          </view>
          <text class="metric-detail">{{ m.pass }}/{{ m.total }} 例达标</text>
        </view>
      </view>

      <!-- 问题病历 -->
      <view class="card">
        <text class="card-title">三、问题病历</text>
        <view v-if="record.stat.problems.length">
          <view v-for="(p, i) in record.stat.problems" :key="i" class="prob">
            <text class="prob-text">{{ p.case_no }} · {{ p.patient_name }} · {{ p.diagnose_type || '-' }} · {{ p.status === 'rejected' ? '驳回' : '待审核' }}</text>
          </view>
        </view>
        <text v-else class="empty">区间内无问题病历</text>
      </view>

      <!-- 改进意见 -->
      <view class="card">
        <text class="card-title">四、改进意见</text>
        <view v-for="(s, i) in record.stat.suggestions" :key="i" class="suggest">
          <text class="suggest-dot">·</text>
          <text class="suggest-text">{{ s }}</text>
        </view>
      </view>
    </template>
    <view v-else class="loading">记录不存在</view>
  </view>
</template>

<style lang="scss" scoped>
.pv-page { min-height: 100vh; background: #f3f4f6; padding: 24rpx 32rpx 60rpx; }
.loading { text-align: center; padding-top: 200rpx; color: #9ca3af; }

.cover {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 60rpx 32rpx;
  border-radius: 24rpx;
  background: linear-gradient(135deg, #8b5cf6, #6366f1);
  margin-bottom: 24rpx;
}
.cover-title { font-size: 40rpx; font-weight: 700; color: #ffffff; }
.cover-range { margin-top: 16rpx; font-size: 26rpx; color: rgba(255, 255, 255, 0.85); }
.cover-time { margin-top: 8rpx; font-size: 22rpx; color: rgba(255, 255, 255, 0.75); }
.cover-download {
  margin-top: 28rpx;
  padding: 16rpx 48rpx;
  border-radius: 36rpx;
  background: #ffffff;
  color: #7c3aed;
  font-size: 28rpx;
  font-weight: 600;
}
.cover-hint { margin-top: 14rpx; font-size: 22rpx; color: rgba(255, 255, 255, 0.85); text-align: center; }

.card { margin-bottom: 24rpx; padding: 32rpx; border-radius: 24rpx; background: #ffffff; }
.card-title { display: block; font-size: 30rpx; font-weight: 600; color: #1f2937; margin-bottom: 20rpx; }
.kv { display: flex; justify-content: space-between; padding: 12rpx 0; border-bottom: 2rpx solid #f3f4f6; }
.kv-l { font-size: 26rpx; color: #9ca3af; }
.kv-v { font-size: 26rpx; color: #1f2937; }

.metric { padding: 16rpx; border-radius: 14rpx; background: #f9fafb; margin-bottom: 14rpx; }
.metric-head { display: flex; align-items: center; justify-content: space-between; }
.metric-name { font-size: 26rpx; font-weight: 600; color: #1f2937; }
.metric-rate { font-size: 28rpx; font-weight: 700; }
.metric-detail { display: block; margin-top: 6rpx; font-size: 22rpx; color: #9ca3af; }

.prob { padding: 10rpx 0; }
.prob-text { font-size: 26rpx; color: #4b5563; }

.suggest { display: flex; gap: 12rpx; margin-bottom: 14rpx; }
.suggest-dot { color: #7c3aed; }
.suggest-text { flex: 1; font-size: 26rpx; color: #4b5563; line-height: 1.6; }

.empty { display: block; text-align: center; padding: 30rpx 0; color: #c0c4cc; font-size: 26rpx; }
</style>
