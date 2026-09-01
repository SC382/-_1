<!-- AI 助手：鲲仑·平安（胸痛中心建设专属智能助手 · 知识库 AI 问答） -->
<script setup lang="ts">
import { nextTick, onUnmounted, reactive, ref } from 'vue'
import DoctorAPI, { type KbAskResult } from '@/api/module_cpx/doctor'
import { safeBack } from '@/utils/back'

definePage({
  name: 'ai',
  layout: 'tabbar',
  style: { navigationStyle: 'custom', navigationBarTitleText: '鲲仑·平安' },
})

type ChatMsg = { role: 'user' | 'ai'; content: string; sources?: { source_file: string; page_no: number }[] }
const messages = reactive<ChatMsg[]>([])
const question = ref('')
const loading = ref(false)
const typing = ref(false)
let typeTimer: ReturnType<typeof setInterval> | null = null

const scrollRef = ref<HTMLDivElement>()

// 语音输入：原生录音 → 后端 ASR 转写 → 填入提问框（仅 app-plus 支持原生录音，H5 降级提示）
const recording = ref(false)
const transcribing = ref(false)
let recorderManager: any = null

function ensureRecorder() {
  if (recorderManager) return recorderManager
  const rm: any = uni.getRecorderManager()
  if (!rm) return null
  rm.onStop((res: any) => {
    recording.value = false
    uni.getFileSystemManager().readFile({
      filePath: res.tempFilePath,
      encoding: 'base64',
      success: async (r: any) => {
        transcribing.value = true
        try {
          const data = await DoctorAPI.asr({ audio_base64: r.data as string, format: 'mp3' })
          question.value = data.text || ''
          uni.showToast({ title: '转写完成，可修改后发送', icon: 'none' })
        }
        catch (e: any) {
          uni.showToast({ title: e?.msg || '语音识别失败', icon: 'none' })
        }
        finally { transcribing.value = false }
      },
      fail: () => uni.showToast({ title: '读取录音失败', icon: 'none' }),
    })
  })
  rm.onError(() => {
    recording.value = false
    uni.showToast({ title: '录音失败', icon: 'none' })
  })
  recorderManager = rm
  return rm
}

function toggleRecord() {
  if ((uni.getSystemInfoSync() as any).platform !== 'app-plus') {
    uni.showToast({ title: '请在 App 端使用录音', icon: 'none' })
    return
  }
  const rm = ensureRecorder()
  if (!rm) {
    uni.showToast({ title: '当前环境不支持录音', icon: 'none' })
    return
  }
  if (recording.value) rm.stop()
  else { recording.value = true; rm.start({ format: 'mp3', sampleRate: 16000 }) }
}

// 问心推荐问题（参考"胸痛中心认证帮扶"高频问题）
const QUICK_QUESTIONS = [
  '建设胸痛中心应具备哪些心血管专科条件？',
  '医院内部需要在哪里体现标识与指引？',
  '如何建立时钟统一制度并管理？',
  '医院低危病例非常多，能否不上报？',
  '胸痛中心认证申请流程是什么？',
  '胸痛中心认证要求的数据上报比例是多少？',
  '最新的胸痛中心认证标准在哪可以下载？',
]

function buildSourceLine(sources: { source_file: string; page_no: number }[]): string {
  if (!sources || !sources.length) return ''
  const seen = new Set<string>()
  const parts: string[] = []
  for (const s of sources) {
    const key = `${s.source_file}|${s.page_no}`
    if (seen.has(key)) continue
    seen.add(key)
    parts.push(`《${s.source_file}》（第${s.page_no}页）`)
  }
  return `\n\n【依据：${parts.join('、')}】`
}

function stopTyping() {
  if (typeTimer) {
    clearInterval(typeTimer)
    typeTimer = null
  }
  typing.value = false
}

function scrollToBottom() {
  nextTick(() => {
    // #ifdef MP-WEIXIN
    // uni.pageScrollTo({ scrollTop: 99999, duration: 100 })
    // #endif
  })
}

