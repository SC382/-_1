<!-- 胸痛学院：内容详情（在线查看 / 下载） -->
<script setup lang="ts">
import { getApiBaseUrl } from '@/http'
import { computed, ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import AcademyAPI, { type AcademyItem } from '@/api/module_cpx/academy'

definePage({
  name: 'academy-detail',
  style: { navigationBarTitleText: '内容详情' },
})

const BASE_URL = getApiBaseUrl()
const id = ref(0)
const loading = ref(false)
const item = ref<AcademyItem | null>(null)

const TYPE_META: Record<string, { label: string; icon: string; color: string }> = {
  video: { label: '视频', icon: '🎬', color: '#ef4444' },
  ppt: { label: 'PPT', icon: '📊', color: '#f59e0b' },
  doc: { label: '文档', icon: '📄', color: '#2563eb' },
  pdf: { label: 'PDF', icon: '📕', color: '#10b981' },
  other: { label: '文件', icon: '📁', color: '#6b7280' },
}
const meta = computed(() => TYPE_META[item.value?.content_type || 'other'] ?? TYPE_META.other)
/** 可访问的绝对 URL */
const fileUrl = computed(() => {
  const p = item.value?.file_path || ''
  return p.startsWith('http') ? p : `${BASE_URL}${p}`
})
function fmtSize(n?: number | null) {
  if (!n) return ''
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${(n / 1024 / 1024).toFixed(1)} MB`
}

onLoad(async (query) => {
  id.value = Number(query?.id || 0)
  if (!id.value) return
  loading.value = true
  try {
    item.value = await AcademyAPI.detail(id.value)
  }
  catch {
    // http 层已 toast
  }
  finally {
    loading.value = false
  }
})

/** 在线预览：H5 新窗口打开；App/小程序下载后 openDocument */
function preview() {
  if (!item.value) return
  // #ifdef H5
  window.open(fileUrl.value, '_blank')
  // #endif
  // #ifndef H5
  uni.downloadFile({
    url: fileUrl.value,
    success: (res) => {
      if (res.statusCode === 200) {
        uni.openDocument({
          filePath: res.tempFilePath,
          showMenu: true,
          fail: () => uni.showToast({ title: '该格式暂不支持在线预览，请下载后查看', icon: 'none' }),
        })
      }
    },
    fail: () => uni.showToast({ title: '预览失败', icon: 'none' }),
  })
  // #endif
}

/** 下载文件 */
function download() {
  if (!item.value) return
  // #ifdef H5
  const a = document.createElement('a')
  a.href = fileUrl.value
  a.download = item.value.file_name || 'download'
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  uni.showToast({ title: '开始下载', icon: 'none' })
  // #endif
  // #ifndef H5
  uni.downloadFile({
    url: fileUrl.value,
    success: (res) => {
      if (res.statusCode === 200)
        uni.showToast({ title: '下载成功', icon: 'success' })
      else
        uni.showToast({ title: '下载失败', icon: 'none' })
    },
    fail: () => uni.showToast({ title: '下载失败', icon: 'none' }),
  })
  // #endif
}
</script>

<template>
  <view class="detail-page">
    <view v-if="loading" class="loading">加载中...</view>
    <template v-else-if="item">
      <!-- 头部信息 -->
      <view class="head-card">
        <view class="head-icon" :style="{ background: meta.color }">
          <text>{{ meta.icon }}</text>
        </view>
        <view class="head-main">
          <text class="head-title">{{ item.title }}</text>
          <view class="head-tags">
            <text class="tag type" :style="{ color: meta.color, background: meta.color + '1a' }">{{ meta.label }}</text>
            <text v-if="item.category" class="tag cat">{{ item.category }}</text>
          </view>
          <view class="head-meta">
            <text>浏览 {{ item.view_count || 0 }}</text>
            <text>下载 {{ item.download_count || 0 }}</text>
            <text v-if="item.file_size">{{ fmtSize(item.file_size) }}</text>
          </view>
        </view>
      </view>

      <!-- 视频：内联播放 -->
      <view v-if="item.content_type === 'video'" class="video-box">
        <video
          :src="fileUrl"
          class="video-player"
          controls
          :poster="item.cover_path || ''"
        />
      </view>

      <!-- 简介 -->
      <view v-if="item.summary" class="summary-card">
        <text class="summary-title">简介</text>
        <text class="summary-text">{{ item.summary }}</text>
      </view>

      <!-- 文件名 -->
      <view v-if="item.file_name" class="file-card">
        <text class="file-label">文件</text>
        <text class="file-name">{{ item.file_name }}</text>
      </view>

      <!-- 操作 -->
      <view class="ops">
        <button class="op-btn op-download" @click="download">下载文件</button>
        <button v-if="item.content_type !== 'video'" class="op-btn op-preview" @click="preview">在线预览</button>
      </view>
      <view class="ops-tip">提示：H5 端在线预览需在浏览器中打开；下载后可离线查看</view>
    </template>

    <view v-else class="loading">内容不存在或已下架</view>
  </view>
</template>

<style lang="scss" scoped>
.detail-page {
  min-height: 100vh;
  background: #f3f4f6;
  padding: 24rpx 32rpx 60rpx;
}
.loading { text-align: center; padding-top: 200rpx; color: #9ca3af; }

.head-card {
  display: flex;
  gap: 24rpx;
  padding: 32rpx;
  border-radius: 24rpx;
  background: #ffffff;
}
.head-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 110rpx;
  height: 110rpx;
  border-radius: 24rpx;
  flex-shrink: 0;
  font-size: 52rpx;
}
.head-main { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 12rpx; }
.head-title { font-size: 34rpx; font-weight: 700; color: #1f2937; line-height: 1.4; }
.head-tags { display: flex; gap: 12rpx; }
.tag { font-size: 22rpx; padding: 4rpx 16rpx; border-radius: 12rpx; }
.tag.type { font-weight: 500; }
.tag.cat { color: #6b7280; background: #f3f4f6; }
.head-meta { display: flex; gap: 24rpx; font-size: 22rpx; color: #9ca3af; }

.video-box {
  margin-top: 24rpx;
  padding: 24rpx;
  border-radius: 24rpx;
  background: #ffffff;
}
.video-player { width: 100%; height: 420rpx; border-radius: 16rpx; background: #000; }

.summary-card, .file-card {
  margin-top: 24rpx;
  padding: 28rpx 32rpx;
  border-radius: 20rpx;
  background: #ffffff;
  display: flex;
  flex-direction: column;
  gap: 12rpx;
}
.summary-title, .file-label { font-size: 24rpx; color: #9ca3af; }
.summary-text { font-size: 28rpx; color: #374151; line-height: 1.7; }
.file-name { font-size: 26rpx; color: #2563eb; word-break: break-all; }

.ops {
  display: flex;
  gap: 24rpx;
  margin-top: 40rpx;
}
.op-btn {
  flex: 1;
  height: 96rpx;
  line-height: 96rpx;
  border-radius: 24rpx;
  font-size: 30rpx;
  font-weight: 600;
  border: none;
}
.op-download { background: linear-gradient(135deg, #2563eb, #38bdf8); color: #ffffff; }
.op-preview { background: #ffffff; color: #2563eb; border: 2rpx solid #2563eb; }
.ops-tip { margin-top: 20rpx; text-align: center; font-size: 22rpx; color: #c0c4cc; }
</style>
