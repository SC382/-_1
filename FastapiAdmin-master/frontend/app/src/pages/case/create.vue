<!-- 患者建档（基本信息）：蓝色自定义导航栏 + 白底表单 + 通栏深蓝保存按钮 -->
<script setup lang="ts">
import { ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import DoctorAPI, { type DoctorTemplate } from '@/api/module_cpx/doctor'
import { useUserStore } from '@/store/userStore'
import { http, getApiBaseUrl } from '@/http'
import { safeBack } from '@/utils/back'

const BASE_URL = getApiBaseUrl()
const userStore = useUserStore()

definePage({
  name: 'case-create',
  style: { navigationStyle: 'custom' },
})

const statusBarHeight = uni.getSystemInfoSync().statusBarHeight || 0

const submitting = ref(false)
const templates = ref<DoctorTemplate[]>([])
const form = ref({
  patient_name: '',
  come_type: '',
  first_contact_time: '',
  gender: '',
  id_type: '',
  birth_date: '',
  age: '',
  onset_address: '',
  detail_address: '',
  insurance_type: '',
  insurance_no: '',
  phone: '',
  diagnose_type: '',
  template_id: 0,
})

const genderOptions = ['男', '女']
const comeTypeOptions = [
  { label: '120急救', value: '120' },
  { label: '自行来院', value: '自行' },
  { label: '外院转诊', value: '转诊' },
]
const idTypeOptions = ['身份证', '医保卡', '其他']
const insuranceOptions = ['城镇职工医保', '城乡居民医保', '新农合', '自费', '其他']
const diagnoseTypes = ['STEMI', 'NSTEMI', 'UA', '主动脉夹层', '肺栓塞', '低危胸痛']

/** 当前时间字符串 yyyy-MM-dd HH:mm */
function nowStr() {
  const n = new Date()
  const p = (x: number) => String(x).padStart(2, '0')
  return `${n.getFullYear()}-${p(n.getMonth() + 1)}-${p(n.getDate())} ${p(n.getHours())}:${p(n.getMinutes())}`
}
/** 今天日期 yyyy-MM-dd */
function todayStr() { return nowStr().slice(0, 10) }

onLoad(async () => {
  // 首次医疗接触时间默认自动填充当前时间（可修改）
  form.value.first_contact_time = nowStr()
  try {
    templates.value = await DoctorAPI.templates()
  }
  catch {
    // http 层 toast
  }
})

function goBack() {
  safeBack()
}

// ── AI 智能录入（AI 自主判断字段 → 动态映射回填表单，识别结果可修改）──
// 字段名映射：AI 返回的标准编码 / 中文名 → 表单字段
const FIELD_MAP: Record<string, string> = {
  patient_name: 'patient_name', '姓名': 'patient_name', '患者姓名': 'patient_name',
  gender: 'gender', '性别': 'gender',
  age: 'age', '年龄': 'age',
  birth_date: 'birth_date', '出生日期': 'birth_date',
  id_number: 'id_number', '身份证号': 'id_number',
  id_type: 'id_type', '证件类型': 'id_type', 'card_type': 'id_type',
  phone: 'phone', '联系电话': 'phone', '电话': 'phone',
  come_type: 'come_type', '来院方式': 'come_type',
  onset_address: 'onset_address', '发病地址': 'onset_address',
  detail_address: 'detail_address', '详细地址': 'detail_address',
  insurance_type: 'insurance_type', '医保类型': 'insurance_type',
  insurance_no: 'insurance_no', '医保编号': 'insurance_no', '医保号': 'insurance_no',
  diagnose_type: 'diagnose_type', '诊断': 'diagnose_type', '诊断类型': 'diagnose_type',
}

/** 日期归一化：把「1968年3月12日」「1968/3/12」「1968.3.12」统一成 YYYY-MM-DD */
function normalizeDate(v: string): string {
  const s = String(v || '').trim()
  const m = s.match(/(\d{4})\s*[-年/.]\s*(\d{1,2})\s*[-月/.]\s*(\d{1,2})/)
  if (!m) return s
  const p = (x: string) => x.padStart(2, '0')
  return `${m[1]}-${p(m[2])}-${p(m[3])}`
}
/** 根据出生日期计算周岁（自动兼容 1968年3月12日 / 1968/3/12 等写法） */
function calcAge(birth: string): number | '' {
  const b = normalizeDate(birth)
  if (!b || !/^\d{4}-\d{2}-\d{2}$/.test(b)) return ''
  const [y, m, d] = b.split('-').map(Number)
  const t = new Date()
  let age = t.getFullYear() - y
  const md = t.getMonth() + 1 - m
  if (md < 0 || (md === 0 && t.getDate() < d)) age--
  if (age < 0 || age > 200) return ''
  return age
}
/** 出生日期 → 自动算年龄填入（年龄由出生日期派生，无需单独识别/手填） */
function syncAgeFromBirth() {
  const a = calcAge(form.value.birth_date)
  if (a !== '') form.value.age = String(a)
}
/** 证件类型归一化：模型可能返回「居民身份证」「社会保障卡」等别名 */
function normalizeIdType(v: string): string {
  const s = String(v).trim()
  if (!s) return s
  if (/身份证|居民身份证|二代身份证|居民身分证/.test(s)) return '身份证'
  if (/医保|医疗保险|医疗保险卡|社保卡|社会保障卡/.test(s)) return '医保卡'
  // AI 视觉模型常把身份证卡面号码栏的印刷标题「公民身份号码」误判为证件类型 → 归为身份证
  if (/公民身份号码|身份证号码|证件号码/.test(s)) return '身份证'
  return s
}

function fillFromRecognized(data: Record<string, string>) {
  let filled = 0
  for (const [k, v] of Object.entries(data)) {
    if (!v) continue
    let key = FIELD_MAP[k] || FIELD_MAP[String(k).trim()]
    if (!key && (k in form.value)) key = k
    if (key && form.value[key] !== undefined) {
      form.value[key] = key === 'id_type'
        ? normalizeIdType(v)
        : (key === 'birth_date' ? normalizeDate(v) : v)
      filled++
    }
  }
  // 识别到出生日期后自动算年龄
  syncAgeFromBirth()
  if (filled > 0) {
    uni.showToast({ title: `已自动填入 ${filled} 项，请核对`, icon: 'success' })
  }
  else {
    uni.showToast({ title: '未识别到可填入的表单字段', icon: 'none' })
  }
}

/** 上传图片到服务器，返回可访问 URL */
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

/** 识别前压缩（App 端）：手机原图 2-8MB → 长边 ≤1600、质量 70，上传与 AI 识别更快；压缩失败自动回退原图 */
function compressForAI(filePath: string, cb: (p: string) => void) {
  // #ifndef H5
  uni.compressImage({
    src: filePath,
    quality: 70,
    compressedWidth: 1600,
    success: (res) => cb(res.tempFilePath || filePath),
    fail: () => cb(filePath),
  })
  // #endif
  // #ifdef H5
  cb(filePath)
  // #endif
}

/** 图片识别：压缩 → 上传 → 后端视觉模型识别 → 回填 */
function recognizeFromImage(filePath: string) {
  uni.showLoading({ title: 'AI 识别中...' })
  compressForAI(filePath, (compressed) => {
    uploadToServer(compressed, async (url) => {
      try {
        const result = await http.Post('/cpx/doctor/ai/recognize', { image_url: url }) as Record<string, string>
        fillFromRecognized(result)
      }
      catch {
        uni.hideLoading()
        uni.showToast({ title: 'AI 识别失败，请重试', icon: 'none' })
      }
    })
  })
}

/** 已拿到图片 URL 后统一识别回填 */
async function recognizeImage(url: string) {
  uni.showLoading({ title: 'AI 识别中...' })
  try {
    const result = await http.Post('/cpx/doctor/ai/recognize', { image_url: url }) as Record<string, string>
    fillFromRecognized(result)
  }
  catch {
    uni.hideLoading()
    uni.showToast({ title: 'AI 识别失败，请重试', icon: 'none' })
  }
}

// #ifdef H5
// ── H5 专属：原生 input 选图（同步 click 保留用户激活，绕开 uni.chooseImage 在异步回调被浏览器拦截）──
let _h5Input: HTMLInputElement | null = null
function pickImageH5(onGot: (file: File) => void) {
  if (!_h5Input) {
    _h5Input = document.createElement('input')
    _h5Input.type = 'file'
    _h5Input.accept = 'image/*'
    _h5Input.style.display = 'none'
    document.body.appendChild(_h5Input)
  }
  _h5Input.onchange = () => {
    const f = _h5Input!.files?.[0]
    _h5Input!.value = ''
    if (f) onGot(f)
  }
  _h5Input.click()
}
function uploadFileH5(file: File, onSuccess: (url: string) => void) {
  uni.showLoading({ title: '上传中...' })
  const form = new FormData()
  form.append('file', file)
  const xhr = new XMLHttpRequest()
  xhr.open('POST', `${BASE_URL}/api/v1/cpx/doctor/upload/image`)
  xhr.setRequestHeader('Authorization', `Bearer ${userStore.getAccessToken() || ''}`)
  xhr.onload = () => {
    uni.hideLoading()
    try {
      const d = JSON.parse(xhr.responseText)
      if (d.code === 0 && d.data?.url) onSuccess(d.data.url)
      else uni.showToast({ title: d.msg || '上传失败', icon: 'none' })
    }
    catch { uni.showToast({ title: '上传失败', icon: 'none' }) }
  }
  xhr.onerror = () => { uni.hideLoading(); uni.showToast({ title: '上传失败', icon: 'none' }) }
  xhr.send(form)
}
// #endif

/** 文字解析：调用后端 ai/recognize {text} 提取患者信息回填 */
async function recognizeFromText(text: string) {
  uni.showLoading({ title: 'AI 解析中...' })
  try {
    const result = await http.Post('/cpx/doctor/ai/recognize', { text }) as Record<string, string>
    fillFromRecognized(result)
  }
  catch {
    uni.hideLoading()
    uni.showToast({ title: 'AI 解析失败，请重试', icon: 'none' })
  }
}

/** AI 智能录入主入口 */
function aiEntry() {
  // #ifdef H5
  // H5：文件选择必须在用户激活内触发，选图类统一走原生 input 同步 click
  uni.showActionSheet({
    itemList: ['证件扫描', '语音输入', '照片拍摄', '本地上传'],
    success: (res) => {
      if (res.tapIndex === 1) {
        voiceInput()
        return
      }
      pickImageH5((file) => uploadFileH5(file, (url) => recognizeImage(url)))
    },
  })
  return
  // #endif
  // #ifndef H5
  uni.showActionSheet({
    itemList: ['证件扫描', '语音输入', '照片拍摄', '本地上传'],
    success: (res) => {
      if (res.tapIndex === 0) idCardEntry()
      else if (res.tapIndex === 1) voiceInput()
      else if (res.tapIndex === 2) imageRecognize('camera')
      else imageRecognize('album')
    },
  })
  // #endif
}

/** 证件扫描：身份证/医保卡 → 照片拍摄/本地上传 → OCR 回填 */
function idCardEntry() {
  uni.showActionSheet({
    itemList: ['身份证', '医保卡'],
    success: (res) => chooseIdCardSource(res.tapIndex === 0 ? '身份证' : '医保卡'),
  })
}

function chooseIdCardSource(cardType: string) {
  // 先把用户选定的证件类型显示出来（"显示被是什么证件"），再由 OCR 填充其余信息
  form.value.id_type = cardType
  uni.showActionSheet({
    itemList: ['照片拍摄', '本地上传'],
    success: (res) => {
      const sourceType = res.tapIndex === 0 ? 'camera' : 'album'
      uni.chooseImage({
        count: 1,
        sourceType: [sourceType],
        success: (chooseRes) => {
          uni.showLoading({ title: `${cardType}识别中...` })
          recognizeFromImage(chooseRes.tempFilePaths[0])
        },
        fail: (err: any) => {
          const msg = (err && err.errMsg) || ''
          if (msg.includes('cancel')) { uni.showToast({ title: '已取消', icon: 'none' }); return }
          uni.showToast({ title: `拍照/选图失败：${msg}`, icon: 'none', duration: 2500 })
        },
      })
    },
  })
}

// ── 语音输入：App 端真实录音 → 后端 ASR 转写 → AI 解析回填；H5 无原生录音 → 文本降级 ──
let recorderManager: any = null
let recordingVoice = false
/** 录音悬浮条状态（App 端）：录音中常驻"正在录音…点击结束"，不再需要再走一遍菜单结束 */
const voiceActive = ref(false)
const voiceSeconds = ref(0)
let voiceTimer: any = null
let voiceStopFallback: any = null

function clearVoiceTimer() {
  if (voiceTimer) {
    clearInterval(voiceTimer)
    voiceTimer = null
  }
}

function voiceInput() {
  // #ifdef H5
  uni.showModal({
    title: 'AI 语音录入',
    editable: true,
    placeholderText: '语音录入请使用 App 端；此处可直接输入，如：「患者李四，男，58岁，电话13812345678」',
    success: (res) => {
      if (!res.confirm || !res.content) return
      recognizeFromText(res.content)
    },
  })
  // #endif
  // #ifndef H5
  // 点击即开始录音；录音中点菜单项不重复开始，引导点击底部悬浮条结束
  if (!recordingVoice) startVoiceRecord()
  else uni.showToast({ title: '正在录音，点击屏幕下方录音条结束', icon: 'none' })
  // #endif
}

function ensureVoiceRecorder() {
  if (recorderManager) return recorderManager
  const rm: any = uni.getRecorderManager()
  if (!rm) return null
  rm.onStop((res: any) => {
    if (voiceStopFallback) { clearTimeout(voiceStopFallback); voiceStopFallback = null }
    recordingVoice = false
    voiceActive.value = false
    clearVoiceTimer()
    uni.hideLoading()
    const fs = uni.getFileSystemManager()
    fs.readFile({
      filePath: res.tempFilePath,
      encoding: 'base64',
      success: async (r: any) => {
        uni.showLoading({ title: '语音转写中...' })
        try {
          const data = await DoctorAPI.asr({ audio_base64: r.data as string, format: 'mp3' })
          uni.hideLoading()
          const text = (data.text || '').trim()
          if (!text) {
            uni.showToast({ title: '未识别到内容，请重试', icon: 'none' })
            return
          }
          // 转写文本可编辑确认 → AI 解析回填
          uni.showModal({
            title: '识别内容确认',
            editable: true,
            content: text,
            success: (m) => {
              if (m.confirm && m.content) recognizeFromText(m.content)
            },
          })
        }
        catch (e: any) {
          uni.hideLoading()
          uni.showToast({ title: e?.msg || '语音转写失败，请重试', icon: 'none' })
        }
      },
      fail: () => {
        uni.hideLoading()
        uni.showToast({ title: '读取录音失败', icon: 'none' })
      },
    })
  })
  rm.onError(() => {
    if (voiceStopFallback) { clearTimeout(voiceStopFallback); voiceStopFallback = null }
    recordingVoice = false
    voiceActive.value = false
    clearVoiceTimer()
    uni.hideLoading()
    uni.showToast({ title: '录音失败，请重试', icon: 'none' })
  })
  recorderManager = rm
  return rm
}

function startVoiceRecord() {
  const rm = ensureVoiceRecorder()
  if (!rm) {
    uni.showToast({ title: '当前环境不支持录音', icon: 'none' })
    return
  }
  recordingVoice = true
  voiceActive.value = true
  voiceSeconds.value = 0
  clearVoiceTimer()
  voiceTimer = setInterval(() => {
    voiceSeconds.value += 1
    // 60 秒上限自动结束，避免无限录音
    if (voiceSeconds.value >= 60) {
      uni.showToast({ title: '已达 60 秒上限，自动结束', icon: 'none' })
      stopVoiceRecord()
    }
  }, 1000)
  rm.start({ format: 'mp3', sampleRate: 16000 })
  uni.showToast({ title: '开始录音，点击屏幕下方录音条结束', icon: 'none', duration: 2000 })
}

function stopVoiceRecord() {
  clearVoiceTimer()
  if (voiceStopFallback) { clearTimeout(voiceStopFallback); voiceStopFallback = null }
  if (recorderManager) recorderManager.stop()
  // 兜底：若 2 秒内未收到 onStop/onError（如录音未真正开始），强制复位，防止录音条卡死无法退出
  voiceStopFallback = setTimeout(() => {
    voiceStopFallback = null
    if (voiceActive.value || recordingVoice) {
      recordingVoice = false
      voiceActive.value = false
      uni.hideLoading()
      uni.showToast({ title: '录音已结束', icon: 'none' })
    }
  }, 2000)
}

/** 图片识别：照片拍摄/本地上传 → OCR 回填（真实调用） */
function imageRecognize(sourceType: 'camera' | 'album') {
  uni.chooseImage({
    count: 1,
    sourceType: [sourceType],
    success: (chooseRes) => recognizeFromImage(chooseRes.tempFilePaths[0]),
    fail: (err: any) => {
      const msg = (err && err.errMsg) || ''
      if (msg.includes('cancel')) { uni.showToast({ title: '已取消', icon: 'none' }); return }
      uni.showToast({ title: `拍照/选图失败：${msg}`, icon: 'none', duration: 2500 })
    },
  })
}

// ── 定位（发病地址）：H5 浏览器原生定位，失败自动降级 IP 定位；App/小程序用地图选择 ──
function ipLocate() {
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
          form.value.onset_address = addr
          uni.showToast({ title: `已定位（IP定位：${addr}）`, icon: 'none' })
        }
        else uni.showToast({ title: '定位失败，请手动输入', icon: 'none' })
      }
      catch { uni.showToast({ title: '定位失败，请手动输入', icon: 'none' }) }
    },
    fail: () => { uni.hideLoading(); uni.showToast({ title: '定位失败，请手动输入', icon: 'none' }) },
  })
}

