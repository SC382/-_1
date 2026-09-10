<!-- AI 语音录入：录音 → 真实语音转写 → AI 解析字段 → 回填病例 -->
<script setup lang="ts">
import { ref } from 'vue'
import { onLoad, onUnload } from '@dcloudio/uni-app'
import DoctorAPI, { type CaseRecordItem, type TemplateField } from '@/api/module_cpx/doctor'

definePage({
  name: 'ai-voice',
  style: { navigationBarTitleText: 'AI语音录入' },
})

const cases = ref<CaseRecordItem[]>([])
const caseId = ref(0)
const templateId = ref(0)
const text = ref('')
const recording = ref(false)
const transcribing = ref(false)
const parsing = ref(false)
const saving = ref(false)
const parsed = ref<Record<string, string>>({})
/** 当前病例所用模板的字段清单（用于把 AI 结果按 field_code 精确匹配） */
const tplFields = ref<TemplateField[]>([])

/** 结果行中文标签兜底字典（优先用模板字段自带的中文名） */
const FIELDS_LABEL: Record<string, string> = {
  patient_name: '患者姓名',
  gender: '性别',
  age: '年龄',
  birth_date: '出生日期',
  id_type: '证件类型',
  id_number: '身份证号',
  phone: '联系电话',
  come_type: '来院方式',
  onset_address: '发病地址',
  detail_address: '详细地址',
  insurance_type: '医保类型',
  insurance_no: '医保编号',
  chief_complaint: '主诉',
  onset_time: '发病时间',
  pre_medication: '院前用药',
  triage_result: '分诊结果',
  diagnose_type: '诊断',
  discharge_medication: '出院用药',
}

/** 选择目标病例：picker 下标 → caseId；同时拉取该病例模板字段，供 AI 结果精确匹配 */
async function onCaseChange(e: { detail: { value: number } }) {
  caseId.value = cases.value[e.detail.value].id
  parsed.value = {}
  tplFields.value = []
  try {
    const detail = await DoctorAPI.caseDetail(caseId.value)
    templateId.value = detail.template_id || 0
    tplFields.value = detail.fields || []
  }
  catch { /* toast */ }
}

/** 结果行中文标签：优先模板字段中文名，其次兜底字典，最后原样展示 */
function labelOf(code: string) {
  const f = tplFields.value.find((x) => x.field_code === code)
  return f?.field_name || FIELDS_LABEL[code] || code
}

onLoad(async () => {
  try {
    const res = await DoctorAPI.myCases({ page_no: 1, page_size: 50 })
    cases.value = res.items
  }
  catch { /* toast */ }
})

onUnload(() => { disposeVoice() })

// 原生录音 → base64 → 后端 ASR 转写（仅 app-plus 支持原生录音，H5 降级提示）
// 智谱 ASR 单次音频硬限制 30 秒（错误码 1214），故每段录满 28 秒自动切段续录：
// 用户一直说到说完，各段文字按段号顺序拼接后落入输入框，再由用户点击「AI 解析录入」。
let recorderManager: any = null
let recordTimer: any = null
let stopFallback: any = null
/** 当前段号（从 1 起，仅用于展示） */
const segNo = ref(1)
/** 已转写累计字数（仅用于展示） */
const chars = ref(0)
/** 各段转写文本，下标 = 段下标（0 起），保证按口述顺序拼接 */
let segments: string[] = []
/** 识别失败的段号（从 1 起），用于最终提示 */
let segFailed: number[] = []
/** 当前段下标（0 起） */
let segIndex = 0
/** 在途转写请求数 */
let pending = 0
/** 用户已点击结束，不再续录 */
let stopRequested = false
/** 本轮是否已结算，防止重复写入输入框 */
let finished = false
/** 已调用 stop()、等待 onStop 回调（同时用于拦截重复回调） */
let awaitingStop = false
/** 页面已卸载，丢弃后续回调 */
let disposed = false
/** 录音开始前输入框已有内容，结算时保留在拼接结果之前 */
let textBefore = ''

function clearRecordTimer() {
  if (recordTimer) {
    clearInterval(recordTimer)
    recordTimer = null
  }
}

function clearStopFallback() {
  if (stopFallback) {
    clearTimeout(stopFallback)
    stopFallback = null
  }
}

/** stop() 后 3 秒仍未收到 onStop/onError（如录音未真正启动）的兜底，防止卡死 */
function armStopFallback() {
  clearStopFallback()
  stopFallback = setTimeout(() => {
    stopFallback = null
    if (!awaitingStop) return
    awaitingStop = false
    clearRecordTimer()
    if (stopRequested) {
      recording.value = false
      checkFinish()
    }
    else {
      startNextSegment()
    }
  }, 3000)
}

function updateChars() {
  chars.value = segments.filter(Boolean).join('').length
}

