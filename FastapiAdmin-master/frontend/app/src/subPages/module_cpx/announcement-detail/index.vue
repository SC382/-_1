<!-- 公告详情页：从首页公告 banner 点击进入 -->
<script setup lang="ts">
import { ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { AnnouncementAPI, type AnnouncementItem } from '@/api/module_cpx/announcement'

definePage({ name: 'announcement-detail', style: { navigationBarTitleText: '公告详情' } })

const toast = useToast()
const detail = ref<AnnouncementItem | null>(null)
const loading = ref(true)

const TYPE_LABEL: Record<string, string> = {
  system: '系统公告',
  version: '版本更新',
  activity: '活动通知',
  notice: '通知',
}

onLoad((options) => {
  const id = Number(options?.id)
  if (!id) {
    toast.show({ msg: '缺少公告 ID' })
    uni.navigateBack()
    return
  }
  fetchDetail(id)
})

async function fetchDetail(id: number) {
  loading.value = true
  try {
    detail.value = await AnnouncementAPI.detail(id)
  }
  catch {
    // http 层已 toast
    setTimeout(() => uni.navigateBack(), 800)
  }
  finally {
    loading.value = false
  }
}

function fmtTime(t?: string | null) {
  if (!t) return ''
  return t.replace('T', ' ').slice(0, 16)
}
</script>

<template>
  <view class="announcement-detail">
    <!-- 加载态 -->
    <view v-if="loading" class="loading-box">
      <view class="loading-dot" />
      <text class="loading-text">加载中...</text>
    </view>

    <template v-else-if="detail">
      <!-- 封面图（可选） -->
      <image
        v-if="detail.cover"
        class="detail-cover"
        :src="detail.cover"
        mode="aspectFill"
      />

      <!-- 标题区 -->
      <view class="detail-header">
        <text class="detail-type">{{ TYPE_LABEL[detail.type || 'notice'] || '通知' }}</text>
        <text class="detail-title">{{ detail.title }}</text>
        <text v-if="detail.subtitle" class="detail-subtitle">{{ detail.subtitle }}</text>
        <text class="detail-time">{{ fmtTime(detail.published_at || detail.create_time) }}</text>
      </view>

      <!-- 正文内容（支持 HTML / 换行文本） -->
      <view class="detail-content">
        <rich-text v-if="detail.content && /<[a-z]+/i.test(detail.content)" :nodes="detail.content" />
        <template v-else>
          <text class="content-line" v-for="(line, i) in (detail.content || '暂无内容').split('\n')" :key="i">{{ line }}</text>
        </template>
      </view>
    </template>

    <view v-else class="empty-box">
      <text class="empty-text">公告不存在或已下线</text>
    </view>
  </view>
</template>

<style lang="scss" scoped>
.announcement-detail {
  min-height: 100vh;
  background: #f3f4f6;
  padding-bottom: 48rpx;
}
.loading-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding-top: 200rpx;
}
.loading-dot {
  width: 48rpx;
  height: 48rpx;
  border-radius: 50%;
  border: 6rpx solid #e5e7eb;
  border-top-color: #2563eb;
  animation: spin 0.8s linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}
.loading-text {
  margin-top: 20rpx;
  font-size: 26rpx;
  color: #9ca3af;
}
.detail-cover {
  width: 100%;
  height: 360rpx;
  display: block;
}
.detail-header {
  margin: 24rpx;
  padding: 32rpx;
  border-radius: 24rpx;
  background: #ffffff;
  box-shadow: 0 8rpx 24rpx rgba(15, 23, 42, 0.06);
}
.detail-type {
  display: inline-block;
  padding: 4rpx 16rpx;
  border-radius: 8rpx;
  background: #eff6ff;
  color: #2563eb;
  font-size: 22rpx;
  font-weight: 600;
}
.detail-title {
  display: block;
  margin-top: 16rpx;
  font-size: 38rpx;
  font-weight: 700;
  color: #1f2937;
  line-height: 1.4;
}
.detail-subtitle {
  display: block;
  margin-top: 12rpx;
  font-size: 26rpx;
  color: #6b7280;
}
.detail-time {
  display: block;
  margin-top: 16rpx;
  font-size: 24rpx;
  color: #9ca3af;
}
.detail-content {
  margin: 0 24rpx;
  padding: 32rpx;
  border-radius: 24rpx;
  background: #ffffff;
  box-shadow: 0 8rpx 24rpx rgba(15, 23, 42, 0.06);
  font-size: 28rpx;
  color: #374151;
  line-height: 1.8;
  word-break: break-all;
}
.content-line {
  display: block;
}
.empty-box {
  display: flex;
  justify-content: center;
  padding-top: 240rpx;
}
.empty-text {
  font-size: 28rpx;
  color: #9ca3af;
}
</style>
