<!-- 数据直报：病例编辑（模板驱动的动态表单，分类与字段由 caseDetail.fields 提供） -->
<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import DoctorAPI, { type TemplateField, type EcgConsultItem } from '@/api/module_cpx/doctor'
import { useUserStore } from '@/store/userStore'
import { http, getApiBaseUrl } from '@/http'
import { safeBack } from '@/utils/back'

definePage({
  name: 'case-fill',
  style: { navigationStyle: 'custom' },
})

const statusBarHeight = uni.getSystemInfoSync().statusBarHeight || 0

function goBack() {
  safeBack()
}

const BASE_URL = getApiBaseUrl()
const userStore = useUserStore()

/** 图片字段 URL 补全 */
function imgSrc(url: unknown) {
  const s = String(url || '')
  if (!s) return ''
  if (s.startsWith('http'))
    return s
  return `${BASE_URL}${s}`
}

/** 上传图片（拍照/相册 → 后端 → 返回 URL 写入 form_data） */
function uploadImage(f: TemplateField) {
  uni.chooseImage({
    count: 1,
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
              formData[f.field_code] = d.data.url
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

const caseId = ref(0)
const loading = ref(false)
const saving = ref(false)
const submitting = ref(false)
const tplFields = ref<TemplateField[]>([])
const templateId = ref<number>(0)
const templateName = ref<string>('')
const activeTab = ref('')
const caseInfo = ref<{ case_no?: string; patient_name?: string; status?: string; audit_records?: any[] }>({})
const formData = reactive<Record<string, unknown>>({})

/** 本病例关联的远程心电记录（用于与数据直报「接收远程心电图」保持一致） */
const ecgRecords = ref<EcgConsultItem[]>([])

/** 取最新一条含图片的远程心电记录图片（ecg_records 已按时间倒序） */
function latestRemoteEcgImage(): string | null {
  const withImg = (ecgRecords.value || []).filter((e) => e.image_path)
  return withImg.length ? (withImg[0].image_path as string) : null
}

const FIELD_TYPE_LABEL: Record<string, string> = {
  text: '文本', number: '数字', date: '日期', time: '时间', datetime: '日期时间', select: '选择', image: '图片',
}

/** 分类（tab）从模板字段动态生成，按 tab_order 升序 */
const tabs = computed(() => {
  const map = new Map<string, { key: string; name: string; order: number }>()
  tplFields.value.forEach((f) => {
    const k = f.tab_name || '未分类'
    if (!map.has(k))
      map.set(k, { key: k, name: k, order: f.tab_order || 0 })
  })
  return Array.from(map.values()).sort((a, b) => a.order - b.order)
})

const fieldsByTab = computed(() => {
  const map: Record<string, TemplateField[]> = {}
  tplFields.value.forEach((f) => {
    const k = f.tab_name || '未分类'
    ;(map[k] = map[k] || []).push(f)
  })
  Object.values(map).forEach((arr) => arr.sort((a, b) => (a.sort_num || 0) - (b.sort_num || 0)))
  return map
})

const currentFields = computed(() => fieldsByTab.value[activeTab.value] || [])

onLoad(async (query) => {
  caseId.value = Number(query?.id || 0)
  if (!caseId.value) return
  loading.value = true
  try {
    const detail = await DoctorAPI.caseDetail(caseId.value)
    tplFields.value = detail.fields || []
    templateId.value = detail.template_id || 0
    templateName.value = detail.template_name || ''
    caseInfo.value = {
      case_no: detail.case_no,
      patient_name: detail.patient_name,
      status: detail.status,
      audit_records: detail.audit_records,
    }
    // 已有表单数据
    Object.keys(detail.form_data || {}).forEach((k) => {
      formData[k] = detail.form_data[k]
    })
    // 基本信息自动带入（建档已填的全部字段，按模板 field_code 回填到对应字段）
    const base = {
      patient_name: detail.patient_name,
      gender: detail.gender,
      age: detail.age,
      phone: detail.phone,
      come_type: detail.come_type,
      diagnose_type: detail.diagnose_type,
      id_type: detail.id_type,
      id_number: detail.id_number,
      birth_date: detail.birth_date,
      onset_address: detail.onset_address,
      detail_address: detail.detail_address,
      insurance_type: detail.insurance_type,
      insurance_no: detail.insurance_no,
      first_contact_time: detail.first_contact_time,
    }
    Object.keys(base).forEach((k) => {
      const v = (base as Record<string, unknown>)[k]
      if (v !== undefined && v !== null && v !== '' && (formData[k] === undefined || formData[k] === ''))
        formData[k] = v
    })
    // 远程心电图 ↔ 数据直报「接收远程心电图」保持一致：合诊患者（已关联远程心电记录）自动导入图片
    ecgRecords.value = (detail.ecg_records as EcgConsultItem[] | undefined) || []
    const hasRemoteField = tplFields.value.some((f) => f.field_code === 'remote_ecg_receive')
    const ecgImg = latestRemoteEcgImage()
    if (hasRemoteField && ecgImg)
      formData['remote_ecg_receive'] = ecgImg
    // 默认激活第一个分类
    if (tabs.value.length)
      activeTab.value = tabs.value[0].key
  }
  finally {
    loading.value = false
  }
})

// ── 自动保存（防抖 3s） ──────────────────────────────
let autoSaveTimer: ReturnType<typeof setTimeout> | null = null
watch(formData, () => {
  if (!caseId.value || loading.value || !templateId.value)
    return
  if (autoSaveTimer)
    clearTimeout(autoSaveTimer)
  autoSaveTimer = setTimeout(() => {
    const s = caseInfo.value.status
    if (s !== 'draft' && s !== 'rejected')
      return
    DoctorAPI.saveForm(caseId.value, { template_id: templateId.value, form_data: { ...formData } })
      .catch(() => { /* 静默失败，下次变化重试 */ })
  }, 3000)
}, { deep: true })

// ── 字段渲染辅助 ──────────────────────────────────────

/** select 选项归一：模板字段存字符串数组或 {label,value}，统一成 {label,value} */
function options(f: TemplateField) {
  const opts = f.field_options
  if (!Array.isArray(opts)) return []
  return opts.map((o: any) => (typeof o === 'string' ? { label: o, value: o } : { label: o.label, value: o.value }))
}

/** datetime 字段拆分：value -> { date, time } */
function datePart(f: TemplateField) { return String(formData[f.field_code] || '').slice(0, 10) }
function timePart(f: TemplateField) { return String(formData[f.field_code] || '').slice(11, 16) }
function onDateChange(f: TemplateField, e: any) { formData[f.field_code] = `${e.detail.value} ${timePart(f) || '00:00'}` }
function onTimeChange(f: TemplateField, e: any) { formData[f.field_code] = `${datePart(f) || todayStr()} ${e.detail.value}` }
function todayStr() {
  const n = new Date()
  const p = (x: number) => String(x).padStart(2, '0')
  return `${n.getFullYear()}-${p(n.getMonth() + 1)}-${p(n.getDate())}`
}
function nowStr() {
  const n = new Date()
  const p = (x: number) => String(x).padStart(2, '0')
  return `${todayStr()} ${p(n.getHours())}:${p(n.getMinutes())}`
}
function setNow(f: TemplateField) { formData[f.field_code] = nowStr() }

function onText(f: TemplateField, e: any) { formData[f.field_code] = e.detail.value }
function onNumber(f: TemplateField, e: any) { formData[f.field_code] = e.detail.value }
function onSelect(f: TemplateField, val: string) { formData[f.field_code] = val }

/** IP 定位兜底：原生定位被浏览器安全策略拦截（局域网 IP / 非 https）时，按出口 IP 定位到省市区 */
function ipLocate(f: TemplateField) {
  uni.showLoading({ title: 'IP 定位中...' })
  uni.request({
    url: 'https://whois.pconline.com.cn/ipJson.jsp?json=true',
    timeout: 8000,
    success: (res) => {
      uni.hideLoading()
      try {
        const d = typeof res.data === 'string' ? JSON.parse(res.data.trim()) : res.data
        const addr = [d.pro, d.city, d.region].filter(Boolean).join('')
        if (addr) {
          formData[f.field_code] = addr
          uni.showToast({ title: `已定位（IP定位：${addr}）`, icon: 'none' })
        }
        else {
          uni.showToast({ title: '定位失败，请手动输入', icon: 'none' })
        }
      }
      catch {
        uni.showToast({ title: '定位失败，请手动输入', icon: 'none' })
      }
    },
    fail: () => {
      uni.hideLoading()
      uni.showToast({ title: '定位失败，请手动输入', icon: 'none' })
    },
  })
}

/** 发病地址定位：H5 优先浏览器原生定位，失败自动降级 IP 定位（保证局域网 IP 访问也能用）；App/小程序用地图选择 */
function locateAddress(f: TemplateField) {
  // #ifdef H5
  // H5：uni.chooseLocation 依赖地图 key 且需 https，直接用浏览器原生定位；
  // 非安全上下文（局域网 IP / 非 https）会被浏览器拒绝 → 自动降级 IP 定位，不再让用户手动输入
  if (typeof navigator !== 'undefined' && navigator.geolocation) {
    uni.showLoading({ title: '定位中...' })
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        uni.hideLoading()
        const lat = pos.coords.latitude
        const lng = pos.coords.longitude
        formData[f.field_code] = `${lat.toFixed(6)},${lng.toFixed(6)}`
        uni.showToast({ title: '已获取当前位置坐标', icon: 'none' })
      },
      () => {
        uni.hideLoading()
        ipLocate(f)
      },
      { enableHighAccuracy: false, timeout: 6000 },
    )
    return
  }
  // #endif
  uni.chooseLocation({
    success: (res) => {
      formData[f.field_code] = res.address || res.name || ''
      if (!formData[f.field_code] && res.latitude)
        formData[f.field_code] = `${res.latitude.toFixed(4)},${res.longitude.toFixed(4)}`
    },
    fail: () => {
      uni.showToast({ title: '定位失败，请手动输入', icon: 'none' })
    },
  })
}

/** 急诊分诊 Tab：院前体征同步回显（仅当模板包含这些字段码时显示） */
const preVitalCodes = ['consciousness', 'respiration', 'pulse', 'pre_heart_rate', 'pre_blood_pressure', 'pre_temp']
const preVitalValues = computed(() => {
  return preVitalCodes
    .map((code) => tplFields.value.find((f) => f.field_code === code))
    .filter(Boolean)
    .map((f) => ({
      name: f!.field_name,
      value: formData[f!.field_code] === undefined || formData[f!.field_code] === '' ? '未采集' : String(formData[f!.field_code]),
    }))
})
const showPreVital = computed(() => activeTab.value === '急诊分诊' && preVitalValues.value.length > 0)

const canEdit = computed(() => {
  const s = caseInfo.value.status
  return s === 'draft' || s === 'rejected'
})

// ── 保存 / 提交 ──────────────────────────────────────

async function handleSave() {
  if (!templateId.value) return
  if (!canEdit.value) {
    uni.showToast({ title: '当前状态不可编辑，仅草稿/驳回可修改', icon: 'none' })
    return
  }
  saving.value = true
  try {
    await DoctorAPI.saveForm(caseId.value, { template_id: templateId.value, form_data: { ...formData } })
    uni.showToast({ title: '草稿已保存', icon: 'success' })
  }
  catch { /* toast by http */ }
  finally { saving.value = false }
}

async function handleSubmit() {
  if (!templateId.value) return
  if (!canEdit.value) {
    uni.showToast({ title: '当前状态不可编辑，仅草稿/驳回可修改', icon: 'none' })
    return
  }
  submitting.value = true
  try {
    await DoctorAPI.saveForm(caseId.value, { template_id: templateId.value, form_data: { ...formData } })
    await DoctorAPI.submitCase(caseId.value)
    // 立即同步状态，避免残留的自动保存定时器带着旧状态（draft）再去存导致 400/500
    caseInfo.value = { ...caseInfo.value, status: 'submitted' }
    uni.showToast({ title: '提交成功，已进入审核', icon: 'success' })
    setTimeout(() => safeBack(), 800)
  }
  catch { /* toast by http */ }
  finally { submitting.value = false }
}

// ── 跳转辅助页 ────────────────────────────────────────
function goTimeline() { uni.navigateTo({ url: `/pages/case/timeline?id=${caseId.value}` }) }
function goAnalysis() { uni.navigateTo({ url: `/pages/case/analysis?id=${caseId.value}` }) }
function goTime() { uni.navigateTo({ url: `/pages/case/time?id=${caseId.value}` }) }

/** 图片上传到服务器（复用后端图片接口） */
function uploadToServer(filePath: string, onSuccess: (url: string) => void) {
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
        if (d.code === 0 && d.data?.url) onSuccess(d.data.url)
        else uni.showToast({ title: d.msg || '上传失败', icon: 'none' })
      }
      catch { uni.showToast({ title: '上传失败', icon: 'none' }) }
    },
    fail: () => { uni.hideLoading(); uni.showToast({ title: '上传失败', icon: 'none' }) },
  })
}