function ensureRecorder() {
  if (recorderManager) return recorderManager
  const rm: any = uni.getRecorderManager()
  if (!rm) return null
  rm.onStop((res: any) => {
    // 只处理本端主动发起的 stop()，拦截重复回调，避免段号乱跳
    if (!awaitingStop) return
    awaitingStop = false
    clearStopFallback()
    clearRecordTimer()
    const segIdx = segIndex
    const segNoCur = segIdx + 1
    const fs = uni.getFileSystemManager()
    fs.readFile({
      filePath: res.tempFilePath,
      encoding: 'base64',
      success: (r: any) => {
        if (disposed) return
        // 先把下一段录起来，再后台上传本段 —— 段间停顿最短
        if (!stopRequested) startNextSegment()
        pending += 1
        uploadSegment(segIdx, segNoCur, r.data as string)
      },
      fail: () => {
        if (disposed) return
        if (!stopRequested) {
          startNextSegment()
        }
        else {
          segFailed.push(segNoCur)
          uni.showToast({ title: `第 ${segNoCur} 段读取失败，已跳过`, icon: 'none' })
        }
        checkFinish()
      },
    })
  })
  rm.onError(() => {
    awaitingStop = false
    clearStopFallback()
    clearRecordTimer()
    recording.value = false
    if (!stopRequested) {
      stopRequested = true
      uni.showToast({ title: '录音中断，已结束', icon: 'none' })
    }
    checkFinish()
  })
  recorderManager = rm
  return rm
}

/** 开始录当前段：录满 28 秒自动切段（智谱单次音频上限 30 秒，留 2 秒余量） */
function beginSegment() {
  if (!recorderManager) return
  clearRecordTimer()
  let sec = 0
  recordTimer = setInterval(() => {
    sec += 1
    if (sec >= 28) {
      clearRecordTimer()
      awaitingStop = true
      recorderManager.stop()
      armStopFallback()
    }
  }, 1000)
  recorderManager.start({ format: 'mp3', sampleRate: 16000 })
}

/** 续录下一段（段号 +1） */
function startNextSegment() {
  if (disposed || stopRequested) return
  segIndex += 1
  segNo.value = segIndex + 1
  beginSegment()
}

/** 后台上传单段音频做 ASR，结果按段号入缓存（不覆盖其他段） */
async function uploadSegment(segIdx: number, segNoCur: number, base64: string) {
  try {
    const data = await DoctorAPI.asr({ audio_base64: base64, format: 'mp3' })
    const t = (data.text || '').trim()
    if (t) segments[segIdx] = t
    else segFailed.push(segNoCur)
  }
  catch {
    segFailed.push(segNoCur)
  }
  finally {
    pending -= 1
    updateChars()
    checkFinish()
  }
}

/** 用户已结束且所有段都返回 → 结算 */
function checkFinish() {
  if (disposed || finished) return
  if (!stopRequested || pending > 0) return
  finished = true
  clearRecordTimer()
  clearStopFallback()
  recording.value = false
  transcribing.value = false
  const joined = segments.filter(Boolean).join('').trim()
  if (!joined) {
    uni.showToast({
      title: segFailed.length ? '语音识别失败，请重试' : '未识别到内容，请重试',
      icon: 'none',
    })
    return
  }
  const okSegs = segments.filter(Boolean).length
  // 保留录音前已输入的内容，避免被冲掉
  text.value = (textBefore ? `${textBefore}\n` : '') + joined
  if (segFailed.length) {
    uni.showToast({ title: `第 ${segFailed.join('、')} 段识别失败，其余已合并`, icon: 'none', duration: 2500 })
  }
  else {
    uni.showToast({ title: `转写完成，共 ${okSegs} 段 ${joined.length} 字`, icon: 'success' })
  }
}

function toggleRecord() {
  // 仅 App 端（真机 / 自定义基座）支持原生录音
  if ((uni.getSystemInfoSync() as any).platform !== 'app-plus') {
    uni.showToast({ title: '请在 App 端使用录音', icon: 'none' })
    return
  }
  const rm = ensureRecorder()
  if (!rm) {
    uni.showToast({ title: '当前环境不支持录音', icon: 'none' })
    return
  }
  if (recording.value) {
    stopLoop()
    return
  }
  // 开始新一轮分段录音
  segments = []
  segFailed = []
  segIndex = 0
  segNo.value = 1
  pending = 0
  chars.value = 0
  stopRequested = false
  finished = false
  awaitingStop = false
  disposed = false
  textBefore = text.value.trim()
  recording.value = true
  beginSegment()
  uni.showToast({ title: '开始录音，说完再点一次结束', icon: 'none', duration: 2500 })
}

