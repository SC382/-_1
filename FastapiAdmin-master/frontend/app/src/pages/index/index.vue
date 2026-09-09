<!-- 医生端首页工作台：统计 + 快捷入口 -->
<script setup lang="ts">
import { computed, ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { useUserStore } from '@/store/userStore'
import DoctorAPI, { type DoctorStats } from '@/api/module_cpx/doctor'
import { AnnouncementAPI, type AnnouncementItem } from '@/api/module_cpx/announcement'
import { ValueAddedAPI, type ValueAddedItem } from '@/api/module_cpx/value_added'
import homeBg from '@/static/images/home_bg.jpg'

// 顶部完整横幅图（image widthFix 按原图 850×480 比例完整显示，图上文字永不裁切）
// homeBg import 见上方，供 <image class="header-bg"> 使用

definePage({
  name: 'home',
  layout: 'tabbar',
  style: { navigationStyle: 'custom' },
})

const userStore = useUserStore()
const stats = ref<DoctorStats>({ today_new: 0, draft: 0, pending: 0, approved: 0, rejected: 0 })

async function fetchStats() {
  try {
    const res = await DoctorAPI.stats()
    stats.value = res
  }
  catch {
    // http 层已 toast
  }
}

onShow(() => {
  fetchStats()
  fetchAnnouncements()
  fetchValueAdded()
})

// ── 公告 banner：swiper 垂直轮播已发布公告 ──────────────────
const announcements = ref<AnnouncementItem[]>([])
async function fetchAnnouncements() {
  try {
    announcements.value = await AnnouncementAPI.active(10)
  }
  catch {
    // http 层已 toast
  }
}
function goAnnouncementDetail(id: number) {
  uni.navigateTo({ url: `/subPages/module_cpx/announcement-detail/index?id=${id}` })
}

// ── 增值服务：横向卡片流，点击跳转 ────────────────────────
const valueAddedList = ref<ValueAddedItem[]>([])
async function fetchValueAdded() {
  try {
    valueAddedList.value = await ValueAddedAPI.active(20)
  }
  catch {
    // http 层已 toast
  }
}
function goValueAdded(item: ValueAddedItem) {
  if (!item.link_url) {
    uni.showToast({ title: '功能开发中', icon: 'none' })
    return
  }
  if (item.link_type === 'internal') {
    // App 内页路由（相对路径）
    uni.navigateTo({ url: item.link_url })
    return
  }
  // h5 / external：H5 端新窗口打开，App 端调起系统浏览器
  // #ifdef H5
  window.open(item.link_url, '_blank')
  // #endif
  // #ifndef H5
  try {
    plus.runtime.openURL(item.link_url)
  }
  catch {
    // 极少数机型无可用浏览器时，回退为复制链接
    uni.setClipboardData({ data: item.link_url, success: () => uni.showToast({ title: '打开失败，链接已复制', icon: 'none' }) })
  }
  // #endif
}
const hasValueAdded = computed(() => valueAddedList.value.length > 0)

const statCards = [
  { key: 'today_new' as const, label: '今日新增', color: '#2563eb', status: 'today' },
  { key: 'draft' as const, label: '草稿', color: '#9ca3af', status: 'draft' },
  { key: 'pending' as const, label: '待审核', color: '#f59e0b', status: 'submitted' },
  { key: 'approved' as const, label: '已通过', color: '#10b981', status: 'approved' },
  { key: 'rejected' as const, label: '驳回', color: '#ef4444', status: 'rejected' },
]

const entries = ref([
  { icon: '/static/icons/nav_data.svg', title: '数据直报', url: '/pages/work/index' },
  { icon: '/static/icons/nav_analysis.svg', title: '数据分析', url: '/pages/analysis/index' },
  { icon: '/static/icons/nav_followup.svg', title: '随访管理', url: '/pages/followup/index' },
  { icon: '/static/icons/nav_hospital.svg', title: '救治医院', url: '/pages/unit/index' },
  { icon: '/static/icons/nav_meeting.svg', title: '三会模板', url: '/pages/meeting/index' },
  { icon: '/static/icons/nav_academy.svg', title: '胸痛学院', url: '/pages/academy/index' },
  { icon: '/static/icons/nav_ecg.svg', title: '远程心电', url: '/pages/ecg/index' },
  { icon: '/static/icons/nav_report.svg', title: '今日报告', url: '/pages/daily-report/index' },
])

function goEntry(e: { url?: string }) {
  if (e.url) {
    uni.navigateTo({ url: e.url })
    return
  }
  uni.showToast({ title: '功能开发中', icon: 'none' })
}

function handleLogout() {
  uni.showModal({
    title: '提示',
    content: '确定要退出登录吗？',
    confirmText: '退出',
    success: (res) => {
      if (res.confirm) {
        userStore.clearAll()
        uni.reLaunch({ url: '/pages/login/index' })
      }
    },
  })
}

/** 点击统计数字 → 跳转数据直报页并自动筛选对应状态 */
function goStatCase(status: string) {
  // 今日新增：跳过去按"今日"日期范围筛选；其余按状态值筛选（storage + URL 双保险）
  if (status === 'today') {
    uni.setStorageSync('workFilter', { range: 'today', status: '' })
    uni.navigateTo({ url: '/pages/work/index?range=today' })
  }
  else {
    uni.setStorageSync('workFilter', { range: '', status })
    uni.navigateTo({ url: `/pages/work/index?status=${status}` })
  }
}

</script>

<template>
  <view class="doctor-home">
    <!-- 顶部 banner：完整横幅图（widthFix 按比例全图显示）+ 图上装饰 + 图内下方统计卡 -->
    <view class="home-header">
      <image class="header-bg" :src="homeBg" mode="widthFix" />
      <view class="header-deco deco-1" />
      <view class="header-deco deco-2">♥</view>

      <!-- 统计卡：图片内部下方，可点击查看对应状态病例 -->
      <view class="stat-card">
        <view v-for="c in statCards" :key="c.key" class="stat-item" @click="goStatCase(c.status)">
          <text class="stat-num" :style="{ color: c.color }">{{ stats[c.key] }}</text>
          <text class="stat-label">{{ c.label }}</text>
        </view>
      </view>
    </view>

    <!-- 公告 banner：垂直轮播最新公告 -->
    <view v-if="announcements.length > 0" class="announce-banner">
      <view class="announce-left">
        <text class="announce-horn">📢</text>
      </view>
      <swiper
        class="announce-swiper"
        vertical
        autoplay
        :interval="4000"
        :circular="announcements.length > 1"
        :duration="400"
      >
        <swiper-item v-for="a in announcements" :key="a.id" @click="goAnnouncementDetail(a.id)">
          <view class="announce-item">
            <text class="announce-title">{{ a.title }}</text>
            <text v-if="a.subtitle" class="announce-subtitle">{{ a.subtitle }}</text>
          </view>
        </swiper-item>
      </swiper>
      <view class="announce-right" @click="goAnnouncementDetail(announcements[0].id)">
        <text class="announce-more">></text>
      </view>
    </view>

    <!-- 功能九宫格 -->
    <view class="entry-grid">
      <view
        v-for="e in entries"
        :key="e.title"
        class="entry-card"
        @click="goEntry(e)"
      >
        <image class="entry-icon" :src="e.icon" mode="aspectFit" />
        <text class="entry-title">{{ e.title }}</text>
      </view>
    </view>

    <!-- 增值服务：浅蓝大卡 + 左标题蓝字 + 右大图标，可滑动切换 -->
    <view v-if="hasValueAdded" class="value-added">
      <view class="section-header">
        <text class="section-title">增值服务</text>
        <text class="section-more" @click="goValueAdded(valueAddedList[0])">更多 ></text>
      </view>
      <swiper
        class="va-swiper"
        :indicator-dots="valueAddedList.length > 1"
        indicator-color="rgba(37, 99, 235, 0.25)"
        indicator-active-color="#2563eb"
        :circular="valueAddedList.length > 1"
        :autoplay="false"
        :duration="300"
      >
        <swiper-item v-for="item in valueAddedList" :key="item.id" @click="goValueAdded(item)">
          <view class="va-banner">
            <view class="va-banner-deco" />
            <view class="va-banner-left">
              <text class="va-banner-name">{{ item.name }}</text>
              <text v-if="item.subtitle" class="va-banner-subtitle">{{ item.subtitle }}</text>
            </view>
            <view class="va-banner-right">
              <image
                v-if="item.cover || item.icon"
                class="va-banner-cover"
                :src="item.cover || item.icon"
                mode="aspectFit"
              />
              <view v-else class="va-banner-cover va-banner-fallback">{{ item.name.slice(0, 1) }}</view>
            </view>
          </view>
        </swiper-item>
      </swiper>
    </view>
  </view>
</template>

<style lang="scss" scoped>
.doctor-home {
  min-height: 100vh;
  background: #f3f4f6;
  padding-bottom: 40rpx;
}

.home-header {
  position: relative;
  /* 全宽横幅带：背景取图边缘实测蓝做垂直渐变（顶 #145CB3 → 底 #4B71F3，与图内垂直渐变同向），
     桌面宽屏下图限宽居中后，两侧由同色系渐变延伸铺满 → 横幅视觉横贯整屏、无灰底；
     图片本身完整不裁、不变形 */
  background: linear-gradient(180deg, #145cb3 0%, #4b71f3 100%);
}
/* 完整横幅图：等比完整显示；限宽 640px 居中（桌面高度≈421px = 640×494/750），
   手机窄屏（<640px）不受限仍铺满全宽，观感不变 */
.header-bg {
  width: 100%;
  max-width: 640px;
  margin: 0 auto;
  display: block;
  position: relative;
  z-index: 0;
}
.header-deco {
  position: absolute;
  opacity: 0.15;
  color: #ffffff;
  z-index: 1;
  pointer-events: none;
}
.deco-1 {
  width: 140rpx;
  height: 140rpx;
  right: -30rpx;
  top: -30rpx;
  border-radius: 50%;
  background: #ffffff;
}
.deco-2 {
  right: 120rpx;
  bottom: 20rpx;
  font-size: 60rpx;
}
.header-title {
  display: block;
  text-align: center;
  margin-top: 4rpx;
  font-size: 38rpx;
  font-weight: 700;
  color: #ffffff;
  letter-spacing: 4rpx;
  text-shadow: 0 2rpx 8rpx rgba(0, 0, 0, 0.25);
}
.header-logout {
  position: absolute;
  right: 32rpx;
  top: 40rpx;
  padding: 10rpx 28rpx;
  border-radius: 32rpx;
  border: 2rpx solid rgba(255, 255, 255, 0.6);
  color: #ffffff;
  font-size: 24rpx;
}

/* 统计卡：叠在完整横幅图内部下方（无底纯数字叠图） */
.stat-card {
  position: absolute;
  left: 32rpx;
  right: 32rpx;
  bottom: 16rpx;
  z-index: 1;
  display: flex;
  justify-content: space-between;
  padding: 0 12rpx;
}
.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 8rpx 12rpx;
  border-radius: 16rpx;
}
.stat-item:active {
  background: rgba(255, 255, 255, 0.2);
}
.stat-num {
  font-size: 42rpx;
  font-weight: 700;
  text-shadow: 0 2rpx 8rpx rgba(0, 0, 0, 0.3);
}
.stat-label {
  margin-top: 4rpx;
  font-size: 22rpx;
  color: #ffffff;
  text-shadow: 0 1rpx 4rpx rgba(0, 0, 0, 0.35);
}

.entry-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 24rpx;
  padding: 20rpx 32rpx 0;
  margin-top: 0;
}

