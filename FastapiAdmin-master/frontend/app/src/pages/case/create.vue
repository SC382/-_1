<!-- 患者建档（基本信息）：蓝色自定义导航栏 + 白底表单 + 通栏深蓝保存按钮 -->
<script setup lang="ts">
import { ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import DoctorAPI, { type DoctorTemplate } from '@/api/module_cpx/doctor'

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
const idTypeOptions = ['身份证', '社保卡', '其他']
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
  uni.navigateBack()
}

// ── AI 智能录入（语音/拍照/本地上传/证件扫描，OCR/ASR 二期接入，识别结果可修改后回填）──
function fillFromRecognized(data: Record<string, string>) {
  if (data.patient_name) form.value.patient_name = data.patient_name
  if (data.gender) form.value.gender = data.gender
  if (data.age) form.value.age = data.age
  if (data.phone) form.value.phone = data.phone
  uni.showToast({ title: '识别完成，请核对', icon: 'success' })
}

/** AI 智能录入主入口 */
function aiEntry() {
  uni.showActionSheet({
    itemList: ['证件扫描', '语音输入', '照片拍摄', '本地上传'],
    success: (res) => {
      if (res.tapIndex === 0) idCardEntry()
      else if (res.tapIndex === 1) voiceInput()
      else if (res.tapIndex === 2) imageRecognize('camera')
      else imageRecognize('album')
    },
  })
}

/** 证件扫描：身份证/医保卡 → 照片拍摄/本地上传 → OCR 回填 */
function idCardEntry() {
  uni.showActionSheet({
    itemList: ['身份证', '医保卡'],
    success: (res) => chooseIdCardSource(res.tapIndex === 0 ? '身份证' : '医保卡'),
  })
}

/** 调起摄像头拍照（H5 用 input capture 强制相机；App/小程序用原生相机） */
function pickCameraPhoto(onGot: () => void) {
  // #ifdef H5
  const input = document.createElement('input')
  input.type = 'file'
  input.accept = 'image/*'
  input.capture = 'environment'
  input.style.display = 'none'
  input.onchange = () => { onGot(); document.body.removeChild(input) }
  document.body.appendChild(input)
  input.click()
  // #endif
  // #ifndef H5
  uni.chooseImage({ count: 1, sourceType: ['camera'], success: onGot })
  // #endif
}

function pickAlbumPhoto(onGot: () => void) {
  uni.chooseImage({ count: 1, sourceType: ['album'], success: onGot })
}

function chooseIdCardSource(cardType: string) {
  uni.showActionSheet({
    itemList: ['照片拍摄', '本地上传'],
    success: (res) => {
      const recognize = () => {
        uni.showLoading({ title: '证件识别中...' })
        setTimeout(() => {
          uni.hideLoading()
          fillFromRecognized({ patient_name: '识别-张三', gender: '男', age: '56', phone: '' })
          uni.showToast({ title: `${cardType}识别完成`, icon: 'success' })
        }, 1200)
      }
      if (res.tapIndex === 0) pickCameraPhoto(recognize)
      else pickAlbumPhoto(recognize)
    },
  })
}

/** AI 语音识别：语音转文字 → 解析姓名/电话回填（模拟） */
function voiceInput() {
  uni.showModal({
    title: 'AI 语音录入',
    editable: true,
    placeholderText: '长按录音转文字（模拟），或直接输入：如「患者李四，男，58岁，电话13812345678」',
    success: (res) => {
      if (!res.confirm || !res.content) return
      const t = res.content
      const data: Record<string, string> = {}
      const nameMatch = t.match(/(?:患者|姓名)?\s*([\u4e00-\u9fa5]{2,4})(?:，|,|男|女)/)
      if (nameMatch) data.patient_name = nameMatch[1]
      if (t.includes('男')) data.gender = '男'
      else if (t.includes('女')) data.gender = '女'
      const ageMatch = t.match(/(\d{1,3})岁/)
      if (ageMatch) data.age = ageMatch[1]
      const phoneMatch = t.match(/1[3-9]\d{9}/)
      if (phoneMatch) data.phone = phoneMatch[1]
      if (Object.keys(data).length) fillFromRecognized(data)
      else uni.showToast({ title: '未识别到有效信息', icon: 'none' })
    },
  })
}

/** 图片识别：照片拍摄/本地上传 → OCR 提取姓名/电话回填（模拟） */
function imageRecognize(sourceType: 'camera' | 'album') {
  const recognize = () => {
    uni.showLoading({ title: '图片识别中...' })
    setTimeout(() => {
      uni.hideLoading()
      fillFromRecognized({ patient_name: '识别-王五', gender: '', age: '61', phone: '13912345678' })
    }, 1200)
  }
  if (sourceType === 'camera') pickCameraPhoto(recognize)
  else pickAlbumPhoto(recognize)
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
          <picker mode="date" :value="form.birth_date" @change="form.birth_date = $event.detail.value">
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
</style>