/** 结束整轮录音（当前段转写完再按序拼接） */
function stopLoop() {
  if (!recording.value) return
  stopRequested = true
  clearRecordTimer()
  recording.value = false
  transcribing.value = true
  // 若正处于自动切段（stop 已在途），等这次 onStop 回来即可，不重复调用 stop()
  if (awaitingStop) return
  awaitingStop = true
  if (recorderManager) recorderManager.stop()
  armStopFallback()
}

/** 离开页面：停循环、清计时器、丢弃未完成回调 */
function disposeVoice() {
  disposed = true
  stopRequested = true
  finished = true
  awaitingStop = false
  clearRecordTimer()
  clearStopFallback()
  recording.value = false
  if (recorderManager) {
    try { recorderManager.stop() }
    catch { /* 忽略：可能未在录音 */ }
  }
}

/** AI 解析：转写文本 → 后端真实 AI 提取字段 → 按当前模板 field_code 精确匹配 */
async function parseText() {
  const t = text.value.trim()
  if (!t) {
    uni.showToast({ title: '请先录音转写或输入文本', icon: 'none' })
    return
  }
  if (!caseId.value) {
    uni.showToast({ title: '请先选择目标病例', icon: 'none' })
    return
  }
  parsing.value = true
  try {
    const info = await DoctorAPI.recognize({ text: t }) as Record<string, string>
    const matched = mapToTemplate(info || {})
    parsed.value = matched
    const n = Object.keys(matched).length
    if (!n) {
      uni.showToast({ title: '未匹配到当前模板字段，请核对内容', icon: 'none' })
    }
    else {
      uni.showModal({
        title: 'AI 识别完成',
        content: `已匹配 ${n} 个字段，请核对后回填病例`,
        showCancel: false,
      })
    }
  }
  catch (e: any) {
    uni.showToast({ title: e?.msg || 'AI 解析失败，请重试', icon: 'none' })
  }
  finally {
    parsing.value = false
  }
}

/** 证件类型归一化（AI 常把身份证卡面「公民身份号码」误判为证件类型） */
function normCard(v: string): string {
  const s = String(v).trim()
  if (!s) return s
  if (/身份证|居民身份证|二代身份证|居民身分证/.test(s)) return '身份证'
  if (/医保|医疗保险|医疗保险卡|社保卡|社会保障卡/.test(s)) return '医保卡'
  if (/公民身份号码|身份证号码|证件号码/.test(s)) return '身份证'
  return s
}

/** AI 返回（标准编码 / 中文名）→ 当前模板 field_code 双通道匹配，只保留模板里真实存在的字段 */
function mapToTemplate(info: Record<string, string>): Record<string, string> {
  const alias: Record<string, string> = {
    patient_name: 'patient_name', '姓名': 'patient_name', '患者姓名': 'patient_name',
    gender: 'gender', '性别': 'gender',
    age: 'age', '年龄': 'age',
    birth_date: 'birth_date', '出生日期': 'birth_date',
    id_number: 'id_number', '身份证号': 'id_number', id_no: 'id_number',
    id_type: 'id_type', '证件类型': 'id_type', card_type: 'card_type',
    phone: 'phone', '联系电话': 'phone', '电话': 'phone',
    come_type: 'come_type', '来院方式': 'come_type',
    onset_address: 'onset_address', '发病地址': 'onset_address',
    detail_address: 'detail_address', '详细地址': 'detail_address',
    insurance_type: 'insurance_type', '医保类型': 'insurance_type', insurance: 'insurance',
    insurance_no: 'insurance_no', '医保编号': 'insurance_no', '医保号': 'insurance_no',
    chief_complaint: 'chief_complaint', '主诉': 'chief_complaint',
    diagnose_type: 'diagnose_type', '诊断': 'diagnose_type', '诊断类型': 'diagnose_type',
  }
  const tplCodes = new Set(tplFields.value.map((f) => f.field_code))
  const result: Record<string, string> = {}
  for (const [k, v] of Object.entries(info)) {
    if (!v) continue
    let code = alias[k] || alias[String(k).trim()]
    if (!code && tplCodes.has(k)) code = k
    if (code && tplCodes.has(code)) {
      result[code] = (code === 'card_type' || code === 'id_type') ? normCard(v) : v
    }
  }
  return result
}

async function handleFill() {
  if (!caseId.value) {
    uni.showToast({ title: '请选择病例', icon: 'none' })
    return
  }
  if (!Object.keys(parsed.value).length) {
    uni.showToast({ title: '暂无可回填内容', icon: 'none' })
    return
  }
  saving.value = true
  try {
    // 模板 id 在选择病例时已取得，此处仅兜底
    if (!templateId.value) {
      const detail = await DoctorAPI.caseDetail(caseId.value)
      templateId.value = detail.template_id || 0
    }
    await DoctorAPI.saveForm(caseId.value, { template_id: templateId.value, form_data: { ...parsed.value } })
    uni.showToast({ title: '已回填病例', icon: 'success' })
  }
  catch { /* toast */ }
  finally { saving.value = false }
}
</script>

