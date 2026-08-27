<!-- 胸痛学院：已发布学习资源列表（在线查看 / 下载入口） -->
<script setup lang="ts">
import { reactive, ref } from 'vue'
import { onPullDownRefresh, onShow } from '@dcloudio/uni-app'
import AcademyAPI, { type AcademyItem } from '@/api/module_cpx/academy'

definePage({
  name: 'academy',
  style: { navigationBarTitleText: '胸痛学院' },
})

const loading = ref(false)
const list = ref<AcademyItem[]>([])
const total = ref(0)
const query = reactive({ page_no: 1, page_size: 20, content_type: '' })

const TYPE_TABS = [
  { label: '全部', value: '' },
  { label: '视频', value: 'video' },
  { label: 'PPT', value: 'ppt' },
  { label: '文档', value: 'doc' },
  { label: 'PDF', value: 'pdf' },
  { label: '其他', value: 'other' },
]

const TYPE_META: Record<string, { label: string; icon: string; color: string }> = {
  video: { label: '视频', icon: '🎬', color: '#ef4444' },
  ppt: { label: 'PPT', icon: '📊', color: '#f59e0b' },
  doc: { label: '文档', icon: '📄', color: '#2563eb' },
  pdf: { label: 'PDF', icon: '📕', color: '#10b981' },
  other: { label: '文件', icon: '📁', color: '#6b7280' },
}

function typeLabel(t?: string) {
  return TYPE_META[t || 'other']?.label ?? '文件'
}
function typeIcon(t?: string) {
  return TYPE_META[t || 'other']?.icon ?? '📁'
}
function typeColor(t?: string) {
  return TYPE_META[t || 'other']?.color ?? '#6b7280'
}
function fmtSize(n?: number | null) {
  if (!n) return ''
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${(n / 1024 / 1024).toFixed(1)} MB`
}

async function fetchData() {
  loading.value = true
  try {
    const res = await AcademyAPI.list({
      page_no: query.page_no,
      page_size: query.page_size,
      content_type: query.content_type || undefined,
    })
    list.value = query.page_no === 1 ? res.items : [...list.value, ...res.items]
    total.value = res.total
  }
  catch {
    // http 层已 toast
  }
  finally {
    loading.value = false
  }
}

function switchType(v: string) {
  query.content_type = v
  query.page_no = 1
  fetchData()
}
function loadMore() {
  if (total.value > query.page_no * query.page_size) {
    query.page_no++
    fetchData()
  }
}
function onPullDownRefresh() {
  query.page_no = 1
  fetchData()
  uni.stopPullDownRefresh()
}
function goDetail(item: AcademyItem) {
  uni.navigateTo({ url: `/pages/academy/detail?id=${item.id}` })
}

onShow(fetchData)
</script>

<template>
  <view class="academy-page">
    <!-- 类型筛选 -->
    <scroll-view scroll-x class="type-bar">
      <view
        v-for="t in TYPE_TABS"
        :key="t.value"
        class="type-item"
        :class="{ active: query.content_type === t.value }"
        @click="switchType(t.value)"
      >
        {{ t.label }}
      </view>
    </scroll-view>

    <!-- 列表 -->
    <view v-if="list.length" class="academy-list">
      <view
        v-for="c in list"
        :key="c.id"
        class="academy-card"
        @click="goDetail(c)"
      >
        <view class="card-icon" :style="{ background: typeColor(c.content_type) }">
          <text>{{ typeIcon(c.content_type) }}</text>
        </view>
        <view class="card-main">
          <text class="card-title">{{ c.title }}</text>
          <view class="card-meta">
            <text class="card-cat">{{ c.category || typeLabel(c.content_type) }}</text>
            <text v-if="c.file_name" class="card-file">{{ c.file_name }}</text>
          </view>
          <view class="card-foot">
            <text class="card-size">{{ fmtSize(c.file_size) }}</text>
            <text class="card-view">浏览 {{ c.view_count || 0 }}</text>
            <text class="card-view">下载 {{ c.download_count || 0 }}</text>
          </view>
        </view>
        <text class="card-arrow">›</text>
      </view>
      <view v-if="total > query.page_no * query.page_size" class="load-more" @click="loadMore">
        加载更多
      </view>
    </view>

    <view v-else-if="!loading" class="empty">
      <text class="empty-icon">📚</text>
      <text class="empty-text">暂无内容</text>
    </view>
  </view>
</template>

<style lang="scss" scoped>
.academy-page {
  min-height: 100vh;
  background: #f3f4f6;
  padding-bottom: 40rpx;
}

.type-bar {
  white-space: nowrap;
  background: #ffffff;
  padding: 20rpx 24rpx;
  border-bottom: 2rpx solid #f3f4f6;
}
.type-item {
  display: inline-block;
  padding: 12rpx 30rpx;
  margin-right: 12rpx;
  border-radius: 32rpx;
  font-size: 26rpx;
  color: #6b7280;
  background: #f3f4f6;
}
.type-item.active { background: #2563eb; color: #ffffff; }

.academy-list {
  display: flex;
  flex-direction: column;
  gap: 20rpx;
  padding: 24rpx 32rpx;
}
.academy-card {
  display: flex;
  align-items: center;
  gap: 24rpx;
  padding: 28rpx;
  border-radius: 20rpx;
  background: #ffffff;
  box-shadow: 0 6rpx 20rpx rgba(15, 23, 42, 0.05);
}
.card-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 96rpx;
  height: 96rpx;
  border-radius: 20rpx;
  flex-shrink: 0;
  font-size: 44rpx;
}
.card-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 10rpx;
}
.card-title {
  font-size: 30rpx;
  font-weight: 600;
  color: #1f2937;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.card-meta {
  display: flex;
  align-items: center;
  gap: 12rpx;
  font-size: 24rpx;
  color: #9ca3af;
}
.card-cat {
  color: #2563eb;
  background: #eff6ff;
  padding: 2rpx 14rpx;
  border-radius: 12rpx;
}
.card-file {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 300rpx;
}
.card-foot {
  display: flex;
  gap: 20rpx;
  font-size: 22rpx;
  color: #c0c4cc;
}
.card-arrow {
  color: #c0c4cc;
  font-size: 40rpx;
}
.load-more {
  text-align: center;
  padding: 24rpx;
  color: #9ca3af;
  font-size: 26rpx;
}
.empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding-top: 200rpx;
  color: #9ca3af;
}
.empty-icon { font-size: 80rpx; }
.empty-text { margin-top: 20rpx; font-size: 28rpx; }
</style>
