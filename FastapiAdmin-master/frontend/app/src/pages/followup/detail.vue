<!-- 随访详情：患者概要 + 患者信息 + 6 分组随访表单（未提交）/ 分组只读展示（已提交） -->
<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import DoctorAPI, { type FollowUpDetail, type FollowUpSubmitBody } from '@/api/module_cpx/doctor'
import { useUserStore } from '@/store/userStore'
import { getApiBaseUrl } from '@/http'
import { safeBack } from '@/utils/back'
import {
  FOLLOWUP_DEPTS,
  INFO_CHANNELS,
  CURRENT_CONDITIONS,
  SYMPTOMS,
  NYHA_LEVELS,
  REACH_STATUS,
  EXAM_STATUS,
  YES_NO,
  MACE_OPTIONS,
} from './_dicts'

definePage({
  name: 'followup-detail',
  style: { navigationBarTitleText: '随访详情' },
})

const followId = ref(0)
const loading = ref(false)
const submitting = ref(false)
const detail = ref<FollowUpDetail | null>(null)

/** 随访表单字段（键与后端 FollowUpSubmitSchema 一致） */
interface FollowUpForm {
  follow_date: string
  follow_status: string
  survival_status: string
  plan_date_start: string
  plan_date_end: string
  follow_dept: string
  follow_user: string
  unplanned_admission: string
  info_channel: string
  current_condition: string
  cardiac_rehab: string
  mace: string
  bp_monitor: string
  lipid_panel: string
  lpa: string
  fasting_glucose: string
  hba1c: string
  smoking: string
  alcohol: string
  height: string
  weight: string
  bmi: string
  symptoms: string
  nyha: string
  ecg_result: string
  ecg_image: string
  ckmb: string
  troponin: string
  bnp: string
  echocardiography: string
  coronary_angiography: string
  coronary_cta: string
  med_antiplatelet: string
  med_lipid_lowering: string
  med_acei: string
  med_arb: string
  med_arni: string
  med_beta_blocker: string
  med_hypoglycemic: string
  med_anticoagulant: string
  med_diuretic: string
  remark: string
}

/** 初始空表单 */
function emptyForm(): FollowUpForm {
  return {
    follow_date: '',
    follow_status: '',
    survival_status: '',
    plan_date_start: '',
    plan_date_end: '',
    follow_dept: '',
    follow_user: '',
    unplanned_admission: '',
    info_channel: '',
    current_condition: '',
    cardiac_rehab: '',
    mace: '',
    bp_monitor: '',
    lipid_panel: '',
    lpa: '',
    fasting_glucose: '',
    hba1c: '',
    smoking: '',
    alcohol: '',
    height: '',
    weight: '',
    bmi: '',
    symptoms: '',
    nyha: '',
    ecg_result: '',
    ecg_image: '',
    ckmb: '',
    troponin: '',
    bnp: '',
    echocardiography: '',
    coronary_angiography: '',
    coronary_cta: '',
    med_antiplatelet: '',
    med_lipid_lowering: '',
    med_acei: '',
    med_arb: '',
    med_arni: '',
    med_beta_blocker: '',
    med_hypoglycemic: '',
    med_anticoagulant: '',
    med_diuretic: '',
    remark: '',
  }
}
const form = reactive<FollowUpForm>(emptyForm())

const FOLLOW_STATUS_TEXT: Record<string, string> = { followed: '已随访', unfollowed: '未随访' }
const SURVIVAL_TEXT: Record<string, string> = { alive: '存活', dead: '死亡', unknown: '未知' }
const followStatusOptions = [
  { label: '已随访', value: 'followed' },
  { label: '未随访', value: 'unfollowed' },
]
const survivalOptions = [
  { label: '存活', value: 'alive' },
  { label: '死亡', value: 'dead' },
  { label: '未知', value: 'unknown' },
]

function today() { return new Date().toISOString().slice(0, 10) }
function addDays(s: string, n: number) {
  const d = new Date(s); d.setDate(d.getDate() + n); return d.toISOString().slice(0, 10)
}
/** 与列表页保持一致的状态口径 */
function displayStatus() {
  const d = detail.value
  if (!d) return '未随访'
  if (d.status === 'submitted') return '已随访'
  const td = today()
  if (d.due_date && d.due_date < td) return '已过期'
  if (d.due_date && d.due_date >= td && d.due_date <= addDays(td, 7)) return '需随访'
  if (d.due_date && d.due_date > addDays(td, 7)) return '未开始'
  return '未随访'
}
function statusClass(s: string) {
  if (s === '已随访') return 'st-done'
  if (s === '已过期') return 'st-overdue'
  if (s === '需随访') return 'st-active'
  return 'st-default'
}