/** 证件识别（拍照/选择图片 → 上传 → 自动填入当前 Tab 的图片字段） */
function idCardEntry() {
  uni.showActionSheet({
    itemList: ['拍照', '从相册选择'],
    success: (res) => {
      const sourceType = res.tapIndex === 0 ? ['camera'] : ['album']
      uni.chooseImage({
        count: 1,
        sourceType,
        success: (chooseRes) => {
          const filePath = chooseRes.tempFilePaths[0]
          uploadToServer(filePath, (url) => {
            const imgField = currentFields.value.find(f => f.field_type === 'image')
            if (imgField) {
              formData[imgField.field_code] = url
              uni.showToast({ title: `已填入「${imgField.field_name}」`, icon: 'success' })
            }
            else {
              uni.showToast({ title: '图片已上传，请在图片字段中选择', icon: 'none' })
            }
          })
        },
      })
    },
  })
}

/** 导入远程心电图：合诊患者（已关联远程心电记录）自动填入图片；非合诊患者提示但仍可手动填 */
function importRemoteEcg() {
  const img = latestRemoteEcgImage()
  if (img) {
    formData['remote_ecg_receive'] = img
    uni.showToast({ title: '已导入远程心电图', icon: 'success' })
  }
  else {
    uni.showModal({
      title: '该患者不是合诊患者',
      content: '该患者暂无远程心电记录，无法自动导入。你仍可在下方手动拍照或选择心电图图片填入「接收远程心电图」。',
      showCancel: false,
    })
  }
}

