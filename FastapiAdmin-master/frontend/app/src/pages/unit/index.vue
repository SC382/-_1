<!-- 救治医院（区域胸痛中心网络）：已开通 / 未开通智慧胸痛的医院 -->
<script setup lang="ts">
import { computed, ref } from 'vue'
import { onPullDownRefresh, onShow } from '@dcloudio/uni-app'
import DoctorAPI, { type HospitalOpenItem } from '@/api/module_cpx/doctor'

definePage({
  name: 'unit',
  style: { navigationBarTitleText: '救治医院' },
})

const hospitals = ref<HospitalOpenItem[]>([])

const openedList = computed(() => hospitals.value.filter((h) => h.opened))
const closedList = computed(() => hospitals.value.filter((h) => !h.opened))

async function fetchUnits() {
  try {
    hospitals.value = await DoctorAPI.units()
  }
  catch { /* toast */ }
}

onShow(fetchUnits)

// 下拉刷新：重新拉取医院列表（配合 cacheFor:0，每次都是最新数据）
onPullDownRefresh(async () => {
  try {
    await fetchUnits()
  }
  finally {
    uni.stopPullDownRefresh()
  }
})
</script>

<template>
  <view class="unit-page">
    <!-- 统计卡片 -->
    <view class="stat-bar">
      <view class="stat-card open">
        <text class="stat-num">{{ openedList.length }}</text>
        <text class="stat-label">已开通救治医院</text>
      </view>
      <view class="stat-card close">
        <text class="stat-num">{{ closedList.length }}</text>
        <text class="stat-label">未开通救治医院</text>
      </view>
    </view>

    <!-- 已开通 -->
    <view class="group-title">
      <text class="dot open" />已开通救治医院（{{ openedList.length }}）
    </view>
    <view v-if="openedList.length" class="hosp-list">
      <view
        v-for="h in openedList"
        :key="h.hospital_id"
        class="hosp-card open"
      >
        <view class="hosp-head">
          <text class="hosp-name">{{ h.hospital_name }}</text>
          <text class="hosp-badge open">已开通</text>
        </view>
        <view class="hosp-meta">
          <text class="hosp-level">{{ h.hospital_level || '等级未填' }}</text>
          <text v-if="h.city" class="hosp-city">{{ h.city }}</text>
        </view>
        <view class="hosp-foot">
          <text class="hosp-tip on">已接入智慧胸痛中心</text>
        </view>
      </view>
    </view>
    <view v-else class="group-empty">暂无已开通救治医院</view>

    <!-- 未开通 -->
    <view class="group-title">
      <text class="dot close" />未开通救治医院（{{ closedList.length }}）
    </view>
    <view v-if="closedList.length" class="hosp-list">
      <view
        v-for="h in closedList"
        :key="h.hospital_id"
        class="hosp-card close"
      >
        <view class="hosp-head">
          <text class="hosp-name">{{ h.hospital_name }}</text>
          <text class="hosp-badge close">未开通</text>
        </view>
        <view class="hosp-meta">
          <text class="hosp-level">{{ h.hospital_level || '等级未填' }}</text>
          <text v-if="h.city" class="hosp-city">{{ h.city }}</text>
        </view>
        <view class="hosp-foot">
          <text class="hosp-tip">暂未接入</text>
        </view>
      </view>
    </view>
    <view v-else class="group-empty">暂无未开通救治医院</view>
  </view>
</template>

<style lang="scss" scoped>
.unit-page { min-height: 100vh; background: #f3f4f6; padding: 24rpx 32rpx 40rpx; }

.stat-bar { display: flex; gap: 20rpx; margin-bottom: 28rpx; }
.stat-card {
  flex: 1;
  padding: 32rpx 28rpx;
  border-radius: 20rpx;
  color: #ffffff;
}
.stat-card.open { background: linear-gradient(135deg, #10b981, #059669); }
.stat-card.close { background: linear-gradient(135deg, #9ca3af, #6b7280); }
.stat-num { display: block; font-size: 56rpx; font-weight: 700; }
.stat-label { font-size: 26rpx; opacity: 0.95; }

.group-title {
  display: flex;
  align-items: center;
  gap: 12rpx;
  margin: 24rpx 4rpx 16rpx;
  font-size: 28rpx;
  font-weight: 600;
  color: #374151;
}
.dot { width: 16rpx; height: 16rpx; border-radius: 50%; }
.dot.open { background: #10b981; }
.dot.close { background: #9ca3af; }

.hosp-list { display: flex; flex-direction: column; gap: 20rpx; }
.hosp-card { padding: 28rpx; border-radius: 20rpx; background: #ffffff; }
.hosp-card.open { box-shadow: 0 6rpx 20rpx rgba(16, 185, 129, 0.08); }
.hosp-card.close { opacity: 0.72; }
.hosp-head { display: flex; align-items: center; justify-content: space-between; }
.hosp-name { font-size: 32rpx; font-weight: 600; color: #1f2937; }
.hosp-badge { font-size: 22rpx; padding: 4rpx 16rpx; border-radius: 16rpx; }
.hosp-badge.open { color: #059669; background: #d1fae5; }
.hosp-badge.close { color: #6b7280; background: #f3f4f6; }
.hosp-meta { display: flex; gap: 20rpx; margin-top: 12rpx; }
.hosp-level, .hosp-city { font-size: 24rpx; color: #9ca3af; }
.hosp-foot { margin-top: 16rpx; }
.hosp-tip { font-size: 24rpx; color: #c0c4cc; }
.hosp-tip.on { color: #059669; }

.group-empty { padding: 20rpx 4rpx; font-size: 24rpx; color: #c0c4cc; }
</style>