onLoad(async (query) => {
  followId.value = Number(query?.id || 0)
  if (!followId.value) return
  loading.value = true
  try {
    const res = await DoctorAPI.followupDetail(followId.value)
    detail.value = res
    const f = form
    if (res.status === 'submitted') {
      // 已提交：回填已存值，其余给合理默认
      f.follow_date = res.follow_date || today()
    f.follow_status = res.follow_status || 'followed'
    f.survival_status = res.survival_status || 'alive'
    f.plan_date_start = res.plan_date_start || res.discharge_date || ''
    f.plan_date_end = res.plan_date_end || res.due_date || ''
    f.follow_dept = res.follow_dept || '心内科'
    f.follow_user = res.follow_user || ''
    f.unplanned_admission = res.unplanned_admission || ''
    f.info_channel = res.info_channel || ''
    f.current_condition = res.current_condition || ''
    f.cardiac_rehab = res.cardiac_rehab || ''
    f.mace = res.mace || ''
    f.bp_monitor = res.bp_monitor || ''
    f.lipid_panel = res.lipid_panel || ''
    f.lpa = res.lpa || ''
    f.fasting_glucose = res.fasting_glucose || ''
    f.hba1c = res.hba1c || ''
    f.smoking = res.smoking || ''
    f.alcohol = res.alcohol || ''
    f.height = res.height || ''
    f.weight = res.weight || ''
    f.bmi = res.bmi || ''
    f.symptoms = res.symptoms || ''
    f.nyha = res.nyha || ''
    f.ecg_result = res.ecg_result || ''
    f.ecg_image = res.ecg_image || ''
    f.ckmb = res.ckmb || ''
    f.troponin = res.troponin || ''
    f.bnp = res.bnp || ''
    f.echocardiography = res.echocardiography || ''
    f.coronary_angiography = res.coronary_angiography || ''
    f.coronary_cta = res.coronary_cta || ''
    f.med_antiplatelet = res.med_antiplatelet || ''
    f.med_lipid_lowering = res.med_lipid_lowering || ''
    f.med_acei = res.med_acei || ''
    f.med_arb = res.med_arb || ''
    f.med_arni = res.med_arni || ''
    f.med_beta_blocker = res.med_beta_blocker || ''
    f.med_hypoglycemic = res.med_hypoglycemic || ''
    f.med_anticoagulant = res.med_anticoagulant || ''
    f.med_diuretic = res.med_diuretic || ''
    f.remark = res.remark || ''
    }
    else {
      // 未随访计划：表单置空（避免页面实例复用残留旧值），随访医生实际填写时再填
      Object.assign(f, emptyForm())
    }

    // 随访人默认当前登录医生
    if (!f.follow_user) {
      try {
        const me = await DoctorAPI.doctorMe()
        f.follow_user = me.real_name || me.username || ''
      }
      catch { /* 忽略 */ }
    }
  }
  catch {
    detail.value = null
  }
  finally {
    loading.value = false
  }
})

const isSubmitted = computed(() => detail.value?.status === 'submitted')

// ── BMI 自动计算 ──────────────
watch(
  () => [form.height, form.weight],
  () => {
    const h = parseFloat(String(form.height || ''))
    const w = parseFloat(String(form.weight || ''))
    if (h > 0 && w > 0) form.bmi = (w / Math.pow(h / 100, 2)).toFixed(1)
    else form.bmi = ''
  },
)

// ── 心电图图片上传（拍照/相册 → 后端 → 相对 URL 存入表单）──────────────
const BASE_URL = getApiBaseUrl()
const userStore = useUserStore()
function imgSrc(url: unknown) {
  const s = String(url || '')
  if (!s) return ''
  if (s.startsWith('http')) return s
  return `${BASE_URL}${s}`
}
function chooseEcgImage() {
  uni.chooseImage({
    count: 1,
    sourceType: ['camera', 'album'],
    success: (res) => {
      const filePath = res.tempFilePaths[0]
      uni.showLoading({ title: '上传中...' })
      uni.uploadFile({
        url: `${BASE_URL}/api/v1/cpx/doctor/upload/image`,
        filePath,
        name: 'file',
        header: { Authorization: `Bearer ${userStore.getAccessToken() || ''}` },
        success: (up) => {
          uni.hideLoading()
          try {
            const d = JSON.parse(up.data)
            if (d.code === 0 && d.data?.url)
              form.ecg_image = d.data.url
            else
              uni.showToast({ title: d.msg || '上传失败', icon: 'none' })
          }
          catch {
            uni.showToast({ title: '上传失败', icon: 'none' })
          }
        },
        fail: () => { uni.hideLoading(); uni.showToast({ title: '上传失败', icon: 'none' }) },
      })
    },
  })
}
/** 点击已提交心电图图片放大预览 */
function previewEcgImage() {
  const url = imgSrc(detail.value?.ecg_image)
  if (url) uni.previewImage({ urls: [url] })
}