/** AI 智能识别：图片识别（调用后端通义千问 Vision）/ 语音识别（Web Speech API + 后端解析） */
function aiEntry() {
  uni.showActionSheet({
    itemList: ['图片识别', '语音识别'],
    success: (res) => {
      if (res.tapIndex === 0) {
        // 图片识别：拍照/选择 → 上传 → 调用后端 AI Vision 接口 → 回填
        uni.chooseImage({
          count: 1,
          sourceType: ['camera', 'album'],
          success: (chooseRes) => {
            uni.showLoading({ title: 'AI 识别中...' })
            uploadToServer(chooseRes.tempFilePaths[0], async (url) => {
              try {
                const result = await http.Post('/cpx/doctor/ai/recognize', { image_url: url }) as Record<string, string>
                fillFormData(result)
              }
              catch {
                uni.hideLoading()
                uni.showToast({ title: 'AI 识别失败，请重试', icon: 'none' })
              }
            })
          },
        })
      }
      else {
        // 语音识别：H5 用 Web Speech API，否则降级手动输入
        startVoiceRecognition()
      }
    },
  })
}

/** 语音识别：优先 Web Speech API（H5原生），降级手动输入 */
function startVoiceRecognition() {
  // #ifdef H5
  if (typeof window !== 'undefined' && ('SpeechRecognition' in (window as any) || 'webkitSpeechRecognition' in (window as any))) {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
    const recognition = new SpeechRecognition()
    recognition.lang = 'zh-CN'
    recognition.interimResults = false
    recognition.maxAlternatives = 1
    uni.showLoading({ title: '正在聆听...' })
    recognition.onresult = async (event: any) => {
      uni.hideLoading()
      const text = event.results[0][0].transcript
      uni.showToast({ title: `识别到：${text.slice(0, 20)}...`, icon: 'none', duration: 2000 })
      try {
        const result = await http.Post('/cpx/doctor/ai/recognize', { text }) as Record<string, string>
        fillFormData(result)
      }
      catch {
        uni.showToast({ title: 'AI 解析失败', icon: 'none' })
      }
    }
    recognition.onerror = () => { uni.hideLoading(); uni.showToast({ title: '语音识别失败，请重试', icon: 'none' }) }
    recognition.start()
    return
  }
  // #endif
  // 降级：手动输入
  voiceInputManual()
}

