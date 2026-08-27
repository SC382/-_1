<!-- 时间采集：关键时间节点一键当前时间 + 手动修改，自动联动病例表单 -->
<script setup lang="ts">
import { ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import DoctorAPI, { type TimelineNode } from '@/api/module_cpx/doctor'

definePage({
  name: 'case-time',
  style: { navigationBarTitleText: '时间采集' },
})

const caseId = ref(0)
const loading = ref(false)
const saving = ref(false)
const templateId = ref(0)
const nodes = ref<TimelineNode[]>([])
const formData = ref<Record<string, unknown>>({})

const groupTabs = [
  { key: 'all', name: '全部' },
  { key: 'pre', name: '院前' },
  { key: 'triage', name: '分诊诊疗' },
  { key: 'treat', name: '诊疗' },
  { key: 'pci', name: '介入' },
]
const activeGroup = ref('all')

// 时间节点分组
const NODE_GROUP: Record<string, string> = {
  onset_time: 'pre',
  call_time: 'pre',
  arrive_gate_time: 'triage',
  fmc_time: 'triage',
  first_ecg_time: 'triage',
  troponin_time: 'triage',
  cath_lab_activate_time: 'treat',
  puncture_time: 'pci',
  balloon_time: 'pci',
  surgery_end_time: 'pci',
}

onLoad(async (query) => {
  caseId.value = Number(query?.id || 0)
  if (!caseId.value) return
  loading.value = true
  try {
    const [detail, timeline] = await Promise.all([
      DoctorAPI.caseDetail(caseId.value),
      DoctorAPI.timeline(caseId.value),
    ])
    nodes.value = timeline.nodes
    formData.value = { ...(detail.form_data || {}) }
    templateId.value = detail.template_id || 0
  }
  finally {
    loading.value = false
  }
})

const filteredNodes = () => {
  if (activeGroup.value === 'all') return nodes.value
  return nodes.value.filter((n) => NODE_GROUP[n.code] === activeGroup.value)
}

function nowStr() {
  const n = new Date()
  const p = (x: number) => String(x).padStart(2, '0')
  return `${n.getFullYear()}-${p(n.getMonth() + 1)}-${p(n.getDate())} ${p(n.getHours())}:${p(n.getMinutes())}`
}

/** 一键采集当前时间 */
function setNow(node: TimelineNode) {
  formData.value[node.code] = nowStr()
  node.value = formData.value[node.code]
}

function onDateChange(node: TimelineNode, e: any) {
  const d = e.detail.value
  const t = String(formData.value[node.code] || '').slice(11, 16) || '00:00'
  formData.value[node.code] = `${d} ${t}`
  node.value = formData.value[node.code]
}
function onTimeChange(node: TimelineNode, e: any) {
  const t = e.detail.value
  const d = String(formData.value[node.code] || '').slice(0, 10) || today()
  formData.value[node.code] = `${d} ${t}`
  node.value = formData.value[node.code]
}
function today() {
  const n = new Date()
  const p = (x: number) => String(x).padStart(2, '0')
  return `${n.getFullYear()}-${p(n.getMonth() + 1)}-${p(n.getDate())}`
}

async function handleSave() {
  saving.value = true
  try {
    await DoctorAPI.saveForm(caseId.value, { template_id: templateId.value, form_data: { ...formData.value } })
    uni.showToast({ title: '时间已保存并联动', icon: 'success' })
  }
  catch { /* toast */ }
  finally { saving.value = false }
}
</script>

<template>
  <view class="time-page">
    <view v-if="loading" class="loading">加载中...</view>
    <template v-else>
      <!-- 分组 Tab -->
      <view class="group-bar">
        <view
          v-for="g in groupTabs"
          :key="g.key"
          class="group-item"
          :class="{ active: activeGroup === g.key }"
          @click="activeGroup = g.key"
        >{{ g.name }}</view>
      </view>

      <view class="node-list">
        <view v-for="n in filteredNodes()" :key="n.code" class="node-card">
          <text class="node-name">{{ n.name }}</text>
          <view class="node-value" :class="{ empty: !formData[n.code] }">
            {{ formData[n.code] || '未采集' }}
          </view>
          <view class="node-ops">
            <picker mode="date" :value="String(formData[n.code] || '').slice(0,10)" @change="onDateChange(n, $event)">
              <view class="op-btn">日期</view>
            </picker>
            <picker mode="time" :value="String(formData[n.code] || '').slice(11,16)" @change="onTimeChange(n, $event)">
              <view class="op-btn">时间</view>
            </picker>
            <view class="op-btn primary" @click="setNow(n)">采集当前时间</view>
          </view>
        </view>
      </view>

      <button class="save-btn" :disabled="saving" @click="handleSave">
        {{ saving ? '保存中...' : '保存并联动病例' }}
      </button>
    </template>
  </view>
</template>

<style lang="scss" scoped>
.time-page {
  min-height: 100vh;
  background: #f3f4f6;
  padding: 24rpx 32rpx 60rpx;
}
.loading { text-align: center; padding-top: 200rpx; color: #9ca3af; }

.group-bar { display: flex; gap: 16rpx; margin-bottom: 24rpx; flex-wrap: wrap; }
.group-item {
  padding: 12rpx 28rpx;
  border-radius: 32rpx;
  background: #ffffff;
  font-size: 26rpx;
  color: #6b7280;
}
.group-item.active { background: #2563eb; color: #ffffff; }

.node-list { display: flex; flex-direction: column; gap: 20rpx; }
.node-card { padding: 28rpx; border-radius: 20rpx; background: #ffffff; }
.node-name { font-size: 30rpx; font-weight: 600; color: #1f2937; }
.node-value {
  margin: 16rpx 0;
  font-size: 36rpx;
  font-weight: 700;
  color: #2563eb;
}
.node-value.empty { color: #c0c4cc; font-weight: 400; }
.node-ops { display: flex; gap: 16rpx; }
.op-btn {
  padding: 12rpx 24rpx;
  border-radius: 16rpx;
  background: #f3f4f6;
  font-size: 26rpx;
  color: #4b5563;
}
.op-btn.primary { background: #2563eb; color: #ffffff; }

.save-btn {
  margin-top: 32rpx;
  height: 92rpx;
  line-height: 92rpx;
  border-radius: 20rpx;
  background: linear-gradient(135deg, #2563eb, #0ea5e9);
  color: #ffffff;
  font-size: 30rpx;
  font-weight: 600;
}
.save-btn::after { border: none; }
</style>
