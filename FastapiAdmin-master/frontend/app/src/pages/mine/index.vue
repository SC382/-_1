<!-- 个人中心：医生个人信息 / 修改密码 / 退出登录 -->
<script setup lang="ts">
import { computed, ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { useUserStore } from '@/store/userStore'
import { Storage } from '@/utils/storage'
import DoctorAPI from '@/api/module_cpx/doctor'
import type { CpxUserInfo } from '@/api/module_cpx/auth'

definePage({
  name: 'mine',
  layout: 'tabbar',
  style: { navigationBarTitleText: '我的' },
})

const CPX_USERINFO_KEY = 'cpx_userinfo'
const userStore = useUserStore()

const userInfo = ref<CpxUserInfo | null>(null)

const roleLabel = (code?: string) => {
  if (code === 'admin') return '管理员'
  if (code === 'auditor') return '审核员'
  if (code === 'doctor') return '医生'
  return code || '-'
}

onShow(() => {
  userInfo.value = Storage.get<CpxUserInfo | null>(CPX_USERINFO_KEY, null)
})

// ── 修改密码 ──────────────────────────────────────────
const pwdVisible = ref(false)
const pwdForm = ref({ old_password: '', new_password: '', confirm: '' })
const pwdSubmitting = ref(false)

function openPwd() {
  pwdForm.value = { old_password: '', new_password: '', confirm: '' }
  pwdVisible.value = true
}

async function submitPwd() {
  const { old_password, new_password, confirm } = pwdForm.value
  if (!old_password) {
    uni.showToast({ title: '请输入原密码', icon: 'none' })
    return
  }
  if (new_password.length < 6) {
    uni.showToast({ title: '新密码至少 6 位', icon: 'none' })
    return
  }
  if (new_password !== confirm) {
    uni.showToast({ title: '两次输入的新密码不一致', icon: 'none' })
    return
  }
  pwdSubmitting.value = true
  try {
    await DoctorAPI.changePassword({ old_password, new_password })
    pwdVisible.value = false
    uni.showToast({ title: '密码修改成功', icon: 'success' })
  }
  catch {
    // http 层 toast
  }
  finally {
    pwdSubmitting.value = false
  }
}

// ── 退出登录 ──────────────────────────────────────────
function handleLogout() {
  uni.showModal({
    title: '提示',
    content: '确定要退出登录吗？',
    confirmText: '退出',
    success: (res) => {
      if (res.confirm) {
        Storage.remove(CPX_USERINFO_KEY)
        userStore.clearAll()
        uni.reLaunch({ url: '/pages/login/index' })
      }
    },
  })
}
</script>

<template>
  <view class="mine-page">
    <!-- 用户卡片 -->
    <view class="user-card">
      <view class="avatar">
        <text>{{ (userInfo?.real_name || userInfo?.username || '医')[0] }}</text>
      </view>
      <text class="user-name">{{ userInfo?.real_name || userInfo?.username || '医生' }}</text>
      <text class="user-role">{{ roleLabel(userInfo?.role_code) }}</text>
      <text class="user-hospital">{{ userInfo?.hospital_name || '未关联医院' }}</text>
    </view>

    <!-- 信息列表 -->
    <view class="menu-card">
      <view class="menu-item">
        <text class="menu-label">登录账号</text>
        <text class="menu-value">{{ userInfo?.username || '-' }}</text>
      </view>
      <view class="menu-item">
        <text class="menu-label">所属医院</text>
        <text class="menu-value">{{ userInfo?.hospital_name || '-' }}</text>
      </view>
      <view class="menu-item">
        <text class="menu-label">用户角色</text>
        <text class="menu-value">{{ roleLabel(userInfo?.role_code) }}</text>
      </view>
    </view>

    <!-- 操作 -->
    <view class="menu-card">
      <view class="menu-action" @click="openPwd">
        <text class="action-icon">🔑</text>
        <text class="action-label">修改密码</text>
        <text class="action-arrow">›</text>
      </view>
      <view class="menu-action" @click="handleLogout">
        <text class="action-icon">🚪</text>
        <text class="action-label logout-text">退出登录</text>
        <text class="action-arrow">›</text>
      </view>
    </view>

    <text class="version">智慧胸痛管理 · 医生端 v1.0</text>

    <!-- 修改密码弹窗 -->
    <view v-if="pwdVisible" class="modal-mask" @click.self="pwdVisible = false">
      <view class="modal">
        <text class="modal-title">修改密码</text>
        <view class="modal-field">
          <text class="modal-label">原密码</text>
          <input v-model="pwdForm.old_password" class="modal-input" type="password" placeholder="请输入原密码" placeholder-class="ph" />
        </view>
        <view class="modal-field">
          <text class="modal-label">新密码</text>
          <input v-model="pwdForm.new_password" class="modal-input" type="password" placeholder="至少 6 位" placeholder-class="ph" />
        </view>
        <view class="modal-field">
          <text class="modal-label">确认新密码</text>
          <input v-model="pwdForm.confirm" class="modal-input" type="password" placeholder="再次输入新密码" placeholder-class="ph" />
        </view>
        <view class="modal-ops">
          <button class="modal-btn cancel" @click="pwdVisible = false">取消</button>
          <button class="modal-btn ok" :disabled="pwdSubmitting" @click="submitPwd">
            {{ pwdSubmitting ? '提交中...' : '确认修改' }}
          </button>
        </view>
      </view>
    </view>
  </view>
</template>

<style lang="scss" scoped>
.mine-page {
  min-height: 100vh;
  background: #f3f4f6;
  padding-bottom: 40rpx;
}

.user-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 60rpx 32rpx 50rpx;
  background: linear-gradient(135deg, #0ea5e9 0%, #2563eb 55%, #059669 100%);
}
.avatar {
  width: 140rpx;
  height: 140rpx;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.92);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 60rpx;
  font-weight: 700;
  color: #2563eb;
}
.user-name {
  margin-top: 20rpx;
  font-size: 40rpx;
  font-weight: 700;
  color: #ffffff;
}
.user-role {
  margin-top: 10rpx;
  padding: 6rpx 24rpx;
  border-radius: 24rpx;
  background: rgba(255, 255, 255, 0.25);
  font-size: 24rpx;
  color: #ffffff;
}
.user-hospital {
  margin-top: 12rpx;
  font-size: 24rpx;
  color: rgba(255, 255, 255, 0.85);
}

