<!-- 我的病例：状态分类 + 搜索 + 列表 + 操作 -->
<script setup lang="ts">
import { reactive, ref } from 'vue'
import { onLoad, onShow } from '@dcloudio/uni-app'
import DoctorAPI, { type CaseRecordItem } from '@/api/module_cpx/doctor'

definePage({
  name: 'work',
  style: { navigationStyle: 'custom' },
})

const statusBarHeight = uni.getSystemInfoSync().statusBarHeight || 0

function goBack() {
  uni.navigateBack()
}

const loading = ref(false)
const list = ref<CaseRecordItem[]>([])
const total = ref(0)
const query = reactive({ page_no: 1, page_size: 10, status: '', keyword: '', start_time: '', end_time: '' })

// 从首页统计数字跳转过来时，URL 参数自动筛选对应状态/日期
onLoad((opt: any) => {
  if (opt?.range === 'today') {
    // 今日新增：按今天的 create_time 范围筛选
    const now = new Date()
    const y = now.getFullYear()
    const m = String(now.getMonth() + 1).padStart(2, '0')
    const d = String(now.getDate()).padStart(2, '0')
    query.start_time = `${y}-${m}-${d}`
    query.end_time = `${y}-${m}-${d}`
  }
  else if (opt?.status) {
    query.status = opt.status
  }
  // onLoad 触发后立即加载一次
  fetchData()
})

// 每次页面显示都刷新列表（从其他页面返回时）
onShow(() => {
  // 如果不是首次加载（onLoad 已调用过），才刷新
  if (list.value.length > 0 || total.value > 0) fetchData()
})

const statusTabs = [
  { label: '全部', value: '' },
  { label: '草稿', value: 'draft' },
  { label: '待审核', value: 'submitted' },
  { label: '已通过', value: 'approved' },
  { label: '驳回', value: 'rejected' },
]

const statusLabel = (s?: string) => {
  if (s === 'draft') return '草稿'
  if (s === 'submitted') return '待审核'
  if (s === 'approved') return '已通过'
  if (s === 'rejected') return '驳回'
  return s ?? '-'
}
const statusColor = (s?: string) => {
  if (s === 'draft') return '#9ca3af'
  if (s === 'submitted') return '#f59e0b'
  if (s === 'approved') return '#10b981'
  if (s === 'rejected') return '#ef4444'
  return '#6b7280'
}

async function fetchData() {
  loading.value = true
  try {
    const res = await DoctorAPI.myCases({
      page_no: query.page_no,
      page_size: query.page_size,
      status: query.status || undefined,
      keyword: query.keyword || undefined,
      start_time: query.start_time || undefined,
      end_time: query.end_time || undefined,
    })
    list.value = res.items
    total.value = res.total
  }
  finally {
    loading.value = false
  }
}

function switchStatus(v: string) {
  query.status = v
  // 主动切换状态 Tab 时，清除"今日"日期范围，查看该状态全量
  query.start_time = ''
  query.end_time = ''
  query.page_no = 1
  fetchData()
}
function handleSearch() {
  query.page_no = 1
  fetchData()
}
function onPullDownRefresh() {
  fetchData()
  uni.stopPullDownRefresh()
}

/** 查看详情（所有状态） */
function goDetail(row: CaseRecordItem) {
  uni.navigateTo({ url: `/pages/case/detail?id=${row.id}` })
}
/** 草稿/驳回 → 继续填报 */
function goFill(row: CaseRecordItem) {
  uni.navigateTo({ url: `/pages/case/fill?id=${row.id}` })
}
/** 删除病例（确认后删除并刷新） */
function handleDelete(row: CaseRecordItem) {
  uni.showModal({
    title: '删除病例',
    content: `确认删除「${row.patient_name || '-'}」的病例？将连带删除详情、审核、随访与心电记录，不可恢复。`,
    confirmText: '删除',
    confirmColor: '#ef4444',
    success: async (res) => {
      if (!res.confirm) return
      try {
        await DoctorAPI.deleteCase(row.id)
        uni.showToast({ title: '已删除', icon: 'success' })
        fetchData()
      }
      catch {
        uni.showToast({ title: '删除失败', icon: 'none' })
      }
    },
  })
}
/** 添加患者（新建病例建档） */
function goCreate() {
  uni.navigateTo({ url: '/pages/case/create' })
}

</script>