// ── 电话：拨号 / 复制 ──────────────
function phoneAction() {
  const phone = detail.value?.phone
  if (!phone) {
    uni.showToast({ title: '该患者暂无电话', icon: 'none' })
    return
  }
  uni.showActionSheet({
    itemList: ['拨打电话', '复制号码'],
    success: (res) => {
      if (res.tapIndex === 0) uni.makePhoneCall({ phoneNumber: phone, fail: () => {} })
      else if (res.tapIndex === 1) uni.setClipboardData({ data: phone })
    },
  })
}

function comeTypeClass(ct?: string) {
  if (ct === '120') return 'come-120'
  if (ct === '转诊') return 'come-transfer'
  if (ct === '自行') return 'come-self'
  return 'come-default'
}

// ── 表单字段配置（option-row 类）──────────────────
type OptionKey = keyof FollowUpForm
interface FieldDef { key: OptionKey; label: string }
const REACH_FIELDS: FieldDef[] = [
  { key: 'bp_monitor', label: '血压监测' },
  { key: 'lipid_panel', label: '血脂四项' },
  { key: 'lpa', label: '脂蛋白a（LPa）' },
  { key: 'fasting_glucose', label: '空腹血糖' },
  { key: 'hba1c', label: '糖化血红蛋白' },
]
const EXAM_FIELDS: FieldDef[] = [
  { key: 'ckmb', label: 'CKMB' },
  { key: 'troponin', label: '肌钙蛋白' },
  { key: 'bnp', label: '脑钠肽' },
  { key: 'echocardiography', label: '超声心动图' },
  { key: 'coronary_angiography', label: '冠脉造影' },
  { key: 'coronary_cta', label: '冠脉CTA' },
]
const MED_FIELDS: FieldDef[] = [
  { key: 'med_antiplatelet', label: '抗血小板' },
  { key: 'med_lipid_lowering', label: '调脂' },
  { key: 'med_acei', label: 'ACEI' },
  { key: 'med_arb', label: 'ARB' },
  { key: 'med_arni', label: 'ARNI' },
  { key: 'med_beta_blocker', label: 'β受体阻滞剂' },
  { key: 'med_hypoglycemic', label: '降糖' },
  { key: 'med_anticoagulant', label: '抗凝' },
  { key: 'med_diuretic', label: '利尿剂' },
]

function setOption(key: OptionKey, val: string) {
  form[key] = val
}
function onPicker(key: OptionKey, e: { detail: { value: number } }, options: string[]) {
  setOption(key, options[e.detail.value])
}
/** 日期类 picker：detail.value 直接是日期字符串 */
function onDateChange(key: OptionKey, e: { detail: { value: string } }) {
  setOption(key, e.detail.value)
}

const LIMITS = { mace: 200, remark: 500 } as const

async function handleSubmit() {
  const f = form
  if (f.follow_status === 'followed') {
    if (!f.follow_date) {
      uni.showToast({ title: '请选择实际评估日期', icon: 'none' })
      return
    }
    const required: [OptionKey, string][] = [
      ['info_channel', '信息获取途径'],
      ['survival_status', '随访状态'],
      ['current_condition', '目前状况'],
      ['cardiac_rehab', '加入心脏康复计划'],
      ['mace', '出院后主要心血管不良事件'],
    ]
    for (const [k, label] of required) {
      if (!String(f[k] || '').trim()) {
        uni.showToast({ title: `请选择/填写${label}`, icon: 'none' })
        return
      }
    }
  }
  const confirmed = await new Promise<boolean>((resolve) => {
    uni.showModal({
      title: '提交确认',
      content: '提交后该随访不可修改，确认提交吗？',
      confirmText: '确认提交',
      cancelText: '再检查一下',
      success: (res) => resolve(!!res.confirm),
      fail: () => resolve(false),
    })
  })
  if (!confirmed) return

  submitting.value = true
  try {
    await DoctorAPI.followupSubmit(followId.value, { ...f } as FollowUpSubmitBody)
    uni.showToast({ title: '随访已提交', icon: 'success' })
    setTimeout(() => safeBack(), 700)
  }
  catch { /* toast */ }
  finally { submitting.value = false }
}

// ── 只读展示分组（已提交）──────────────────
function val(key: string): string {
  const d = detail.value as unknown as Record<string, unknown> | null
  if (!d) return '-'
  const v = d[key]
  if (v === undefined || v === null || v === '') return '-'
  return String(v)
}
function isYes(v?: string) { return v === '是' }

/** AI 按钮占位（后续迭代接入图片识别） */
function showAiTip() {
  uni.showToast({ title: 'AI 智能识别即将上线', icon: 'none' })
}
</script>