.menu-card {
  margin: 24rpx 32rpx 0;
  padding: 8rpx 32rpx;
  border-radius: 24rpx;
  background: #ffffff;
}
.menu-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 28rpx 0;
  border-bottom: 2rpx solid #f3f4f6;
}
.menu-item:last-child {
  border-bottom: none;
}
.menu-label {
  font-size: 28rpx;
  color: #6b7280;
}
.menu-value {
  font-size: 28rpx;
  color: #1f2937;
}

.menu-action {
  display: flex;
  align-items: center;
  padding: 30rpx 0;
  border-bottom: 2rpx solid #f3f4f6;
}
.menu-action:last-child {
  border-bottom: none;
}
.action-icon {
  margin-right: 20rpx;
  font-size: 32rpx;
}
.action-label {
  flex: 1;
  font-size: 28rpx;
  color: #1f2937;
}
.logout-text {
  color: #ef4444;
}
.action-arrow {
  font-size: 32rpx;
  color: #c0c4cc;
}

.version {
  display: block;
  margin-top: 48rpx;
  text-align: center;
  font-size: 22rpx;
  color: #c0c4cc;
}

/* 弹窗 */
.modal-mask {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 999;
}
.modal {
  width: 84%;
  max-width: 560rpx;
  padding: 40rpx 36rpx;
  border-radius: 28rpx;
  background: #ffffff;
}
.modal-title {
  display: block;
  text-align: center;
  font-size: 34rpx;
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 32rpx;
}
.modal-field {
  margin-bottom: 24rpx;
}
.modal-label {
  display: block;
  font-size: 26rpx;
  color: #4b5563;
  margin-bottom: 10rpx;
}
.modal-input {
  height: 84rpx;
  padding: 0 24rpx;
  border-radius: 16rpx;
  background: #f3f4f6;
  font-size: 28rpx;
}
.ph {
  color: #9ca3af;
}
.modal-ops {
  display: flex;
  gap: 20rpx;
  margin-top: 36rpx;
}
.modal-btn {
  flex: 1;
  height: 84rpx;
  line-height: 84rpx;
  border-radius: 16rpx;
  font-size: 28rpx;
}
.modal-btn::after {
  border: none;
}
.cancel {
  background: #f3f4f6;
  color: #4b5563;
}
.ok {
  background: #2563eb;
  color: #ffffff;
}
</style>
