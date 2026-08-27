<!--
  APP 端登录页（智慧胸痛管理主题，与 Web 管理端登录页视觉一致）
  登录走 cpx 业务登录接口：管理员 / 审核员 / 医生 均可登录
-->
<script lang="ts" setup>
import { reactive, ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { useUserStore } from '@/store/userStore'
import CpxAuthAPI from '@/api/module_cpx/auth'
import { Storage } from '@/utils/storage'

/** 业务用户信息本地存储 key */
const CPX_USERINFO_KEY = 'cpx_userinfo'

definePage({ name: 'login', style: { navigationStyle: 'custom' } })

const userStore = useUserStore()
const loading = ref(false)
const form = reactive({ username: '', password: '' })

/** 登录成功后的落地页（医生端首页） */
const redirect = ref('/pages/index/index')

async function handleSubmit() {
  const username = form.username.trim()
  const password = form.password
  if (!username) {
    uni.showToast({ title: '请输入登录账号', icon: 'none' })
    return
  }
  if (!password) {
    uni.showToast({ title: '请输入登录密码', icon: 'none' })
    return
  }
  loading.value = true
  try {
    const result = await CpxAuthAPI.login(username, password)
    if (result?.access_token) {
      // 业务 token 直接作为访问令牌（无刷新令牌）
      userStore.setAccessToken(result.access_token)
      userStore.setRefreshToken('')
      // 保存业务用户信息（个人中心展示）
      if (result.userinfo) {
        Storage.set(CPX_USERINFO_KEY, result.userinfo)
        // 同步写入 userStore.userInfo：路由守卫 isLoggedIn() 依赖它，
        // 否则登录后点任意 tab（如 AI 助手）都会被鉴权守卫拦回登录页
        userStore.setUserInfo(result.userinfo)
      }
      uni.reLaunch({ url: redirect.value })
    }
  }
  catch {
    // 错误提示由 http 层统一 toast
  }
  finally {
    loading.value = false
  }
}
</script>

<template>
  <view class="cpx-login-root">
    <!-- 医院主题背景：医疗色渐变 -->
    <view class="login-bg" />

    <!-- 心电图波形（横贯底部） -->
    <image class="login-ecg" :src="'/static/login-ecg.svg'" mode="scaleToFill" />

    <!-- 装饰：医院十字 + 心形（散落，半透明） -->
    <view class="deco deco-cross deco-1" />
    <view class="deco deco-heart deco-2">♥</view>
    <view class="deco deco-cross deco-3" />
    <view class="deco deco-heart deco-4">♥</view>

    <!-- 登录卡片 -->
    <view class="login-card">
      <view class="card-header">
        <view class="logo-box">
          <view class="logo-cross logo-cross-v" />
          <view class="logo-cross logo-cross-h" />
        </view>
        <text class="card-title">智慧胸痛管理</text>
        <text class="card-subtitle">胸痛中心数据填报 · 医生端</text>
      </view>

      <view class="card-form">
        <view class="field">
          <text class="field-label">登录账号</text>
          <view class="field-input">
            <wd-input
              v-model="form.username"
              placeholder="请输入登录账号"
              clearable
              prefix-icon="user"
              confirm-type="next"
              custom-style="--input-height: 88rpx; --input-font-size: 30rpx; --input-color: #1f2937; --input-placeholder-color: #9ca3af;"
              @confirm="handleSubmit"
            />
          </view>
        </view>

        <view class="field">
          <text class="field-label">登录密码</text>
          <view class="field-input">
            <wd-input
              v-model="form.password"
              placeholder="请输入登录密码"
              clearable
              show-password
              prefix-icon="lock"
              confirm-type="done"
              custom-style="--input-height: 88rpx; --input-font-size: 30rpx; --input-color: #1f2937; --input-placeholder-color: #9ca3af;"
              @confirm="handleSubmit"
            />
          </view>
        </view>

        <button
          class="login-btn"
          :class="{ 'is-loading': loading }"
          :disabled="loading"
          @click="handleSubmit"
        >
          {{ loading ? '登录中...' : '登 录' }}
        </button>

        <text class="card-footer">管理员 / 审核员请使用 Web 管理端 · 医生请使用本端登录</text>
      </view>
    </view>
  </view>
</template>

<style lang="scss" scoped>
.cpx-login-root {
  position: relative;
  width: 100vw;
  height: 100vh;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}

.login-bg {
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, #0ea5e9 0%, #2563eb 55%, #059669 100%);
}

.login-ecg {
  position: absolute;
  left: 0;
  bottom: 0;
  width: 100%;
  height: 440rpx;
  opacity: 1;
  pointer-events: none;
}

/* 装饰元素 */
.deco {
  position: absolute;
  opacity: 0.15;
  pointer-events: none;
}
.deco-cross {
  width: 96rpx;
  height: 96rpx;
}
.deco-cross::before {
  content: '';
  position: absolute;
  left: 40rpx;
  top: 8rpx;
  width: 16rpx;
  height: 80rpx;
  border-radius: 4rpx;
  background: #ffffff;
}
.deco-cross::after {
  content: '';
  position: absolute;
  left: 8rpx;
  top: 40rpx;
  width: 80rpx;
  height: 16rpx;
  border-radius: 4rpx;
  background: #ffffff;
}
.deco-heart {
  font-size: 64rpx;
  color: #ffffff;
  line-height: 1;
}
.deco-1 { left: 8%; top: 14%; }
.deco-2 { right: 10%; top: 11%; font-size: 56rpx; }
.deco-3 { right: 16%; bottom: 22%; }
.deco-4 { left: 14%; bottom: 28%; font-size: 48rpx; }

/* 登录卡片 */
.login-card {
  position: relative;
  z-index: 10;
  width: 86%;
  max-width: 420px;
  background: #ffffff;
  border-radius: 36rpx;
  padding: 56rpx 48rpx 40rpx;
  box-shadow: 0 24rpx 80rpx rgba(15, 23, 42, 0.28);
}

.card-header {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-bottom: 48rpx;
}

.logo-box {
  position: relative;
  width: 120rpx;
  height: 120rpx;
  border-radius: 28rpx;
  background: linear-gradient(135deg, #2563eb, #38bdf8);
  box-shadow: 0 12rpx 24rpx rgba(37, 99, 235, 0.35);
  margin-bottom: 24rpx;
  display: flex;
  align-items: center;
  justify-content: center;
}
.logo-cross {
  position: absolute;
  background: #ffffff;
  border-radius: 4rpx;
}
.logo-cross-v {
  width: 20rpx;
  height: 68rpx;
}
.logo-cross-h {
  width: 68rpx;
  height: 20rpx;
}

.card-title {
  font-size: 44rpx;
  font-weight: 700;
  color: #1f2937;
}
.card-subtitle {
  margin-top: 10rpx;
  font-size: 24rpx;
  color: #9ca3af;
}

/* 表单 */
.card-form {
  display: flex;
  flex-direction: column;
}

.field {
  margin-bottom: 28rpx;
}
.field-label {
  display: block;
  margin-bottom: 12rpx;
  font-size: 26rpx;
  color: #4b5563;
}
.field-input {
  display: flex;
  align-items: center;
  padding: 0 24rpx;
  border-radius: 16rpx;
  background: #f3f4f6;
  border: 2rpx solid transparent;
}
.field-input:focus-within {
  border-color: #2563eb;
  background: #ffffff;
}
.field-input :deep(.wd-input) {
  flex: 1;
}

.login-btn {
  margin-top: 16rpx;
  height: 96rpx;
  line-height: 96rpx;
  border-radius: 20rpx;
  border: none;
  background: linear-gradient(135deg, #2563eb, #0ea5e9);
  color: #ffffff;
  font-size: 32rpx;
  font-weight: 600;
  letter-spacing: 8rpx;
  box-shadow: 0 12rpx 24rpx rgba(37, 99, 235, 0.3);
}
.login-btn::after {
  border: none;
}
.login-btn.is-loading {
  opacity: 0.7;
}

.card-footer {
  margin-top: 32rpx;
  text-align: center;
  font-size: 22rpx;
  color: #c0c4cc;
}
</style>