<template>
  <view class="fd-page">
    <view v-if="loading" class="loading">加载中...</view>
    <template v-else-if="detail">
      <!-- 概要 -->
      <view class="summary">
        <view class="sum-row">
          <text class="sum-name">{{ detail.patient_name || '-' }}</text>
          <view class="sum-meta">
            <text class="gender">{{ detail.gender === '女' ? '♀' : '♂' }}</text>
            <text class="age">{{ detail.age || '-' }}岁</text>
            <text v-if="detail.diagnose_type" class="diag-badge">{{ detail.diagnose_type }}</text>
          </view>
        </view>
        <text class="sum-case">{{ detail.case_no || '-' }} · {{ detail.plan_month }} 月随访</text>
        <view class="sum-due-row">
          <text class="sum-due">应随访日期：{{ detail.due_date || '-' }}</text>
          <text class="sum-status" :class="statusClass(displayStatus())">{{ displayStatus() }}</text>
        </view>
      </view>

      <!-- 患者信息 -->
      <view class="card">
        <view class="card-title">患者信息</view>
        <view class="info-row">
          <view class="info-item">
            <text class="info-label">住院号:</text>
            <text class="info-val">{{ detail.inpatient_no || '-' }}</text>
          </view>
          <view class="info-item">
            <text class="info-label">出院日期:</text>
            <text class="info-val">{{ detail.discharge_date || '-' }}</text>
          </view>
        </view>
        <view class="info-row">
          <view class="info-item">
            <text class="info-label">来院方式:</text>
            <text v-if="detail.come_type" class="come-badge" :class="comeTypeClass(detail.come_type)">{{ detail.come_type }}</text>
            <text v-else class="info-val">-</text>
          </view>
          <view class="info-item">
            <text class="info-label">随访计划:</text>
            <text class="info-val">{{ detail.plan_month }} 月</text>
          </view>
        </view>
        <view class="phone-row" @click="phoneAction">
          <text class="phone-icon">📞</text>
          <text class="phone-val">{{ detail.phone || '暂无电话' }}</text>
          <text v-if="detail.phone" class="phone-tip">拨号/复制</text>
        </view>
      </view>

      <!-- 已提交：分组只读展示 -->
      <template v-if="isSubmitted">
        <view class="card">
          <view class="card-title">基本信息</view>
          <view class="read-grid">
            <view class="read-item">
              <text class="read-label">是否随访</text>
              <text class="read-val">{{ FOLLOW_STATUS_TEXT[detail.follow_status || ''] || '-' }}</text>
            </view>
            <view class="read-item">
              <text class="read-label">实际评估日期</text>
              <text class="read-val">{{ detail.follow_date || '-' }}</text>
            </view>
            <view class="read-item">
              <text class="read-label">随访计划日期</text>
              <text class="read-val">{{ val('plan_date_start') }} ~ {{ val('plan_date_end') }}</text>
            </view>
            <view class="read-item">
              <text class="read-label">随访科室</text>
              <text class="read-val">{{ val('follow_dept') }}</text>
            </view>
            <view class="read-item">
              <text class="read-label">随访人</text>
              <text class="read-val">{{ val('follow_user') }}</text>
            </view>
            <view class="read-item">
              <text class="read-label">非计划入院</text>
              <text class="read-val">{{ val('unplanned_admission') }}</text>
            </view>
            <view class="read-item">
              <text class="read-label">信息获取途径</text>
              <text class="read-val">{{ val('info_channel') }}</text>
            </view>
            <view class="read-item">
              <text class="read-label">随访状态</text>
              <text class="read-val">{{ SURVIVAL_TEXT[detail.survival_status || ''] || '-' }}</text>
            </view>
            <view class="read-item">
              <text class="read-label">目前状况</text>
              <text class="read-val">{{ val('current_condition') }}</text>
            </view>
            <view class="read-item">
              <text class="read-label">心脏康复计划</text>
              <text class="read-val">{{ val('cardiac_rehab') }}</text>
            </view>
            <view class="read-item full">
              <text class="read-label">出院后主要心血管不良事件</text>
              <text class="read-val">{{ val('mace') }}</text>
            </view>
          </view>
        </view>

        <view class="card">
          <view class="card-title">危险因素控制</view>
          <view class="read-grid">
            <view v-for="fld in REACH_FIELDS" :key="fld.key" class="read-item">
              <text class="read-label">{{ fld.label }}</text>
              <text class="read-val">{{ val(fld.key) }}</text>
            </view>
            <view class="read-item">
              <text class="read-label">吸烟</text>
              <text class="read-val">{{ val('smoking') }}</text>
            </view>
            <view class="read-item">
              <text class="read-label">饮酒</text>
              <text class="read-val">{{ val('alcohol') }}</text>
            </view>
            <view class="read-item">
              <text class="read-label">身高(cm)</text>
              <text class="read-val">{{ val('height') }}</text>
            </view>
            <view class="read-item">
              <text class="read-label">体重(kg)</text>
              <text class="read-val">{{ val('weight') }}</text>
            </view>
            <view class="read-item">
              <text class="read-label">BMI</text>
              <text class="read-val">{{ val('bmi') }}</text>
            </view>
          </view>
        </view>

        <view class="card">
          <view class="card-title">躯体症状与心功能评价</view>
          <view class="read-grid">
            <view class="read-item">
              <text class="read-label">躯体症状</text>
              <text class="read-val">{{ val('symptoms') }}</text>
            </view>
            <view class="read-item">
              <text class="read-label">NYHA 分级</text>
              <text class="read-val">{{ val('nyha') }}</text>
            </view>
          </view>
        </view>

        <view class="card">
          <view class="card-title">心电图</view>
          <view class="read-grid">
            <view class="read-item full">
              <text class="read-label">心电图图片</text>
              <image v-if="detail.ecg_image" :src="imgSrc(detail.ecg_image)" class="read-img" mode="aspectFit" @click="previewEcgImage" />
              <text v-else class="read-val">-</text>
            </view>
            <view class="read-item full">
              <text class="read-label">心电图结果</text>
              <text class="read-val">{{ val('ecg_result') }}</text>
            </view>
          </view>
        </view>

        <view class="card">
          <view class="card-title">检查项目</view>
          <view class="read-grid">
            <view v-for="fld in EXAM_FIELDS" :key="fld.key" class="read-item">
              <text class="read-label">{{ fld.label }}</text>
              <text class="read-val">{{ val(fld.key) }}</text>
            </view>
          </view>
        </view>

        <view class="card">
          <view class="card-title">用药情况</view>
          <view class="read-grid">
            <view v-for="fld in MED_FIELDS" :key="fld.key" class="read-item">
              <text class="read-label">{{ fld.label }}</text>
              <text class="read-val" :class="{ 'val-yes': isYes(val(fld.key)), 'val-no': val(fld.key) === '否' }">{{ val(fld.key) }}</text>
            </view>
          </view>
        </view>

        <view v-if="detail.remark" class="card">
          <view class="card-title">备注</view>
          <text class="block-val">{{ detail.remark }}</text>
        </view>
        <view v-if="detail.update_time" class="submit-time">提交时间：{{ detail.update_time }}</view>
      </template>

      <!-- 未提交：6 分组随访表单 -->
      <template v-else>
        <!-- 基本信息 -->
        <view class="card">
          <view class="card-title">基本信息</view>
          <view class="field">
            <view class="label-row">
              <text class="label">是否随访 <text class="req">*</text></text>
            </view>
            <view class="option-row">
              <view
                v-for="o in followStatusOptions"
                :key="o.value"
                class="option"
                :class="{ active: form.follow_status === o.value }"
                @click="setOption('follow_status', o.value)"
              >{{ o.label }}</view>
            </view>
          </view>

          <view class="field">
            <view class="label-row">
              <text class="label">实际评估日期 <text v-if="form.follow_status === 'followed'" class="req">*</text></text>
              <text v-if="form.follow_status === 'unfollowed'" class="optional">未随访时选填</text>
            </view>
            <picker mode="date" :value="String(form.follow_date || '')" @change="onDateChange('follow_date', $event)">
              <view class="input" :class="{ empty: !form.follow_date }">{{ form.follow_date || '请选择实际评估日期' }}</view>
            </picker>
          </view>

          <view class="field">
            <view class="label-row"><text class="label">随访计划日期</text></view>
            <view class="row-2">
              <picker mode="date" :value="String(form.plan_date_start || '')" @change="onDateChange('plan_date_start', $event)">
                <view class="input" :class="{ empty: !form.plan_date_start }">{{ form.plan_date_start || '开始日期' }}</view>
              </picker>
              <picker mode="date" :value="String(form.plan_date_end || '')" @change="onDateChange('plan_date_end', $event)">
                <view class="input" :class="{ empty: !form.plan_date_end }">{{ form.plan_date_end || '结束日期' }}</view>
              </picker>
            </view>
          </view>

          <view class="field">
            <view class="label-row"><text class="label">随访科室</text></view>
            <picker :range="FOLLOWUP_DEPTS" @change="onPicker('follow_dept', $event as any, FOLLOWUP_DEPTS)">
              <view class="input" :class="{ empty: !form.follow_dept }">{{ form.follow_dept || '请选择随访科室' }}</view>
            </picker>
          </view>

          <view class="field">
            <view class="label-row"><text class="label">随访人</text></view>
            <input v-model="form.follow_user" class="input" placeholder="随访人姓名" placeholder-class="ph" />
          </view>

          <view class="field">
            <view class="label-row"><text class="label">非计划入院</text></view>
            <view class="option-row">
              <view
                v-for="o in YES_NO"
                :key="o"
                class="option"
                :class="{ active: form.unplanned_admission === o }"
                @click="setOption('unplanned_admission', o)"
              >{{ o }}</view>
            </view>
          </view>

          <view class="field">
            <view class="label-row"><text class="label">信息获取途径 <text class="req">*</text></text></view>
            <picker :range="INFO_CHANNELS" @change="onPicker('info_channel', $event as any, INFO_CHANNELS)">
              <view class="input" :class="{ empty: !form.info_channel }">{{ form.info_channel || '请选择信息获取途径' }}</view>
            </picker>
          </view>

          <view class="field">
            <view class="label-row"><text class="label">随访状态 <text class="req">*</text></text></view>
            <view class="option-row">
              <view
                v-for="o in survivalOptions"
                :key="o.value"
                class="option"
                :class="{ active: form.survival_status === o.value }"
                @click="setOption('survival_status', o.value)"
              >{{ o.label }}</view>
            </view>
          </view>

          <view class="field">
            <view class="label-row"><text class="label">目前状况 <text class="req">*</text></text></view>
            <picker :range="CURRENT_CONDITIONS" @change="onPicker('current_condition', $event as any, CURRENT_CONDITIONS)">
              <view class="input" :class="{ empty: !form.current_condition }">{{ form.current_condition || '请选择目前状况' }}</view>
            </picker>
          </view>

          <view class="field">
            <view class="label-row"><text class="label">加入心脏康复计划 <text class="req">*</text></text></view>
            <view class="option-row">
              <view
                v-for="o in YES_NO"
                :key="o"
                class="option"
                :class="{ active: form.cardiac_rehab === o }"
                @click="setOption('cardiac_rehab', o)"
              >{{ o }}</view>
            </view>
          </view>

          <view class="field">
            <view class="label-row">
              <text class="label">出院后主要心血管不良事件 <text class="req">*</text></text>
              <text class="counter" :class="{ warn: String(form.mace || '').length > LIMITS.mace - 20 }">{{ String(form.mace || '').length }}/{{ LIMITS.mace }}</text>
            </view>
            <textarea v-model="form.mace" class="textarea" :maxlength="LIMITS.mace" :placeholder="`如：${MACE_OPTIONS.join('、')}`" placeholder-class="ph" />
          </view>
        </view>

        <!-- 危险因素控制 -->
        <view class="card">
          <view class="card-title">危险因素控制</view>
          <view v-for="fld in REACH_FIELDS" :key="fld.key" class="field">
            <view class="label-row"><text class="label">{{ fld.label }}</text></view>
            <view class="option-row">
              <view
                v-for="o in REACH_STATUS"
                :key="o"
                class="option"
                :class="{ active: form[fld.key] === o }"
                @click="setOption(fld.key, o)"
              >{{ o }}</view>
            </view>
          </view>

          <view class="field">
            <view class="label-row"><text class="label">吸烟</text></view>
            <view class="option-row">
              <view
                v-for="o in YES_NO"
                :key="o"
                class="option"
                :class="{ active: form.smoking === o }"
                @click="setOption('smoking', o)"
              >{{ o }}</view>
            </view>
          </view>

          <view class="field">
            <view class="label-row"><text class="label">饮酒</text></view>
            <view class="option-row">
              <view
                v-for="o in YES_NO"
                :key="o"
                class="option"
                :class="{ active: form.alcohol === o }"
                @click="setOption('alcohol', o)"
              >{{ o }}</view>
            </view>
          </view>

          <view class="field">
            <view class="label-row"><text class="label">身高（cm）</text></view>
            <input v-model="form.height" class="input" type="number" placeholder="请输入身高" placeholder-class="ph" />
          </view>

          <view class="field">
            <view class="label-row"><text class="label">体重（kg）</text></view>
            <input v-model="form.weight" class="input" type="digit" placeholder="请输入体重" placeholder-class="ph" />
          </view>

          <view class="field">
            <view class="label-row"><text class="label">BMI</text></view>
            <view class="input bmi-input">{{ form.bmi || '填写身高体重后自动计算' }}</view>
          </view>
        </view>

        <!-- 躯体症状与心功能评价 -->
        <view class="card">
          <view class="card-title">躯体症状与心功能评价</view>
          <view class="field">
            <view class="label-row"><text class="label">躯体症状</text></view>
            <picker :range="SYMPTOMS" @change="onPicker('symptoms', $event as any, SYMPTOMS)">
              <view class="input" :class="{ empty: !form.symptoms }">{{ form.symptoms || '请选择躯体症状' }}</view>
            </picker>
          </view>
          <view class="field">
            <view class="label-row"><text class="label">心脏纽约分级（NYHA）</text></view>
            <picker :range="NYHA_LEVELS" @change="onPicker('nyha', $event as any, NYHA_LEVELS)">
              <view class="input" :class="{ empty: !form.nyha }">{{ form.nyha || '请选择 NYHA 分级' }}</view>
            </picker>
          </view>
        </view>

        <!-- 心电图 -->
        <view class="card">
          <view class="card-title">心电图</view>
          <view class="field">
            <view class="label-row">
              <text class="label">心电图图片</text>
              <view class="ai-badge" @click="showAiTip">
                <text>🤖 AI</text>
              </view>
            </view>
            <view v-if="!form.ecg_image" class="upload-box" @click="chooseEcgImage">
              <text class="upload-icon">📷</text>
              <text class="upload-text">点击拍照 / 从相册选择</text>
            </view>
            <view v-else class="preview-wrap">
              <image :src="imgSrc(form.ecg_image)" class="preview" mode="aspectFit" @click="chooseEcgImage" />
              <view class="img-actions">
                <view class="img-btn" @click="chooseEcgImage">重新选择</view>
                <view class="img-btn danger" @click="form.ecg_image = ''">删除</view>
              </view>
            </view>
          </view>
          <view class="field">
            <view class="label-row"><text class="label">心电图结果</text></view>
            <picker :range="EXAM_STATUS" @change="onPicker('ecg_result', $event as any, EXAM_STATUS)">
              <view class="input" :class="{ empty: !form.ecg_result }">{{ form.ecg_result || '请选择心电图结果' }}</view>
            </picker>
          </view>
        </view>

        <!-- 检查项目 -->
        <view class="card">
          <view class="card-title">检查项目</view>
          <view v-for="fld in EXAM_FIELDS" :key="fld.key" class="field">
            <view class="label-row"><text class="label">{{ fld.label }}</text></view>
            <view class="option-row">
              <view
                v-for="o in EXAM_STATUS"
                :key="o"
                class="option"
                :class="{ active: form[fld.key] === o }"
                @click="setOption(fld.key, o)"
              >{{ o }}</view>
            </view>
          </view>
        </view>

        <!-- 用药情况 -->
        <view class="card">
          <view class="card-title">用药情况</view>
          <view v-for="fld in MED_FIELDS" :key="fld.key" class="field">
            <view class="label-row"><text class="label">{{ fld.label }}</text></view>
            <view class="option-row">
              <view
                v-for="o in YES_NO"
                :key="o"
                class="option"
                :class="{ active: form[fld.key] === o }"
                @click="setOption(fld.key, o)"
              >{{ o }}</view>
            </view>
          </view>
        </view>

        <!-- 备注 / 失访原因 -->
        <view class="card">
          <view class="card-title">备注</view>
          <view class="field">
            <view class="label-row">
              <text class="label">{{ form.follow_status === 'unfollowed' ? '失访原因' : '备注' }}</text>
              <text class="counter" :class="{ warn: String(form.remark || '').length > LIMITS.remark - 50 }">{{ String(form.remark || '').length }}/{{ LIMITS.remark }}</text>
            </view>
            <textarea
              v-model="form.remark"
              class="textarea"
              :maxlength="LIMITS.remark"
              :placeholder="form.follow_status === 'unfollowed' ? '可记录失访原因（如：多次拨打无人接听）' : '其他随访记录'"
              placeholder-class="ph"
            />
          </view>
        </view>
      </template>

      <button v-if="!isSubmitted" class="submit-btn" :disabled="submitting" @click="handleSubmit">
        {{ submitting ? '提交中...' : '提交随访' }}
      </button>
      <view v-else class="submitted-tip">该随访已提交，不可修改</view>
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
.sum-row { display: flex; align-items: center; gap: 16rpx; }
.sum-name { font-size: 38rpx; font-weight: 700; color: #ffffff; }
.sum-meta { display: flex; align-items: center; gap: 12rpx; }
.gender { font-size: 30rpx; color: #ffffff; font-weight: 600; }
.age { font-size: 26rpx; color: rgba(255, 255, 255, 0.9); }
.diag-badge {
  background: rgba(255, 255, 255, 0.25);
  color: #ffffff;
  padding: 4rpx 14rpx;
  border-radius: 12rpx;
  font-size: 22rpx;
  font-weight: 500;
}
.sum-case { margin-top: 10rpx; font-size: 24rpx; color: rgba(255, 255, 255, 0.85); }
.sum-due-row { margin-top: 12rpx; display: flex; align-items: center; justify-content: space-between; }
.sum-due { font-size: 26rpx; color: #ffffff; }
.sum-status { font-size: 22rpx; padding: 6rpx 18rpx; border-radius: 18rpx; font-weight: 500; }
.st-done { background: #ffffff; color: #059669; }
.st-overdue { background: rgba(255, 255, 255, 0.9); color: #6b7280; }
.st-active { background: #f97316; color: #ffffff; }
.st-default { background: rgba(255, 255, 255, 0.85); color: #374151; }

.card { padding: 32rpx; border-radius: 24rpx; background: #ffffff; margin-bottom: 24rpx; }
.card-title {
  font-size: 28rpx;
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 20rpx;
  padding-left: 14rpx;
  border-left: 6rpx solid #10b981;
}

.info-row { display: flex; justify-content: space-between; margin-top: 12rpx; }
.info-item { display: flex; align-items: center; gap: 10rpx; }
.info-label { font-size: 26rpx; color: #9ca3af; }
.info-val { font-size: 26rpx; color: #1f2937; }

.come-badge {
  padding: 6rpx 18rpx;
  border-radius: 6rpx;
  font-size: 24rpx;
  color: #ffffff;
  font-weight: 500;
}
.come-120 { background: #ef4444; }
.come-transfer { background: #f59e0b; }
.come-self { background: #10b981; }
.come-default { background: #9ca3af; }

.phone-row {
  display: flex;
  align-items: center;
  gap: 12rpx;
  margin-top: 24rpx;
  padding: 20rpx 24rpx;
  border-radius: 16rpx;
  background: #f8f9fb;
}
.phone-icon { font-size: 30rpx; }
.phone-val { flex: 1; font-size: 28rpx; color: #2563eb; font-weight: 500; }
.phone-tip { font-size: 24rpx; color: #9ca3af; }

/* 只读网格 */
.read-grid { display: flex; flex-wrap: wrap; gap: 20rpx 32rpx; }
.read-item { display: flex; flex-direction: column; gap: 8rpx; min-width: 200rpx; }
.read-item.full { flex: 1 1 100%; }
.read-label { font-size: 24rpx; color: #9ca3af; }
.read-val { font-size: 28rpx; color: #1f2937; font-weight: 500; }
.val-yes { color: #059669; }
.val-no { color: #ef4444; }

.block-val {
  display: block;
  font-size: 28rpx;
  color: #1f2937;
  line-height: 1.6;
  padding: 20rpx 24rpx;
  border-radius: 16rpx;
  background: #f8f9fb;
}
.submit-time { margin-top: 24rpx; font-size: 24rpx; color: #9ca3af; }

.field { margin-bottom: 28rpx; }
.label-row { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12rpx; }
.label-row .label { margin-bottom: 0; }
.label { display: block; font-size: 26rpx; color: #4b5563; }
.req { color: #ef4444; }
.optional { font-size: 22rpx; color: #9ca3af; }
.counter { font-size: 24rpx; color: #9ca3af; }
.counter.warn { color: #f59e0b; }

.input {
  height: 88rpx;
  line-height: 88rpx;
  padding: 0 24rpx;
  border-radius: 16rpx;
  background: #f3f4f6;
  font-size: 30rpx;
  color: #1f2937;
  box-sizing: border-box;
}
.input.empty { color: #9ca3af; }
.bmi-input { color: #10b981; font-weight: 600; }
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

.row-2 { display: flex; gap: 16rpx; }
.row-2 .input { flex: 1; }

.option-row { display: flex; gap: 16rpx; flex-wrap: wrap; }
.option {
  padding: 14rpx 32rpx;
  border-radius: 16rpx;
  background: #f3f4f6;
  font-size: 26rpx;
  color: #4b5563;
}
.option.active { background: #10b981; color: #ffffff; }

.ai-badge {
  padding: 4rpx 16rpx;
  border-radius: 12rpx;
  background: #ecfdf5;
  font-size: 22rpx;
  color: #059669;
}

/* 心电图图片上传 */
.upload-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12rpx;
  height: 220rpx;
  border-radius: 16rpx;
  border: 2rpx dashed #cbd5e1;
  background: #f8fafc;
}
.upload-icon { font-size: 52rpx; }
.upload-text { font-size: 26rpx; color: #9ca3af; }
.preview-wrap { display: flex; flex-direction: column; gap: 16rpx; }
.preview {
  width: 100%;
  height: 360rpx;
  border-radius: 16rpx;
  background: #f3f4f6;
}
.img-actions { display: flex; gap: 16rpx; }
.img-btn {
  padding: 14rpx 32rpx;
  border-radius: 16rpx;
  background: #ecfdf5;
  font-size: 26rpx;
  color: #059669;
  font-weight: 500;
}
.img-btn.danger { background: #fef2f2; color: #ef4444; }
.read-img {
  width: 100%;
  height: 360rpx;
  border-radius: 16rpx;
  background: #f3f4f6;
  margin-top: 8rpx;
}

.submit-btn {
  margin-top: 8rpx;
  height: 92rpx;
  line-height: 92rpx;
  border-radius: 20rpx;
  background: linear-gradient(135deg, #10b981, #0ea5e9);
  color: #ffffff;
  font-size: 30rpx;
  font-weight: 600;
}
.submit-btn::after { border: none; }
.submitted-tip { text-align: center; margin-top: 20rpx; font-size: 26rpx; color: #9ca3af; }
</style>