function locateAddress() {
  // #ifdef H5
  if (typeof navigator !== 'undefined' && navigator.geolocation) {
    uni.showLoading({ title: '定位中...' })
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        uni.hideLoading()
        const lat = pos.coords.latitude
        const lng = pos.coords.longitude
        form.value.onset_address = `${lat.toFixed(6)},${lng.toFixed(6)}`
        uni.showToast({ title: '已获取当前位置坐标', icon: 'none' })
      },
      () => { uni.hideLoading(); ipLocate() },
      { enableHighAccuracy: false, timeout: 6000 },
    )
    return
  }
  // #endif
  uni.chooseLocation({
    success: (res) => {
      form.value.onset_address = res.address || res.name || ''
      if (!form.value.onset_address && res.latitude)
        form.value.onset_address = `${res.latitude.toFixed(4)},${res.longitude.toFixed(4)}`
    },
    fail: () => { uni.showToast({ title: '定位失败，请手动输入', icon: 'none' }) },
  })
}

// ── 扫码（医保编号）：App/小程序调起扫码；H5 浏览器不支持 → 提示手动输入 ──
function scanCode(field: 'insurance_no') {
  // #ifdef H5
  uni.showToast({ title: '当前浏览器环境不支持扫码，请手动输入', icon: 'none' })
  // #endif
  // #ifndef H5
  uni.scanCode({
    success: (res) => {
      form.value[field] = res.result || ''
      uni.showToast({ title: '扫码成功', icon: 'success' })
    },
    fail: () => { uni.showToast({ title: '未识别到条码', icon: 'none' }) },
  })
  // #endif
}