/* 公告 banner：白底卡片 */
.announce-banner {
  display: flex;
  align-items: center;
  margin: 24rpx 32rpx 0;
  padding: 20rpx 24rpx;
  border-radius: 20rpx;
  background: #ffffff;
  border: 2rpx solid #e5e7eb;
  box-shadow: 0 4rpx 12rpx rgba(15, 23, 42, 0.05);
}
.announce-left {
  margin-right: 16rpx;
}
.announce-horn {
  font-size: 34rpx;
}
.announce-swiper {
  flex: 1;
  height: 44rpx;
}
.announce-item {
  display: flex;
  align-items: center;
  height: 44rpx;
  overflow: hidden;
}
.announce-title {
  font-size: 26rpx;
  color: #1f2937;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 420rpx;
}
.announce-subtitle {
  margin-left: 16rpx;
  font-size: 22rpx;
  color: #9ca3af;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.announce-right {
  margin-left: 12rpx;
  padding: 4rpx 0 4rpx 16rpx;
  border-left: 2rpx solid #f3f4f6;
}
.announce-more {
  font-size: 30rpx;
  color: #2563eb;
  font-weight: 600;
}

/* 增值服务 */
.value-added {
  margin: 32rpx 32rpx 0;
}
.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20rpx;
}
.section-title {
  font-size: 32rpx;
  font-weight: 700;
  color: #1f2937;
}
.section-more {
  font-size: 26rpx;
  color: #2563eb;
}
/* 增值服务：浅蓝大卡（单卡轮播） */
.va-swiper {
  height: 200rpx;
  padding: 0 4rpx;
}
.va-banner {
  position: relative;
  display: flex;
  align-items: center;
  height: 180rpx;
  padding: 24rpx 32rpx;
  border-radius: 24rpx;
  background: linear-gradient(135deg, #e0f2ff 0%, #f0f9ff 60%, #ffffff 100%);
  border: 2rpx solid #d6e8fa;
  box-shadow: 0 6rpx 18rpx rgba(37, 99, 235, 0.08);
  overflow: hidden;
}
.va-banner-deco {
  position: absolute;
  width: 220rpx;
  height: 220rpx;
  right: -60rpx;
  top: -60rpx;
  border-radius: 50%;
  background: rgba(37, 99, 235, 0.08);
}
.va-banner-left {
  flex: 1;
  min-width: 0;
  position: relative;
  z-index: 1;
}
.va-banner-name {
  display: block;
  font-size: 32rpx;
  font-weight: 700;
  color: #1e40af;
  line-height: 1.35;
  word-break: break-all;
}
.va-banner-subtitle {
  display: block;
  margin-top: 8rpx;
  font-size: 22rpx;
  color: #6b7280;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.va-banner-right {
  width: 200rpx;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  z-index: 1;
}
.va-banner-cover {
  width: 160rpx;
  height: 160rpx;
}
.va-banner-fallback {
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #2563eb, #0ea5e9);
  color: #ffffff;
  font-size: 56rpx;
  font-weight: 700;
  border-radius: 24rpx;
}
.entry-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 16rpx 12rpx;
}
.entry-icon {
  width: 104rpx;
  height: 104rpx;
  margin-bottom: 12rpx;
}
.entry-title {
  font-size: 26rpx;
  font-weight: 500;
  color: #1f2937;
}
</style>