/** 手动输入文字 → 调用后端 AI 解析（降级方案） */
function voiceInputManual() {
  uni.showModal({
    title: 'AI 文字识别',
    editable: true,
    placeholderText: '请输入识别到的文字，如「患者李四，男，58岁，电话13812345678」',
    success: async (res) => {
      if (!res.confirm || !res.content) return
      try {
        const result = await http.Post('/cpx/doctor/ai/recognize', { text: res.content }) as Record<string, string>
        fillFormData(result)
      }
      catch {
        uni.showToast({ title: 'AI 解析失败', icon: 'none' })
      }
    },
  })
}

/** 将 AI 识别结果回填到 form_data（按 field_code 匹配） */
function fillFormData(info: Record<string, string>) {
  // AI 返回字段（标准编码/中文名）→ 模板表单 field_code 动态映射
  const fieldAlias: Record<string, string> = {
    patient_name: 'patient_name', '姓名': 'patient_name', '患者姓名': 'patient_name',
    gender: 'gender', '性别': 'gender',
    age: 'age', '年龄': 'age',
    birth_date: 'birth_date', '出生日期': 'birth_date',
    id_number: 'id_number', '身份证号': 'id_number',
    id_type: 'id_type', '证件类型': 'id_type', 'card_type': 'card_type',
    phone: 'phone', '联系电话': 'phone', '电话': 'phone',
    come_type: 'come_type', '来院方式': 'come_type',
    onset_address: 'onset_address', '发病地址': 'onset_address',
    detail_address: 'detail_address', '详细地址': 'detail_address',
    insurance_type: 'insurance_type', '医保类型': 'insurance_type', 'insurance': 'insurance',
    insurance_no: 'insurance_no', '医保编号': 'insurance_no', '医保号': 'insurance_no',
    chief_complaint: 'chief_complaint', '主诉': 'chief_complaint',
    diagnose_type: 'diagnose_type', '诊断': 'diagnose_type', '诊断类型': 'diagnose_type',
  }
  // 模板实际存在的 field_code 集合：模型若直接返回标准编码（如 fmc_time）可精准命中
  const tplCodes = new Set((tplFields.value || []).map((f: any) => f.field_code))
  let filled = 0
  const details: string[] = []
  const unmatched: string[] = []
  for (const [k, v] of Object.entries(info)) {
    if (!v) continue
    let code = fieldAlias[k] || fieldAlias[String(k).trim()]
    if (!code && tplCodes.has(k)) code = k
    if (code && formData[code] !== undefined) {
      formData[code] = v
      filled++
      details.push(`${code}=${v}`)
    }
    else if (!code) {
      unmatched.push(`${k}=${v}`)
    }
  }
  if (filled > 0) {
    let content = `已自动填入 ${filled} 个字段，请核对：\n${details.join('\n')}`
    if (unmatched.length) {
      const head = unmatched.slice(0, 5).join('、') + (unmatched.length > 5 ? '…' : '')
      content += `\n\n另有 ${unmatched.length} 项未匹配到当前模板字段（${head}），请手动补充`
    }
    uni.showModal({ title: 'AI 识别完成', content, showCancel: false })
  }
  else if (unmatched.length) {
    const head = unmatched.slice(0, 5).join('、') + (unmatched.length > 5 ? '…' : '')
    uni.showModal({
      title: 'AI 识别结果',
      content: `识别到 ${unmatched.length} 项，但当前模板暂无对应字段可填入（${head}），请手动补充`,
      showCancel: false,
    })
  }
  else {
    uni.showToast({ title: '未识别到可填入的字段信息', icon: 'none' })
  }
}
</script>