// ── 日期时间拆分（首次医疗接触时间）──
function fctDate() { return form.value.first_contact_time.slice(0, 10) }
function fctTime() { return form.value.first_contact_time.slice(11, 16) }
function onFctDate(e: any) { form.value.first_contact_time = `${e.detail.value} ${fctTime() || '00:00'}` }
function onFctTime(e: any) { form.value.first_contact_time = `${fctDate() || todayStr()} ${e.detail.value}` }
function onBirthDateChange(e: any) {
  form.value.birth_date = e.detail.value
  syncAgeFromBirth()
}

// ── 提交 ──
async function handleCreate() {
  if (!form.value.patient_name.trim()) { uni.showToast({ title: '请填写姓名', icon: 'none' }); return }
  if (!form.value.come_type) { uni.showToast({ title: '请选择来院方式', icon: 'none' }); return }
  if (!form.value.first_contact_time) { uni.showToast({ title: '请选择首次医疗接触时间', icon: 'none' }); return }
  if (form.value.age && (Number(form.value.age) < 0 || Number(form.value.age) > 200)) {
    uni.showToast({ title: '年龄须在 0-200 之间', icon: 'none' }); return
  }
  if (!form.value.template_id) { uni.showToast({ title: '请选择填报模板', icon: 'none' }); return }

  submitting.value = true
  try {
    const res = await DoctorAPI.createCase({
      patient_name: form.value.patient_name.trim(),
      gender: form.value.gender || undefined,
      age: form.value.age ? Number(form.value.age) : undefined,
      phone: form.value.phone || undefined,
      template_id: form.value.template_id,
      come_type: form.value.come_type || undefined,
      diagnose_type: form.value.diagnose_type || undefined,
      first_contact_time: form.value.first_contact_time || undefined,
      id_type: form.value.id_type || undefined,
      birth_date: form.value.birth_date || undefined,
      onset_address: form.value.onset_address || undefined,
      detail_address: form.value.detail_address || undefined,
      insurance_type: form.value.insurance_type || undefined,
      insurance_no: form.value.insurance_no || undefined,
    })
    uni.showToast({ title: '建档成功', icon: 'success' })
    setTimeout(() => {
      uni.redirectTo({ url: `/pages/case/fill?id=${res.id}` })
    }, 600)
  }
  catch {
    // http 层 toast
  }
  finally {
    submitting.value = false
  }
}
</script>