<template>
  <view class="voice-page">
    <view class="card">
      <text class="label">目标病例</text>
      <picker
        :range="cases"
        range-key="case_no"
        @change="onCaseChange"
      >
        <view class="picker-box" :class="{ empty: !caseId }">
          {{ cases.find((c) => c.id === caseId)?.case_no || '请选择病例' }}
        </view>
      </picker>
    </view>

    <view class="card">
      <text class="label">语音转写</text>
      <button class="mic-btn" :class="{ recording }" :disabled="transcribing" @click="toggleRecord">
        {{ recording ? ('⏹ 结束录音（第 ' + segNo + ' 段 · 已转写 ' + chars + ' 字）') : (transcribing ? '整理识别结果...' : '🎙️ 点击开始录音') }}
      </button>
      <text v-if="recording" class="rec-tip">可连续口述，每 28 秒自动续录一段，说完再点上方按钮结束</text>
      <textarea v-model="text" class="voice-input" :disabled="recording" placeholder="录音自动转写为文字，也可手动输入：如 患者胸痛2小时，8点发病，已给予阿司匹林，分诊为高危" placeholder-class="ph" />
      <button class="parse-btn" :disabled="parsing || !text.trim()" @click="parseText">
        {{ parsing ? '解析中...' : 'AI 解析录入' }}
      </button>
    </view>

    <view v-if="Object.keys(parsed).length" class="card">
      <text class="label">解析结果（可修改）</text>
      <view v-for="(v, k) in parsed" :key="k" class="result-row">
        <text class="result-key">{{ labelOf(k) }}</text>
        <input v-model="parsed[k]" class="result-input" />
      </view>
      <button class="fill-btn" :disabled="saving" @click="handleFill">
        {{ saving ? '回填中...' : '确认回填病例' }}
      </button>
    </view>
  </view>
</template>

<style lang="scss" scoped>
.voice-page { min-height: 100vh; background: #f3f4f6; padding: 24rpx 32rpx 60rpx; }
.card { margin-bottom: 24rpx; padding: 32rpx; border-radius: 24rpx; background: #ffffff; }
.label { display: block; font-size: 26rpx; color: #4b5563; margin-bottom: 16rpx; }

.picker-box {
  height: 88rpx;
  line-height: 88rpx;
  padding: 0 24rpx;
  border-radius: 16rpx;
  background: #f3f4f6;
  font-size: 28rpx;
  color: #1f2937;
}
.picker-box.empty { color: #9ca3af; }

.mic-btn {
  height: 88rpx;
  line-height: 88rpx;
  border-radius: 18rpx;
  background: linear-gradient(135deg, #10b981, #0ea5e9);
  color: #ffffff;
  font-size: 30rpx;
  font-weight: 600;
}
.mic-btn::after { border: none; }
.mic-btn.recording {
  background: linear-gradient(135deg, #ef4444, #f97316);
  font-size: 26rpx;
  animation: pulse 1s infinite;
}
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}
.rec-tip {
  display: block;
  margin-top: 16rpx;
  font-size: 22rpx;
  line-height: 1.5;
  color: #6b7280;
}

.voice-input {
  width: 100%;
  min-height: 160rpx;
  margin-top: 20rpx;
  padding: 20rpx 24rpx;
  border-radius: 16rpx;
  background: #f3f4f6;
  font-size: 28rpx;
  box-sizing: border-box;
}
.ph { color: #9ca3af; }

.parse-btn {
  margin-top: 20rpx;
  height: 88rpx;
  line-height: 88rpx;
  border-radius: 18rpx;
  background: linear-gradient(135deg, #7c3aed, #6366f1);
  color: #ffffff;
  font-size: 30rpx;
  font-weight: 600;
}
.parse-btn::after { border: none; }

.result-row { display: flex; align-items: center; gap: 16rpx; margin-bottom: 16rpx; }
.result-key {
  width: 200rpx;
  font-size: 26rpx;
  color: #4b5563;
  background: #f3f4f6;
  padding: 0 16rpx;
  border-radius: 12rpx;
  height: 80rpx;
  line-height: 80rpx;
}
.result-input {
  flex: 1;
  height: 80rpx;
  padding: 0 20rpx;
  border-radius: 12rpx;
  background: #f3f4f6;
  font-size: 28rpx;
}

.fill-btn {
  margin-top: 24rpx;
  height: 88rpx;
  line-height: 88rpx;
  border-radius: 18rpx;
  background: linear-gradient(135deg, #10b981, #0ea5e9);
  color: #ffffff;
  font-size: 30rpx;
  font-weight: 600;
}
.fill-btn::after { border: none; }
</style>