<template>
  <view class="fill-page">
    <!-- 自定义蓝色导航栏 -->
    <view class="nav-bar" :style="{ paddingTop: `${statusBarHeight}px` }">
      <view class="nav-back" @click="goBack">‹</view>
      <text class="nav-title">病例填报</text>
      <view class="nav-right">
        <view class="nav-icon-btn" @click="idCardEntry">
          <image class="nav-icon-img" src="/static/icons/camera.png" mode="aspectFit" />
        </view>
        <view class="nav-icon-btn" @click="aiEntry">
          <image class="nav-icon-img" src="/static/icons/ai_chat.png" mode="aspectFit" />
        </view>
      </view>
    </view>

    <view class="page-body">
    <view v-if="loading" class="loading">加载中...</view>

    <template v-else-if="caseId">
      <!-- 概要 -->
      <view class="summary">
        <view class="summary-top">
          <text class="summary-name">{{ caseInfo.patient_name || '-' }}</text>
          <text class="summary-no">{{ caseInfo.case_no }}</text>
        </view>
        <view class="summary-meta">
          <text class="summary-tpl">使用模板：{{ templateName || '未选择' }}</text>
        </view>
        <view class="summary-actions">
          <text class="summary-link" @click="goTime">⏱ 时间采集</text>
          <text class="summary-link" @click="goTimeline">📊 时间轴</text>
          <text class="summary-link" @click="goAnalysis">📈 病例分析</text>
        </view>
      </view>

      <!-- 驳回提示 -->
      <view v-if="caseInfo.status === 'rejected'" class="reject-tip">
        <text class="tip-title">病例被驳回，请修改后重新提交</text>
        <view v-for="a in caseInfo.audit_records || []" :key="a.id" class="tip-item">
          <text>审核意见：{{ a.audit_comment || '（无意见）' }}</text>
        </view>
      </view>

      <!-- Tab 切换 -->
      <scroll-view v-if="tabs.length" scroll-x class="tab-bar">
        <view
          v-for="t in tabs"
          :key="t.key"
          class="tab-item"
          :class="{ active: activeTab === t.key }"
          @click="activeTab = t.key"
        >
          {{ t.name }}
        </view>
      </scroll-view>
      <view v-else class="no-tpl-tip">该病例模板未配置字段</view>

      <!-- 字段表单 -->
      <view v-if="tabs.length" class="form-card">
        <!-- 急诊分诊：院前体征同步 -->
        <view v-if="showPreVital" class="pre-vital-box">
          <text class="pre-vital-title">院前体征同步</text>
          <view class="pre-vital-grid">
            <view v-for="p in preVitalValues" :key="p.name" class="pre-vital-item">
              <text class="pre-vital-name">{{ p.name }}</text>
              <text class="pre-vital-value">{{ p.value }}</text>
            </view>
          </view>
          <text class="pre-vital-tip">数据来自「院前急救」Tab，可返回修改</text>
        </view>

        <view v-for="f in currentFields" :key="f.id" class="field">
          <text class="field-label">
            {{ f.field_name }}<text v-if="f.required_flag === 1" class="req"> *</text>
            <text class="field-type">{{ FIELD_TYPE_LABEL[f.field_type] || f.field_type }}</text>
          </text>

          <!-- 文本 -->
          <view v-if="f.field_type === 'text'" class="text-row">
            <input
              :model-value="String(formData[f.field_code] ?? '')"
              class="field-input"
              :placeholder="`请输入${f.field_name}`"
              placeholder-class="ph"
              @input="onText(f, $event)"
            />
            <view v-if="f.field_code === 'onset_address'" class="locate-btn" @click="locateAddress(f)">📍定位</view>
          </view>

          <!-- 数字 -->
          <input
            v-else-if="f.field_type === 'number'"
            :model-value="String(formData[f.field_code] ?? '')"
            class="field-input"
            type="digit"
            :placeholder="`请输入${f.field_name}`"
            placeholder-class="ph"
            @input="onNumber(f, $event)"
          />

          <!-- 日期 -->
          <picker v-else-if="f.field_type === 'date'" mode="date" :value="String(formData[f.field_code] || '')" @change="formData[f.field_code] = $event.detail.value">
            <view class="field-input picker-value" :class="{ empty: !formData[f.field_code] }">{{ formData[f.field_code] || `请选择${f.field_name}` }}</view>
          </picker>

          <!-- 时间 -->
          <picker v-else-if="f.field_type === 'time'" mode="time" :value="String(formData[f.field_code] || '')" @change="formData[f.field_code] = $event.detail.value">
            <view class="field-input picker-value" :class="{ empty: !formData[f.field_code] }">{{ formData[f.field_code] || `请选择${f.field_name}` }}</view>
          </picker>

          <!-- 日期时间 -->
          <view v-else-if="f.field_type === 'datetime'" class="dt-field">
            <view class="dt-segments">
              <picker mode="date" :value="datePart(f)" @change="onDateChange(f, $event)">
                <view class="dt-segment" :class="{ empty: !datePart(f) }">
                  <text class="dt-icon">📅</text>
                  <text>{{ datePart(f) || '选择日期' }}</text>
                </view>
              </picker>
              <picker mode="time" :value="timePart(f)" @change="onTimeChange(f, $event)">
                <view class="dt-segment" :class="{ empty: !timePart(f) }">
                  <text class="dt-icon">⏰</text>
                  <text>{{ timePart(f) || '选择时间' }}</text>
                </view>
              </picker>
            </view>
            <view class="dt-now-btn" @click="setNow(f)">现在</view>
          </view>

          <!-- 图片 -->
          <view v-else-if="f.field_type === 'image'" class="img-field">
            <image v-if="formData[f.field_code]" :src="imgSrc(formData[f.field_code])" class="img-preview" mode="aspectFit" />
            <view class="img-actions">
              <view v-if="f.field_code === 'remote_ecg_receive'" class="img-btn import" @click="importRemoteEcg">📥 导入远程心电图</view>
              <view class="img-btn" @click="uploadImage(f)">📷 拍照 / 选图</view>
              <view v-if="formData[f.field_code]" class="img-btn danger" @click="formData[f.field_code] = ''">删除</view>
            </view>
          </view>

          <!-- 选择 -->
          <view v-else-if="f.field_type === 'select'" class="select-group">
            <view
              v-for="opt in options(f)"
              :key="String(opt.value)"
              class="select-item"
              :class="{ active: formData[f.field_code] === opt.value }"
              @click="onSelect(f, String(opt.value))"
            >{{ opt.label }}</view>
            <view v-if="f.field_code === 'card_type'" class="scan-tip">💳 支持身份证/医保卡扫描快速回填（二期 OCR）</view>
            <view v-if="f.field_code === 'reperfusion'" class="reperfusion-tip">
              <text v-if="formData.reperfusion === '直接PCI'">→ 请填写「介入手术」Tab 的导管室激活、穿刺、开通时间</text>
              <text v-else-if="formData.reperfusion === '溶栓'">→ 请填写「院前急救/院内诊疗」中的溶栓治疗信息</text>
            </view>
          </view>

          <input
            v-else
            :model-value="String(formData[f.field_code] ?? '')"
            class="field-input"
            :placeholder="`请输入${f.field_name}`"
            placeholder-class="ph"
            @input="onText(f, $event)"
          />
        </view>
        <view v-if="!currentFields.length" class="empty">该分类暂无字段</view>
      </view>

      <!-- 操作 -->
      <view v-if="tabs.length" class="ops">
        <button class="op-btn op-save" :disabled="saving" @click="handleSave">{{ saving ? '保存中...' : '保存草稿' }}</button>
        <button class="op-btn op-submit" :disabled="submitting" @click="handleSubmit">{{ submitting ? '提交中...' : '提交审核' }}</button>
      </view>
    </template>

    <view v-else class="loading">病例不存在或已删除</view>
    </view>
  </view>