<template>
  <view class="my-cases">
    <!-- 自定义蓝色导航栏：返回 + 标题「病例列表」 + 右上角添加患者 -->
    <view class="nav-bar" :style="{ paddingTop: `${statusBarHeight}px` }">
      <view class="nav-back" @click="goBack">‹</view>
      <text class="nav-title">病例列表</text>
      <view class="nav-right" @click="goCreate">
        <text class="nav-add">＋</text>
        <text class="nav-add-text">添加患者</text>
      </view>
    </view>

    <view class="page-body">
    <!-- 搜索区 -->
    <view class="search-bar">
      <input
        v-model="query.keyword"
        class="search-input"
        placeholder="患者姓名 / 病例编号"
        placeholder-class="search-placeholder"
        confirm-type="search"
        @confirm="handleSearch"
      />
      <view class="search-btn" @click="handleSearch">查询</view>
    </view>

    <!-- 状态 Tab -->
    <view class="status-tabs">
      <view
        v-for="t in statusTabs"
        :key="t.value"
        class="status-tab"
        :class="{ active: query.status === t.value }"
        @click="switchStatus(t.value)"
      >
        {{ t.label }}
      </view>
    </view>

    <!-- 列表 -->
    <view v-if="list.length" class="case-list">
      <view
        v-for="c in list"
        :key="c.id"
        class="case-card"
        @click="goDetail(c)"
      >
        <view class="case-head">
          <text class="case-patient">{{ c.patient_name || '-' }}</text>
          <text class="case-status" :style="{ color: statusColor(c.status) }">{{ statusLabel(c.status) }}</text>
        </view>
        <view class="case-tags">
          <text v-if="c.diagnose_type" class="case-tag diag">{{ c.diagnose_type }}</text>
          <text v-if="c.come_type" class="case-tag come">{{ c.come_type === '120' ? '120急救' : c.come_type }}</text>
          <text class="case-no">{{ c.case_no }}</text>
        </view>
        <view class="case-foot">
          <text class="case-time">{{ c.update_time || c.create_time || '' }}</text>
          <view class="case-ops">
            <text class="op-link" @click.stop="goDetail(c)">详情</text>
            <text
              v-if="c.status === 'draft' || c.status === 'rejected'"
              class="op-link"
              @click.stop="goFill(c)"
            >{{ c.status === 'rejected' ? '修改重提' : '继续填报' }}</text>
            <text class="op-link danger" @click.stop="handleDelete(c)">删除</text>
          </view>
        </view>
      </view>
      <view v-if="total > query.page_size * query.page_no" class="load-more" @click="query.page_no++; fetchData()">
        加载更多
      </view>
    </view>

    <view v-else-if="!loading" class="empty">
      <text class="empty-icon">📭</text>
      <text class="empty-text">暂无病例</text>
    </view>
    </view>
  </view>
</template>

<style lang="scss" scoped>
.my-cases {
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
.nav-right {
  width: 160rpx;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 6rpx;
}
.nav-add { font-size: 40rpx; color: #ffffff; line-height: 1; }
.nav-add-text { font-size: 24rpx; color: #ffffff; }

.page-body { padding: 24rpx 32rpx 0; }

.search-bar {
  display: flex;
  align-items: center;
  gap: 16rpx;
  margin-bottom: 24rpx;
}
.search-input {
  flex: 1;
  height: 80rpx;
  padding: 0 24rpx;
  border-radius: 16rpx;
  background: #f5f6f8;
  font-size: 28rpx;
}
.search-placeholder {
  color: #9ca3af;
}
.search-btn {
  padding: 0 36rpx;
  height: 80rpx;
  line-height: 80rpx;
  border-radius: 16rpx;
  background: #1d4ed8;
  color: #ffffff;
  font-size: 28rpx;
}

.status-tabs {
  display: flex;
  gap: 16rpx;
  margin-bottom: 24rpx;
}
.status-tab {
  padding: 12rpx 24rpx;
  border-radius: 32rpx;
  background: #f5f6f8;
  font-size: 26rpx;
  color: #6b7280;
}
.status-tab.active {
  background: #2563eb;
  color: #ffffff;
}

.case-list {
  display: flex;
  flex-direction: column;
  gap: 20rpx;
}
.case-card {
  padding: 28rpx;
  border-radius: 20rpx;
  background: #ffffff;
  border: 2rpx solid #f0f1f3;
  box-shadow: 0 6rpx 20rpx rgba(15, 23, 42, 0.04);
}
.case-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.case-patient {
  font-size: 34rpx;
  font-weight: 600;
  color: #1f2937;
}
.case-status {
  font-size: 26rpx;
  font-weight: 500;
}
.case-tags {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12rpx;
  margin-top: 12rpx;
}
.case-tag {
  font-size: 22rpx;
  padding: 4rpx 14rpx;
  border-radius: 16rpx;
}
.case-tag.diag {
  background: #eff6ff;
  color: #2563eb;
}
.case-tag.come {
  background: #f0fdf4;
  color: #16a34a;
}
.case-no {
  font-size: 22rpx;
  color: #9ca3af;
}
.case-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 16rpx;
}
.case-time {
  font-size: 22rpx;
  color: #c0c4cc;
}
.op-link {
  font-size: 26rpx;
  color: #2563eb;
  padding: 6rpx 16rpx;
}
.op-link.danger {
  color: #ef4444;
}

.load-more {
  text-align: center;
  padding: 24rpx;
  color: #2563eb;
  font-size: 26rpx;
}

.empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding-top: 160rpx;
}
.empty-icon {
  font-size: 80rpx;
}
.empty-text {
  margin-top: 20rpx;
  font-size: 28rpx;
  color: #9ca3af;
}
</style>