<template>
  <view class="create-page">
    <!-- 自定义蓝色导航栏：返回 + 标题「基本信息」 + 右上角两个小图标（证件识别 / AI录入） -->
    <view class="nav-bar" :style="{ paddingTop: `${statusBarHeight}px` }">
      <view class="nav-back" @click="goBack">‹</view>
      <text class="nav-title">基本信息</text>
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
      <!-- 基本信息表单（白底，标签在上输入在下，必填红*） -->
      <view class="form-card">
        <view class="field">
          <text class="field-label">姓名<text class="req"> *</text></text>
          <input v-model="form.patient_name" class="field-input" placeholder="请填写姓名" placeholder-class="ph" />
        </view>

        <view class="field">
          <text class="field-label">来院方式<text class="req"> *</text></text>
          <picker :range="comeTypeOptions" range-key="label" @change="form.come_type = comeTypeOptions[Number($event.detail.value)].value">
            <view class="field-input picker-value" :class="{ empty: !form.come_type }">
              {{ comeTypeOptions.find((o) => o.value === form.come_type)?.label || '请选择来院方式' }}
            </view>
          </picker>
        </view>

        <view class="field">
          <text class="field-label">首次医疗接触时间<text class="req"> *</text></text>
          <view class="dt-field">
            <view class="dt-segments">
              <picker mode="date" :value="fctDate()" @change="onFctDate">
                <view class="dt-segment" :class="{ empty: !fctDate() }">
                  <text class="dt-icon">📅</text>
                  <text>{{ fctDate() || '选择日期' }}</text>
                </view>
              </picker>
              <picker mode="time" :value="fctTime()" @change="onFctTime">
                <view class="dt-segment" :class="{ empty: !fctTime() }">
                  <text class="dt-icon">⏰</text>
                  <text>{{ fctTime() || '选择时间' }}</text>
                </view>
              </picker>
            </view>
          </view>
        </view>

        <view class="field">
          <text class="field-label">性别</text>
          <view class="chip-row">
            <view
              v-for="g in genderOptions"
              :key="g"
              class="chip"
              :class="{ active: form.gender === g }"
              @click="form.gender = g"
            >{{ g }}</view>
          </view>
        </view>

        <view class="field">
          <text class="field-label">证件类型</text>
          <picker :range="idTypeOptions" @change="form.id_type = idTypeOptions[Number($event.detail.value)]">
            <view class="field-input picker-value" :class="{ empty: !form.id_type }">{{ form.id_type || '请选择证件类型' }}</view>
          </picker>
        </view>

        <view class="field">
          <text class="field-label">出生日期</text>
          <picker mode="date" :value="form.birth_date" @change="onBirthDateChange">
            <view class="field-input picker-value" :class="{ empty: !form.birth_date }">{{ form.birth_date || '请填写出生日期' }}</view>
          </picker>
        </view>

        <view class="field">
          <text class="field-label">年龄</text>
          <view class="input-unit">
            <input v-model="form.age" class="field-input" type="number" placeholder="请填写年龄" placeholder-class="ph" />
            <text class="unit">岁</text>
          </view>
        </view>

        <view class="field">
          <text class="field-label">发病地址</text>
          <view class="input-action">
            <input v-model="form.onset_address" class="field-input" placeholder="请填写发病地址" placeholder-class="ph" />
            <text class="action-btn" @click="locateAddress">📍</text>
          </view>
        </view>

        <view class="field">
          <text class="field-label">详细地址</text>
          <input v-model="form.detail_address" class="field-input" placeholder="请填写详细地址" placeholder-class="ph" />
        </view>

        <view class="field">
          <text class="field-label">医保类型</text>
          <picker :range="insuranceOptions" @change="form.insurance_type = insuranceOptions[Number($event.detail.value)]">
            <view class="field-input picker-value" :class="{ empty: !form.insurance_type }">{{ form.insurance_type || '请选择医保类型' }}</view>
          </picker>
        </view>

        <view class="field">
          <text class="field-label">医保编号</text>
          <view class="input-action">
            <input v-model="form.insurance_no" class="field-input" placeholder="请填写医保编号" placeholder-class="ph" />
            <text class="action-btn" @click="scanCode('insurance_no')">📷</text>
          </view>
        </view>

        <view class="field">
          <text class="field-label">联系电话</text>
          <input v-model="form.phone" class="field-input" type="number" placeholder="请填写联系电话" placeholder-class="ph" />
        </view>

        <view class="field">
          <text class="field-label">诊断类型</text>
          <view class="chip-row wrap">
            <view
              v-for="d in diagnoseTypes"
              :key="d"
              class="chip"
              :class="{ active: form.diagnose_type === d }"
              @click="form.diagnose_type = d"
            >{{ d }}</view>
          </view>
        </view>
      </view>

      <!-- 填报模板 -->
      <view class="form-card">
        <text class="card-title">填报模板<text class="req"> *</text></text>
        <view
          v-for="t in templates"
          :key="t.id"
          class="template-item"
          :class="{ active: form.template_id === t.id }"
          @click="form.template_id = t.id"
        >
          <view class="template-info">
            <text class="template-name">{{ t.template_name }}</text>
            <text class="template-meta">版本 {{ t.version || '-' }} · {{ t.fields.length }} 个字段</text>
          </view>
          <view class="template-check" :class="{ checked: form.template_id === t.id }">
            {{ form.template_id === t.id ? '✓' : '' }}
          </view>
        </view>
        <view v-if="!templates.length" class="template-empty">暂无可用的已发布模板，请联系管理员配置</view>
      </view>

      <!-- 底部通栏深蓝圆角大按钮 -->
      <button class="save-btn" :disabled="submitting" @click="handleCreate">
        {{ submitting ? '保存中...' : '保存' }}
      </button>
    </view>

    <!-- 录音悬浮条（App 端录音中常驻）：点击即结束并转写 -->
    <!-- #ifndef H5 -->
    <view v-if="voiceActive" class="voice-bar" @click="stopVoiceRecord">
      <view class="voice-dot" />
      <text class="voice-text">正在录音 {{ voiceSeconds }}s，点击结束</text>
    </view>
    <!-- #endif -->
  </view>