async function ask(q?: string) {
  const text = (q ?? question.value).trim()
  if (!text) {
    uni.showToast({ title: '请输入问题', icon: 'none' })
    return
  }
  if (q) question.value = q
  stopTyping()
  loading.value = true

  // 推入用户消息
  messages.push({ role: 'user', content: text })

  // 推入 AI 占位消息（流式填充）
  const aiIndex = messages.length
  messages.push({ role: 'ai', content: '' })

  try {
    const res = await DoctorAPI.kbAsk(text)
    const r = res as unknown as KbAskResult
    const answer = r.answer || '暂未找到相关内容，请换个问法或联系院内管理员补充知识库。'
    const sources = r.sources || []
    const full = answer + buildSourceLine(sources)

    // 打字机效果逐字显示（流式）
    typing.value = true
    let i = 0
    typeTimer = setInterval(() => {
      i++
      messages[aiIndex].content = full.slice(0, i)
      messages[aiIndex].sources = sources
      if (i >= full.length) {
        stopTyping()
      }
      scrollToBottom()
    }, 18)
  }
  catch {
    messages[aiIndex].content = '请求失败，请稍后重试'
    messages[aiIndex].sources = []
  }
  finally {
    loading.value = false
    question.value = ''
    scrollToBottom()
  }
}

function onSendTap() {
  ask()
}

function onClearChat() {
  stopTyping()
  messages.splice(0, messages.length)
  question.value = ''
}

onUnmounted(() => {
  stopTyping()
  if (recording.value && recorderManager) recorderManager.stop()
})
</script>

<template>
  <view class="ai-page">
    <!-- 自定义导航栏（蓝紫色） -->
    <view class="ai-header">
      <text class="header-back" @click="() => safeBack()">‹</text>
      <text class="header-title">鲲仑·平安</text>
      <text class="header-menu" @click="onClearChat">⋯</text>
    </view>

    <!-- 首次进入：欢迎区 + 常见问题 -->
    <template v-if="messages.length === 0">
      <view class="welcome-card">
        <view class="welcome-row">
          <view class="welcome-avatar">
            <image class="avatar-img" src="/static/images/ai-bot.png" mode="aspectFit" />
          </view>
          <view class="welcome-text">
            <text class="welcome-hi">Hi，我是"鲲仑·平安"</text>
            <text class="welcome-desc">您好，我是鲲仑·平安，您身边之胸痛中心建设专属智能助手，可以为您解答填报、认证、质控、诊疗相关问题，快来体验一下吧~</text>
          </view>
        </view>
      </view>

      <view class="quick-block">
        <text class="quick-tip">您可以这样问~</text>
        <view class="quick-list">
          <view
            v-for="q in QUICK_QUESTIONS"
            :key="q"
            class="quick-item"
            @click="ask(q)"
          >
            <text class="quick-text">{{ q }}</text>
            <text class="quick-arrow">›</text>
          </view>
        </view>
      </view>
    </template>

    <!-- 对话历史 -->
    <scroll-view v-else class="chat-scroll" scroll-y :scroll-into-view="''">
      <view
        v-for="(m, i) in messages"
        :key="i"
        class="msg-row"
        :class="{ user: m.role === 'user' }"
      >
        <view v-if="m.role === 'user'" class="bubble user-bubble">{{ m.content }}</view>
        <view v-else class="bubble ai-bubble">
          <view v-if="!m.content && loading && i === messages.length - 1" class="typing">
            <text class="dot"></text><text class="dot"></text><text class="dot"></text>
          </view>
          <text v-else class="ai-content">{{ m.content }}</text>
        </view>
      </view>
    </scroll-view>

    <!-- 底部输入栏 -->
    <view class="input-bar">
      <view class="mic-btn" :class="{ recording: recording || transcribing }" @click="toggleRecord">
        <image class="mic-icon" src="/static/icons/mic.svg" mode="aspectFit" />
      </view>
      <view class="input-wrap">
        <input
          v-model="question"
          class="input"
          placeholder="请问我有什么可以帮您?"
          placeholder-class="input-placeholder"
          confirm-type="send"
          @confirm="onSendTap"
        />
      </view>
      <view class="send-btn" @click="onSendTap">
        <text class="send-icon">↑</text>
      </view>
    </view>
  </view>
</template>

<style lang="scss" scoped>
.ai-page {
  min-height: 100vh;
  background: #f5f7fa;
  display: flex;
  flex-direction: column;
  padding-bottom: calc(140px + 52px + env(safe-area-inset-bottom));
}
.ai-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 88rpx;
  padding: 0 24rpx;
  padding-top: var(--status-bar-height, 44rpx);
  background: linear-gradient(135deg, #6366f1 0%, #7c3aed 100%);
  color: #ffffff;
}
.header-back,
.header-menu {
  font-size: 48rpx;
  width: 60rpx;
  text-align: center;
  font-weight: 500;
  line-height: 1;
}
.header-title {
  font-size: 34rpx;
  font-weight: 600;
  letter-spacing: 2rpx;
}

