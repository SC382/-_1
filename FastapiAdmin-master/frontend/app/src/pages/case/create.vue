<!-- 患者建档（基本信息）：蓝色自定义导航栏 + 白底表单 + 通栏深蓝保存按钮 -->
<script setup lang="ts">
import { ref } from 'vue'
import { onLoad, onUnload } from '@dcloudio/uni-app'
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

// 离开页面：丢弃未完成回调、停录音、收起面板
onUnload(() => {
  voiceDisposed = true
  voiceStopRequested = true
  voiceFinished = true
  voiceAwaitingStop = false
  clearVoiceTimer()
  clearVoiceFallback()
  recordingVoice = false
  voiceActive.value = false
  voicePanel.value = false
  voicePanelRecording.value = false
  if (recorderManager) {
    try { recorderManager.stop() }
    catch { /* 忽略：可能未在录音 */ }
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
  id_number: 'id_number', '身份证号': 'id_number', '社会保障号码': 'id_number', '公民身份号码': 'id_number',
  id_type: 'id_type', '证件类型': 'id_type', 'card_type': 'id_type',
  phone: 'phone', '联系电话': 'phone', '电话': 'phone',
  come_type: 'come_type', '来院方式': 'come_type',
  onset_address: 'onset_address', '发病地址': 'onset_address',
  detail_address: 'detail_address', '详细地址': 'detail_address',
  insurance_type: 'insurance_type', '医保类型': 'insurance_type',
  insurance_no: 'insurance_no', '医保编号': 'insurance_no', '医保号': 'insurance_no', '医保卡号': 'insurance_no', '社保卡号': 'insurance_no', '卡号': 'insurance_no',
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

/** 识别前压缩（App 端）：手机原图 2-8MB → 长边 ≤1280、质量 60（满足腾讯 OCR 分辨率要求，体积更小更快）；失败自动回退原图 */
function compressForAI(filePath: string, cb: (p: string) => void) {
  // #ifndef H5
  uni.compressImage({
    src: filePath,
    quality: 60,
    compressedWidth: 1280,
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

/** 证件 OCR 主流程（图片 URL 已就绪）：提示识别中 → 调腾讯 OCR → 回填；医保卡附识别文字供核对 */
async function runOcrFromUrl(url: string, cardType: string) {
  try {
    uni.showLoading({ title: `${cardType}识别中...` })
    const result = await http.Post('/cpx/doctor/ai/ocr', { image_url: url, card_type: cardType }) as Record<string, string>
    uni.hideLoading()
    fillFromRecognized(result)
    if (result.ocr_text) {
      uni.showModal({
        title: '识别文字（请核对补充）',
        content: result.ocr_text,
        showCancel: false,
        confirmText: '知道了',
      })
    }
  }
  catch {
    uni.hideLoading()
    uni.showToast({ title: '证件识别失败，请重试', icon: 'none' })
  }
}

// #ifdef H5
// ── H5 专属：原生 input 选图（同步 click 保留用户激活，绕开 uni.chooseImage 在异步回调被浏览器拦截）──
let _h5Input: HTMLInputElement | null = null
/** H5 选图：mode='camera' 时 input 加 capture 直接唤起手机相机（iOS/Android 浏览器均支持）；默认相册 */
function pickImageH5(onGot: (file: File) => void, mode: 'album' | 'camera' = 'album') {
  if (!_h5Input) {
    _h5Input = document.createElement('input')
    _h5Input.type = 'file'
    _h5Input.accept = 'image/*'
    _h5Input.style.display = 'none'
    document.body.appendChild(_h5Input)
  }
  if (mode === 'camera') _h5Input.setAttribute('capture', 'environment')
  else _h5Input.removeAttribute('capture')
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
/** H5 浏览器端压缩（App 用 uni.compressImage）：原图 2-8MB → 长边 ≤1280、JPEG 质量 0.6，上传提速；失败回退原图 */
function compressFileH5(file: File, maxSide = 1280, quality = 0.6): Promise<File> {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file)
    const img = new Image()
    img.onload = () => {
      URL.revokeObjectURL(url)
      try {
        const scale = Math.min(1, maxSide / Math.max(img.width, img.height))
        const w = Math.max(1, Math.round(img.width * scale))
        const h = Math.max(1, Math.round(img.height * scale))
        const canvas = document.createElement('canvas')
        canvas.width = w
        canvas.height = h
        const ctx = canvas.getContext('2d')
        if (!ctx) { reject(new Error('canvas 不可用')); return }
        ctx.drawImage(img, 0, 0, w, h)
        canvas.toBlob((blob) => {
          if (blob) {
            const name = (file.name || 'photo').replace(/\.[^.]+$/, '')
            resolve(new File([blob], `${name}.jpg`, { type: 'image/jpeg' }))
          }
          else reject(new Error('压缩失败'))
        }, 'image/jpeg', quality)
      }
      catch (e) { reject(e as Error) }
    }
    img.onerror = () => { URL.revokeObjectURL(url); reject(new Error('图片读取失败')) }
    img.src = url
  })
}
/** H5 统一上传：先 canvas 压缩再传（HEIC 等压缩失败自动回退原图，不阻塞） */
async function uploadH5Compressed(file: File, onSuccess: (url: string) => void) {
  let f = file
  try { f = await compressFileH5(file) }
  catch { /* 回退原图 */ }
  uploadFileH5(f, onSuccess)
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
      if (res.tapIndex === 0) {
        idCardEntry()
        return
      }
      if (res.tapIndex === 1) {
        voiceInput()
        return
      }
      const mode = res.tapIndex === 2 ? 'camera' : 'album'
      pickImageH5((file) => uploadH5Compressed(file, (url) => recognizeImage(url)), mode)
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
  // 先把用户选定的证件类型显示出来，再由 OCR / 手动方式填充其余信息
  form.value.id_type = cardType
  // #ifdef H5
  // H5：拍照（input capture 唤起相机）或相册 → canvas 压缩 → 上传 → OCR
  uni.showActionSheet({
    itemList: ['照片拍摄', '从相册选择'],
    success: (res) => {
      const mode = res.tapIndex === 0 ? 'camera' : 'album'
      pickImageH5((file) => uploadH5Compressed(file, (url) => runOcrFromUrl(url, cardType)), mode)
    },
  })
  return
  // #endif
  // #ifndef H5
  uni.showActionSheet({
    itemList: ['照片拍摄', '本地上传'],
    success: (res) => {
      const sourceType = res.tapIndex === 0 ? 'camera' : 'album'
      uni.chooseImage({
        count: 1,
        sourceType: [sourceType],
        success: (chooseRes) => {
          compressForAI(chooseRes.tempFilePaths[0], (compressed) => {
            uploadToServer(compressed, (url) => runOcrFromUrl(url, cardType))
          })
        },
        fail: (err: any) => {
          const msg = (err && err.errMsg) || ''
          if (msg.includes('cancel')) { uni.showToast({ title: '已取消', icon: 'none' }); return }
          uni.showToast({ title: `拍照/选图失败：${msg}`, icon: 'none', duration: 2500 })
        },
      })
    },
  })
  // #endif
}

// ── 语音输入：App 端真实录音 → 分段 ASR 转写 → 拼接 → AI 解析回填；H5 无原生录音 → 文本降级 ──
// 智谱 ASR 单次音频硬限制 30 秒（错误码 1214），故每段录满 28 秒自动切段续录：
// 用户一直说到说完，各段文字按段号顺序拼接成完整文本，再交给 AI 解析。
let recorderManager: any = null
let recordingVoice = false
/** 录音悬浮条状态（App 端）：整轮录音期间常驻，点击结束整轮 */
const voiceActive = ref(false)
/** 当前段已录秒数 */
const voiceSeconds = ref(0)
/** 当前段号（从 1 起，仅用于展示） */
const voiceSegNo = ref(1)
/** 已转写累计字数（仅用于展示） */
const voiceChars = ref(0)
/** 底部语音面板是否展开（录音中 + 转写结果两态都用它） */
const voicePanel = ref(false)
/** 面板是否处于「录音中」（false = 已结束，展示文字框） */
const voicePanelRecording = ref(false)
/** 转写结果文字框内容（可编辑） */
const voicePanelText = ref('')
/** 是否未识别到任何文字（用于文字框内灰字提示） */
const voiceNoResult = ref(false)
let voiceTimer: any = null
let voiceStopFallback: any = null
/** 各段转写文本，下标 = 段下标（0 起），保证按口述顺序拼接 */
let voiceSegments: string[] = []
/** 识别失败的段号（从 1 起），用于最终提示 */
let voiceSegFailed: number[] = []
/** 当前段下标（0 起） */
let voiceSegIndex = 0
/** 在途转写请求数 */
let voicePending = 0
/** 用户已点击结束，不再续录 */
let voiceStopRequested = false
/** 本轮是否已结算，防止重复弹窗 */
let voiceFinished = false
/** 已调用 stop()、等待 onStop 回调（同时用于拦截重复回调） */
let voiceAwaitingStop = false
/** 页面已卸载，丢弃后续回调 */
let voiceDisposed = false

function clearVoiceTimer() {
  if (voiceTimer) {
    clearInterval(voiceTimer)
    voiceTimer = null
  }
}

function clearVoiceFallback() {
  if (voiceStopFallback) {
    clearTimeout(voiceStopFallback)
    voiceStopFallback = null
  }
}

/** stop() 后 3 秒仍未收到 onStop/onError（如录音未真正启动）的兜底，防止卡死 */
function armVoiceStopFallback() {
  clearVoiceFallback()
  voiceStopFallback = setTimeout(() => {
    voiceStopFallback = null
    if (!voiceAwaitingStop) return
    voiceAwaitingStop = false
    clearVoiceTimer()
    if (voiceStopRequested) {
      recordingVoice = false
      voiceActive.value = false
      checkVoiceFinish()
    }
    else {
      startNextSegment()
    }
  }, 3000)
}

function updateVoiceChars() {
  voiceChars.value = voiceSegments.filter(Boolean).join('').length
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
    // 只处理本端主动发起的 stop()，拦截重复回调，避免段号乱跳
    if (!voiceAwaitingStop) return
    voiceAwaitingStop = false
    clearVoiceFallback()
    clearVoiceTimer()
    const segIdx = voiceSegIndex
    const segNo = segIdx + 1
    const fs = uni.getFileSystemManager()
    fs.readFile({
      filePath: res.tempFilePath,
      encoding: 'base64',
      success: (r: any) => {
        if (voiceDisposed) return
        // 先把下一段录起来，再后台上传本段 —— 段间停顿最短
        if (!voiceStopRequested) startNextSegment()
        voicePending += 1
        uploadVoiceSegment(segIdx, segNo, r.data as string)
      },
      fail: () => {
        if (voiceDisposed) return
        if (!voiceStopRequested) {
          startNextSegment()
        }
        else {
          voiceSegFailed.push(segNo)
          uni.showToast({ title: `第 ${segNo} 段读取失败，已跳过`, icon: 'none' })
          checkVoiceFinish()
        }
      },
    })
  })
  rm.onError(() => {
    voiceAwaitingStop = false
    clearVoiceFallback()
    clearVoiceTimer()
    uni.hideLoading()
    recordingVoice = false
    voiceActive.value = false
    if (!voiceStopRequested) {
      voiceStopRequested = true
      uni.showToast({ title: '录音中断，已结束', icon: 'none' })
    }
    checkVoiceFinish()
  })
  recorderManager = rm
  return rm
}

/** 开始录当前段：录满 28 秒自动切段（智谱单次音频上限 30 秒，留 2 秒余量） */
function beginVoiceSegment() {
  voiceSeconds.value = 0
  clearVoiceTimer()
  voiceTimer = setInterval(() => {
    voiceSeconds.value += 1
    if (voiceSeconds.value >= 28) {
      clearVoiceTimer()
      voiceAwaitingStop = true
      if (recorderManager) recorderManager.stop()
      armVoiceStopFallback()
    }
  }, 1000)
  if (recorderManager) recorderManager.start({ format: 'mp3', sampleRate: 16000 })
}

/** 续录下一段（段号 +1） */
function startNextSegment() {
  if (voiceDisposed || voiceStopRequested) return
  voiceSegIndex += 1
  voiceSegNo.value = voiceSegIndex + 1
  beginVoiceSegment()
}

/** 后台上传单段音频做 ASR，结果按段号入缓存（不覆盖其他段） */
async function uploadVoiceSegment(segIdx: number, segNo: number, base64: string) {
  try {
    const data = await DoctorAPI.asr({ audio_base64: base64, format: 'mp3' })
    const t = (data.text || '').trim()
    if (t) voiceSegments[segIdx] = t
    else voiceSegFailed.push(segNo)
  }
  catch {
    voiceSegFailed.push(segNo)
  }
  finally {
    voicePending -= 1
    updateVoiceChars()
    checkVoiceFinish()
  }
}

/** 用户已结束且所有段都返回 → 结算 */
function checkVoiceFinish() {
  if (voiceDisposed || voiceFinished) return
  if (!voiceStopRequested || voicePending > 0) return
  voiceFinished = true
  clearVoiceTimer()
  clearVoiceFallback()
  recordingVoice = false
  voiceActive.value = false
  uni.hideLoading()
  finishVoiceRecord()
}

/** 结算：按段号顺序拼接全部文本 → 落入底部面板文字框（用户可编辑后确认解析） */
function finishVoiceRecord() {
  const joined = voiceSegments.filter(Boolean).join('').trim()
  voicePanelRecording.value = false
  voicePanel.value = true
  voicePanelText.value = joined
  voiceNoResult.value = !joined
  if (joined && voiceSegFailed.length) {
    uni.showToast({ title: `第 ${voiceSegFailed.join('、')} 段识别失败，其余已合并`, icon: 'none', duration: 2500 })
  }
}

/** 关闭底部语音面板（放弃本轮结果） */
function closeVoicePanel() {
  voicePanel.value = false
  voicePanelRecording.value = false
  voicePanelText.value = ''
  voiceNoResult.value = false
  voiceSegments = []
  voiceSegFailed = []
}

/** 确认面板文字 → AI 解析回填 */
function confirmVoicePanel() {
  const t = voicePanelText.value.trim()
  if (!t) {
    uni.showToast({ title: '没有识别到语音', icon: 'none' })
    return
  }
  closeVoicePanel()
  recognizeFromText(t)
}

function startVoiceRecord() {
  const rm = ensureVoiceRecorder()
  if (!rm) {
    uni.showToast({ title: '当前环境不支持录音', icon: 'none' })
    return
  }
  voiceSegments = []
  voiceSegFailed = []
  voiceSegIndex = 0
  voiceSegNo.value = 1
  voicePending = 0
  voiceChars.value = 0
  voiceStopRequested = false
  voiceFinished = false
  voiceAwaitingStop = false
  voiceDisposed = false
  recordingVoice = true
  voiceActive.value = true
  // 展开底部面板并进入录音态
  voicePanel.value = true
  voicePanelRecording.value = true
  voicePanelText.value = ''
  voiceNoResult.value = false
  beginVoiceSegment()
  uni.showToast({ title: '开始录音，说完点击下方录音条结束', icon: 'none', duration: 2500 })
}

function stopVoiceRecord() {
  if (voiceDisposed || voiceStopRequested) return
  voiceStopRequested = true
  clearVoiceTimer()
  voiceAwaitingStop = true
  // 面板仍保持展开，等转写回来后原位变成文字框
  voicePanelRecording.value = false
  uni.showLoading({ title: '整理识别结果...' })
  if (recorderManager) recorderManager.stop()
  armVoiceStopFallback()
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

    <!-- 语音面板（App 端）：录音态显示段号/秒数/已识别字数；结束后原位变文字框 -->
    <!-- #ifndef H5 -->
    <view v-if="voicePanel" class="voice-panel">
      <!-- 录音态 -->
      <template v-if="voicePanelRecording">
        <view class="vp-head">
          <view class="voice-dot" />
          <text class="vp-title">正在录音 · 第 {{ voiceSegNo }} 段 {{ voiceSeconds }}s</text>
          <text class="vp-count">已识别 {{ voiceChars }} 字</text>
        </view>
        <view class="vp-stop" @click="stopVoiceRecord">点击结束</view>
      </template>
      <!-- 结果态：文字框 -->
      <template v-else>
        <view class="vp-head">
          <text class="vp-title">{{ voiceNoResult ? '语音识别结果' : '识别完成，可修改后确认' }}</text>
          <text class="vp-close" @click="closeVoicePanel">✕</text>
        </view>
        <textarea
          v-model="voicePanelText"
          class="vp-textarea"
          :class="{ empty: voiceNoResult }"
          :placeholder="voiceNoResult ? '没有识别到语音' : ''"
          placeholder-class="vp-ph"
          auto-height
          :maxlength="-1"
        />
        <view class="vp-actions">
          <button class="vp-btn vp-again" @click="startVoiceRecord">重新录音</button>
          <button class="vp-btn vp-ok" :disabled="voiceNoResult" @click="confirmVoicePanel">确认识别</button>
        </view>
      </template>
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

/* 语音面板：底部卡片，录音态 → 结果态（文字框）原位切换 */
.voice-panel {
  position: fixed;
  left: 32rpx;
  right: 32rpx;
  bottom: 40rpx;
  z-index: 999;
  background: #ffffff;
  border-radius: 24rpx;
  padding: 28rpx 32rpx 24rpx;
  box-shadow: 0 12rpx 40rpx rgba(15, 23, 42, 0.18);
  border: 2rpx solid #e5e7eb;
}
.vp-head {
  display: flex;
  align-items: center;
  gap: 12rpx;
  margin-bottom: 20rpx;
}
.vp-title {
  flex: 1;
  font-size: 28rpx;
  font-weight: 600;
  color: #1e293b;
}
.vp-count {
  font-size: 24rpx;
  color: #2563eb;
}
.vp-close {
  font-size: 32rpx;
  color: #94a3b8;
  padding: 0 8rpx;
}
.vp-stop {
  padding: 20rpx 0;
  text-align: center;
  border-radius: 16rpx;
  background: #2563eb;
  color: #ffffff;
  font-size: 30rpx;
  font-weight: 600;
}
.vp-textarea {
  width: 100%;
  min-height: 160rpx;
  max-height: 420rpx;
  padding: 20rpx 24rpx;
  box-sizing: border-box;
  background: #f8fafc;
  border: 2rpx solid #e5e7eb;
  border-radius: 16rpx;
  font-size: 28rpx;
  line-height: 1.6;
  color: #0f172a;
}
.vp-textarea.empty { color: #94a3b8; }
.vp-ph { color: #94a3b8; }
.vp-actions {
  display: flex;
  gap: 20rpx;
  margin-top: 24rpx;
}
.vp-btn {
  flex: 1;
  height: 84rpx;
  line-height: 84rpx;
  font-size: 30rpx;
  border-radius: 16rpx;
  margin: 0;
}
.vp-btn::after { border: none; }
.vp-again {
  background: #f1f5f9;
  color: #334155;
}
.vp-ok {
  background: #2563eb;
  color: #ffffff;
}
.vp-ok[disabled] { opacity: 0.45; }
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
</style>