</template>

<style lang="scss" scoped>
.fill-page {
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
.nav-right { width: 120rpx; display: flex; align-items: center; justify-content: flex-end; gap: 16rpx; }
.nav-icon-btn { width: 48rpx; height: 48rpx; display: flex; align-items: center; justify-content: center; }
.nav-icon-btn:active { opacity: 0.6; }
.nav-icon-img { width: 48rpx; height: 48rpx; }

.page-body { padding-top: 24rpx; }

.loading { text-align: center; padding-top: 200rpx; color: #9ca3af; }
.no-tpl-tip { padding: 40rpx 32rpx; text-align: center; color: #f59e0b; font-size: 26rpx; }

.summary {
  margin: 0 32rpx 24rpx;
  padding: 32rpx;
  border-radius: 24rpx;
  background: linear-gradient(135deg, #2563eb, #1d4ed8);
}
.summary-top { display: flex; align-items: center; justify-content: space-between; }
.summary-name { font-size: 38rpx; font-weight: 700; color: #ffffff; }
.summary-no { font-size: 24rpx; color: rgba(255, 255, 255, 0.85); }
.summary-meta { margin-top: 12rpx; }
.summary-tpl { font-size: 24rpx; color: rgba(255, 255, 255, 0.85); }
.summary-actions { display: flex; gap: 32rpx; margin-top: 20rpx; }
.summary-link { font-size: 24rpx; color: #ffffff; }

.reject-tip {
  margin: 0 32rpx 24rpx;
  padding: 24rpx;
  border-radius: 16rpx;
  background: #fef2f2;
  border: 2rpx solid #fecaca;
}
.tip-title { font-size: 28rpx; font-weight: 600; color: #dc2626; }
.tip-item { margin-top: 12rpx; font-size: 26rpx; color: #b91c1c; }

.tab-bar {
  white-space: nowrap;
  background: #ffffff;
  padding: 16rpx 32rpx;
  border-bottom: 2rpx solid #f0f1f3;
}
.tab-item {
  display: inline-block;
  padding: 12rpx 28rpx;
  margin-right: 12rpx;
  border-radius: 32rpx;
  font-size: 26rpx;
  color: #6b7280;
  background: #f3f4f6;
}
.tab-item.active { background: #2563eb; color: #ffffff; }

.form-card {
  margin: 24rpx 32rpx;
  padding: 28rpx 32rpx;
  border-radius: 24rpx;
  background: #ffffff;
  border: 2rpx solid #f0f1f3;
}
.field { margin-bottom: 28rpx; }
.field-label { display: block; font-size: 26rpx; color: #4b5563; margin-bottom: 12rpx; }
.req { color: #ef4444; }
.field-type { margin-left: 12rpx; font-size: 20rpx; color: #c0c4cc; }
.field-input {
  height: 88rpx;
  padding: 0 24rpx;
  border-radius: 16rpx;
  background: #f3f4f6;
  font-size: 30rpx;
  line-height: 88rpx;
}
.ph { color: #9ca3af; }
.picker-value.empty { color: #9ca3af; }

.dt-field {
  display: flex;
  align-items: center;
  height: 88rpx;
  padding: 0 8rpx;
  border-radius: 16rpx;
  background: #f3f4f6;
  border: 2rpx solid transparent;
  transition: border-color 0.2s;
}
.dt-field:focus-within { border-color: #2563eb; background: #ffffff; }
.dt-segments { flex: 1; display: flex; align-items: center; height: 100%; }
.dt-segment {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 8rpx;
  height: 100%;
  padding: 0 16rpx;
  font-size: 28rpx;
  color: #1f2937;
  font-weight: 500;
}
.dt-segment.empty { color: #9ca3af; font-weight: 400; }
.dt-icon { font-size: 24rpx; }
.dt-now-btn {
  height: 72rpx;
  line-height: 72rpx;
  padding: 0 28rpx;
  border-radius: 12rpx;
  background: linear-gradient(135deg, #2563eb, #0ea5e9);
  color: #ffffff;
  font-size: 26rpx;
  font-weight: 600;
  white-space: nowrap;
}

.select-group { display: flex; flex-wrap: wrap; gap: 16rpx; }
.select-item {
  padding: 16rpx 36rpx;
  border-radius: 16rpx;
  background: #f3f4f6;
  font-size: 28rpx;
  color: #4b5563;
}
.select-item.active { background: #2563eb; color: #ffffff; }

.text-row { display: flex; gap: 16rpx; align-items: center; }
.text-row .field-input { flex: 1; }
.locate-btn {
  padding: 0 24rpx;
  height: 88rpx;
  line-height: 88rpx;
  border-radius: 16rpx;
  background: #eff6ff;
  color: #2563eb;
  font-size: 26rpx;
  white-space: nowrap;
}
.scan-tip {
  width: 100%;
  margin-top: 12rpx;
  font-size: 22rpx;
  color: #8b5cf6;
  background: #f5f3ff;
  padding: 10rpx 16rpx;
  border-radius: 12rpx;
}
.reperfusion-tip {
  width: 100%;
  margin-top: 12rpx;
  font-size: 22rpx;
  color: #b45309;
  background: #fffbeb;
  padding: 10rpx 16rpx;
  border-radius: 12rpx;
}

.pre-vital-box {
  margin-bottom: 28rpx;
  padding: 20rpx;
  border-radius: 16rpx;
  background: #eff6ff;
  border: 2rpx solid #dbeafe;
}
.pre-vital-title { font-size: 26rpx; font-weight: 600; color: #1d4ed8; }
.pre-vital-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16rpx;
  margin-top: 16rpx;
}
.pre-vital-item { padding: 12rpx; background: #ffffff; border-radius: 12rpx; }
.pre-vital-name { display: block; font-size: 22rpx; color: #6b7280; }
.pre-vital-value { display: block; font-size: 26rpx; color: #1f2937; font-weight: 500; margin-top: 4rpx; }
.pre-vital-tip { display: block; margin-top: 12rpx; font-size: 22rpx; color: #6b7280; }

.img-field { display: flex; flex-direction: column; gap: 16rpx; }
.img-preview { width: 100%; max-height: 360rpx; border-radius: 12rpx; background: #f3f4f6; }
.img-actions { display: flex; gap: 16rpx; }
.img-btn {
  flex: 1;
  padding: 20rpx;
  border-radius: 12rpx;
  background: #eff6ff;
  color: #2563eb;
  text-align: center;
  font-size: 26rpx;
}
.img-btn.danger { background: #fef2f2; color: #dc2626; flex: 0 0 160rpx; }
.img-btn.import { background: #ecfdf5; color: #059669; flex: 0 0 220rpx; }

.empty { padding: 20rpx 4rpx; font-size: 24rpx; color: #c0c4cc; text-align: center; }

.ops {
  display: flex;
  gap: 24rpx;
  margin: 8rpx 32rpx 0;
}
.op-btn {
  flex: 1;
  height: 100rpx;
  line-height: 100rpx;
  border-radius: 24rpx;
  font-size: 32rpx;
  font-weight: 600;
  border: none;
}
.op-save { background: #ffffff; color: #1d4ed8; border: 2rpx solid #1d4ed8; }
.op-submit { background: #1d4ed8; color: #ffffff; }
</style>
