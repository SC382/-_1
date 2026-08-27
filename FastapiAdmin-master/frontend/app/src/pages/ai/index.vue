<!-- AI 助手：认证帮扶问答（知识库 AI 问答，流式打字机展示，回答末尾直接标注来源） -->
<script setup lang="ts">
import { onUnmounted, ref } from 'vue'
import DoctorAPI, { type KbAskResult } from '@/api/module_cpx/doctor'

definePage({
  name: 'ai',
  layout: 'tabbar',
  style: { navigationBarTitleText: '认证帮扶问答' },
})

const question = ref('')
const loading = ref(false)
const asked = ref(false)
// 流式展示
const displayText = ref('')     // 打字机当前已显示文本
const fullText = ref('')        // 完整回答（含末尾【依据】行）
const typing = ref(false)       // 是否正在打字
let typeTimer: ReturnType<typeof setInterval> | null = null

// 快捷问题（点击直接提问）
const QUICK_QUESTIONS = [
  'STEMI 患者 D2W 时间标准是多少？',
  '首份心电图的时间要求是什么？',
  'ACS 出院患者随访要求是什么？',
  '再认证需要准备哪些材料？',
]

/** 把结构化来源拼成回答末尾的依据行： 【依据：《文件》（第X页）、《文件》（第Y页）】 */
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
  return `【依据：${parts.join('、')}】`
}

/** 停止打字机 */
function stopTyping() {
  if (typeTimer) {
    clearInterval(typeTimer)
    typeTimer = null
  }
  typing.value = false
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
  asked.value = true
  displayText.value = ''
  fullText.value = ''
  try {
    const res = await DoctorAPI.kbAsk(text)
    // 回答正文 + 末尾直接标注来源（不依赖模型自觉，前端固定拼接）
    const srcLine = buildSourceLine(res.sources)
    fullText.value = res.answer + (srcLine ? `\n\n${srcLine}` : '')
    // 流式打字机：每 25ms 追加 2 个字符
    typing.value = true
    let i = 0
    typeTimer = setInterval(() => {
      i += 2
      displayText.value = fullText.value.slice(0, i)
      if (i >= fullText.value.length) {
        stopTyping()
      }
    }, 25)
  }
  catch {
    /* http 层已 toast */
  }
  finally {
    loading.value = false
  }
}

onUnmounted(stopTyping)
</script>

<template>
  <view class="qa-page">
    <!-- 输入区 -->
    <view class="ask-bar">
      <input
        v-model="question"
        class="ask-input"
        placeholder="输入认证/质控问题，如：D2W 时间标准"
        placeholder-class="ph"
        confirm-type="search"
        confirm-hold
        @confirm="ask()"
      />
      <view class="ask-btn" :class="{ disabled: loading }" @click="ask()">
        <text v-if="!loading">提问</text>
        <text v-else>…</text>
      </view>
    </view>

    <!-- 快捷问题 -->
    <view class="quick-wrap">
      <text class="quick-label">快捷提问</text>
      <view class="quick-tags">
        <view v-for="q in QUICK_QUESTIONS" :key="q" class="quick-tag" @click="ask(q)">
          <text class="quick-text">{{ q }}</text>
        </view>
      </view>
    </view>

    <!-- 回答区（流式打字机） -->
    <view v-if="loading" class="answer-loading">
      <text class="loading-icon">🤖</text>
      <text class="loading-text">AI 正在查阅知识库，请稍候…</text>
    </view>

    <view v-else-if="asked" class="answer-card">
      <view class="answer-q">
        <text class="q-mark">问</text>
        <text class="q-text">{{ question }}</text>
      </view>
      <view class="answer-a">
        <text class="a-mark">答</text>
        <text class="a-text">
          {{ displayText }}<text v-if="typing" class="cursor">▌</text>
        </text>
      </view>
    </view>

    <view v-else class="hint">
      <text class="hint-title">💡 知识库说明</text>
      <text class="hint-line">· 依据《中国胸痛中心认证标准（第六版）》</text>
      <text class="hint-line">· 依据《中国胸痛中心再认证标准（标准版）》</text>
      <text class="hint-line">· 每个回答末尾将直接标注依据来源（文件名 + 页码）</text>
    </view>
  </view>
</template>

<style lang="scss" scoped>
.qa-page {
  min-height: 100vh;
  background: #f3f4f6;
  padding: 24rpx 32rpx 60rpx;
}

/* 输入区 */
.ask-bar {
  display: flex;
  gap: 16rpx;
  margin-bottom: 20rpx;
}
.ask-input {
  flex: 1;
  height: 84rpx;
  padding: 0 28rpx;
  border-radius: 42rpx;
  background: #ffffff;
  font-size: 28rpx;
}
.ph { color: #9ca3af; }
.ask-btn {
  width: 140rpx;
  height: 84rpx;
  line-height: 84rpx;
  text-align: center;
  border-radius: 42rpx;
  background: linear-gradient(135deg, #8b5cf6, #6366f1);
  color: #ffffff;
  font-size: 30rpx;
  font-weight: 600;
}
.ask-btn.disabled { opacity: 0.6; }

/* 快捷提问 */
.quick-wrap { margin-bottom: 24rpx; }
.quick-label { font-size: 24rpx; color: #9ca3af; }
.quick-tags { display: flex; flex-wrap: wrap; gap: 16rpx; margin-top: 12rpx; }
.quick-tag {
  padding: 12rpx 24rpx;
  border-radius: 30rpx;
  background: #ede9fe;
}
.quick-text { font-size: 24rpx; color: #6d28d9; }

/* 回答 */
.answer-loading { display: flex; flex-direction: column; align-items: center; padding-top: 120rpx; }
.loading-icon { font-size: 72rpx; }
.loading-text { margin-top: 20rpx; font-size: 26rpx; color: #9ca3af; }

.answer-card {
  padding: 28rpx;
  border-radius: 20rpx;
  background: #ffffff;
}
.answer-q { display: flex; gap: 12rpx; }
.q-mark {
  width: 40rpx;
  height: 40rpx;
  border-radius: 50%;
  background: #8b5cf6;
  color: #ffffff;
  font-size: 22rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.q-text { font-size: 28rpx; font-weight: 600; color: #1f2937; line-height: 1.5; }
.answer-a { display: flex; gap: 12rpx; margin-top: 20rpx; }
.a-mark {
  width: 40rpx;
  height: 40rpx;
  border-radius: 50%;
  background: #10b981;
  color: #ffffff;
  font-size: 22rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.a-text { flex: 1; font-size: 26rpx; color: #4b5563; line-height: 1.75; white-space: pre-wrap; }

/* 流式光标 */
.cursor {
  display: inline-block;
  margin-left: 2rpx;
  color: #8b5cf6;
  animation: blink 1s steps(1) infinite;
}
@keyframes blink {
  0%, 50% { opacity: 1; }
  50.01%, 100% { opacity: 0; }
}

.empty { display: flex; flex-direction: column; align-items: center; padding-top: 120rpx; }
.empty-icon { font-size: 70rpx; }
.empty-text { margin-top: 16rpx; font-size: 26rpx; color: #9ca3af; }

.hint {
  margin-top: 24rpx;
  padding: 28rpx;
  border-radius: 20rpx;
  background: #ffffff;
}
.hint-title { display: block; font-size: 28rpx; font-weight: 600; color: #1f2937; margin-bottom: 12rpx; }
.hint-line { display: block; font-size: 24rpx; color: #6b7280; line-height: 1.9; }
</style>