</template>

<style lang="scss" scoped>
.create-page {
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
  display: flex;
  align-items: center;
  gap: 12rpx;
}
.nav-icon-btn {
  width: 64rpx;
  height: 64rpx;
  display: flex;
  align-items: center;
  justify-content: center;
}
.nav-icon-btn:active {
  opacity: 0.6;
}
.nav-icon { font-size: 34rpx; line-height: 1; }
.nav-icon-img { width: 48rpx; height: 48rpx; }

.page-body {
  padding: 24rpx 32rpx 0;
}

/* 表单卡片 */
.form-card {
  margin-bottom: 24rpx;
  padding: 28rpx 32rpx;
  border-radius: 24rpx;
  background: #ffffff;
  border: 2rpx solid #f0f1f3;
}
.card-title {
  display: block;
  font-size: 30rpx;
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 20rpx;
}
.req { color: #ef4444; }

.field { margin-bottom: 24rpx; }
.field:last-child { margin-bottom: 0; }
.field-label {
  display: block;
  font-size: 26rpx;
  color: #4b5563;
  margin-bottom: 12rpx;
}
.field-input {
  height: 88rpx;
  padding: 0 24rpx;
  border-radius: 16rpx;
  background: #f5f6f8;
  font-size: 30rpx;
  line-height: 88rpx;
}
.ph { color: #9ca3af; }
.picker-value.empty { color: #9ca3af; }

/* 性别/诊断类型 chips */
.chip-row { display: flex; gap: 20rpx; }
.chip-row.wrap { flex-wrap: wrap; }
.chip {
  padding: 16rpx 48rpx;
  border-radius: 16rpx;
  background: #f5f6f8;
  font-size: 28rpx;
  color: #4b5563;
}
.chip.active { background: #2563eb; color: #ffffff; }

/* 年龄：输入 + 单位 */
.input-unit { position: relative; }
.input-unit .field-input { padding-right: 96rpx; }
.unit {
  position: absolute;
  right: 24rpx;
  top: 0;
  height: 88rpx;
  line-height: 88rpx;
  font-size: 26rpx;
  color: #9ca3af;
}

/* 输入 + 操作按钮（定位/扫码） */
.input-action { display: flex; gap: 16rpx; align-items: center; }
.input-action .field-input { flex: 1; }
.action-btn {
  width: 88rpx;
  height: 88rpx;
  line-height: 88rpx;
  text-align: center;
  border-radius: 16rpx;
  background: #eff6ff;
  color: #2563eb;
  font-size: 34rpx;
  flex-shrink: 0;
}

/* 首次医疗接触时间：日期 + 时间 */
.dt-field {
  display: flex;
  align-items: center;
  height: 88rpx;
  border-radius: 16rpx;
  background: #f5f6f8;
}
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

/* 模板选择 */
.template-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 24rpx;
  border-radius: 16rpx;
  border: 2rpx solid #e5e7eb;
  margin-bottom: 16rpx;
}
.template-item.active { border-color: #2563eb; background: #eff6ff; }
.template-name { font-size: 30rpx; color: #1f2937; font-weight: 500; }
.template-meta { display: block; margin-top: 6rpx; font-size: 22rpx; color: #9ca3af; }
.template-check {
  width: 44rpx;
  height: 44rpx;
  border-radius: 50%;
  border: 2rpx solid #d1d5db;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 26rpx;
  color: #ffffff;
}
.template-check.checked { background: #2563eb; border-color: #2563eb; }
.template-empty { padding: 40rpx 0; text-align: center; font-size: 26rpx; color: #9ca3af; }

/* 底部通栏深蓝圆角大按钮 */
.save-btn {
  margin-top: 8rpx;
  height: 100rpx;
  line-height: 100rpx;
  border-radius: 24rpx;
  background: #1d4ed8;
  color: #ffffff;
  font-size: 34rpx;
  font-weight: 600;
  letter-spacing: 4rpx;
}
.save-btn::after { border: none; }
.save-btn[disabled] { opacity: 0.6; }

/* 录音悬浮条：底部居中，录音中点击结束 */
.voice-bar {
  position: fixed;
  left: 50%;
  bottom: 60rpx;
  transform: translateX(-50%);
  z-index: 999;
  display: flex;
  align-items: center;
  gap: 14rpx;
  padding: 22rpx 44rpx;
  border-radius: 60rpx;
  background: rgba(29, 78, 216, 0.95);
  box-shadow: 0 8rpx 24rpx rgba(29, 78, 216, 0.35);
}
.voice-dot {
  width: 18rpx;
  height: 18rpx;
  border-radius: 50%;
  background: #f87171;
  animation: voiceBlink 1s ease-in-out infinite;
}
@keyframes voiceBlink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.25; }
}
.voice-text {
  color: #ffffff;
  font-size: 28rpx;
}
</style>