.welcome-card {
  margin: 32rpx 32rpx 24rpx;
  padding: 32rpx;
  background: #ffffff;
  border-radius: 24rpx;
  box-shadow: 0 4rpx 16rpx rgba(15, 23, 42, 0.04);
}
.welcome-row {
  display: flex;
  align-items: flex-start;
  gap: 24rpx;
}
.welcome-avatar {
  flex-shrink: 0;
  width: 96rpx;
  height: 96rpx;
  border-radius: 50%;
  background: linear-gradient(135deg, #3b82f6 0%, #6366f1 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}
.avatar-img {
  width: 96rpx;
  height: 96rpx;
}
.avatar-icon {
  font-size: 56rpx;
}
.welcome-text {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 8rpx;
}
.welcome-hi {
  font-size: 30rpx;
  font-weight: 700;
  color: #1f2937;
}
.welcome-desc {
  font-size: 25rpx;
  line-height: 1.6;
  color: #4b5563;
}

.quick-block {
  margin: 0 32rpx 32rpx;
}
.quick-tip {
  display: block;
  margin-bottom: 16rpx;
  font-size: 26rpx;
  color: #6b7280;
}
.quick-list {
  display: flex;
  flex-direction: column;
  gap: 16rpx;
}
.quick-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 24rpx 28rpx;
  background: #ffffff;
  border-radius: 16rpx;
  box-shadow: 0 2rpx 8rpx rgba(15, 23, 42, 0.04);
}
.quick-text {
  flex: 1;
  font-size: 27rpx;
  color: #1f2937;
}
.quick-arrow {
  font-size: 36rpx;
  color: #9ca3af;
  margin-left: 16rpx;
  line-height: 1;
}

.msg-row {
  display: flex;
  margin: 16rpx 32rpx;
}
.msg-row.user {
  justify-content: flex-end;
}
.bubble {
  max-width: 80%;
  padding: 20rpx 24rpx;
  border-radius: 20rpx;
  font-size: 28rpx;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
}
.user-bubble {
  background: #3b82f6;
  color: #ffffff;
  border-bottom-right-radius: 6rpx;
}
.ai-bubble {
  background: #ffffff;
  color: #1f2937;
  border-bottom-left-radius: 6rpx;
  box-shadow: 0 2rpx 8rpx rgba(15, 23, 42, 0.04);
}
.ai-content {
  white-space: pre-wrap;
}
.typing {
  display: flex;
  gap: 8rpx;
  padding: 4rpx 0;
}
.typing .dot {
  width: 12rpx;
  height: 12rpx;
  border-radius: 50%;
  background: #cbd5e1;
  animation: blink 1.2s infinite ease-in-out;
}
.typing .dot:nth-child(2) {
  animation-delay: 0.2s;
}
.typing .dot:nth-child(3) {
  animation-delay: 0.4s;
}
@keyframes blink {
  0%, 80%, 100% { opacity: 0.3; }
  40% { opacity: 1; }
}

.input-bar {
  position: fixed;
  left: 0;
  right: 0;
  bottom: calc(52px + env(safe-area-inset-bottom));
  z-index: 100;
  display: flex;
  align-items: center;
  gap: 16rpx;
  padding: 16rpx 24rpx;
  background: #ffffff;
  border-top: 2rpx solid #e5e7eb;
}
.mic-btn,
.send-btn {
  flex-shrink: 0;
  width: 72rpx;
  height: 72rpx;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}
.mic-btn {
  background: #f3f4f6;
}
.mic-btn.recording {
  background: #ef4444;
  animation: mic-pulse 1s infinite;
}
@keyframes mic-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}
.mic-icon {
  width: 30rpx;
  height: 30rpx;
}
.send-btn {
  background: #3b82f6;
}
.send-icon {
  color: #ffffff;
  font-size: 40rpx;
  font-weight: 600;
  line-height: 1;
}
.input-wrap {
  flex: 1;
}
.input {
  background: #f5f7fa;
  border-radius: 36rpx;
  padding: 16rpx 28rpx;
  font-size: 28rpx;
  height: 72rpx;
}
.input-placeholder {
  color: #9ca3af;
}
</style>