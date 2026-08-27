<script lang="ts" setup>
import { useI18n } from 'vue-i18n'

const router = useRouter()

const route = useRoute()

const { t } = useI18n()

const { activeTabbar, getTabbarItemValue, setTabbarItemActive, tabbarList } = useTabbar()

function handleTabbarChange({ value }: { value: string }) {
  setTabbarItemActive(value)
  router.pushTab({ name: value })
}

onMounted(() => {
  // #ifdef APP
  uni.hideTabBar()
  // #endif
  nextTick(() => {
    if (route.name && route.name !== activeTabbar.value.name) {
      setTabbarItemActive(route.name)
    }
  })
})
</script>

<script lang="ts">
export default {
  options: {
    addGlobalClass: true,
    virtualHost: true,
    styleIsolation: 'shared',
  },
}
</script>

<template>
  <slot />
  <wd-gap
    safe-area-bottom
    height="52px"
    custom-class="tabbar-gap"
  />
  <wd-tabbar
    :model-value="activeTabbar.name" bordered safe-area-inset-bottom fixed custom-class="app-tabbar"
    @change="handleTabbarChange"
  >
    <wd-tabbar-item
      v-for="(item, index) in tabbarList" :key="index" :name="item.name"
      :value="getTabbarItemValue(item.name)" :icon="item.icon"
      :text="t(item.titleKey)" :custom-class="index === 1 ? 'tabbar-mid' : ''"
    />
  </wd-tabbar>
</template>

<style lang="scss">
/* 底部导航：图标 + 文字标签；中间 AI Tab 改为蓝色渐变矩形 + 白色 "Ai" 字样 */
.app-tabbar {
  --wot-tabbar-height: 52px;
  --wot-tabbar-item-icon-size: 32px;
  --wot-tabbar-item-font-size: 18px;
  --wot-tabbar-item-color-active: #2563eb;
  --wot-tabbar-item-color-inactive: #9ca3af;
  :deep(.wd-tabbar-item__body-icon) {
    image {
      width: 32px !important;
      height: 32px !important;
      display: block;
    }
  }
  /* 中间 AI Tab：蓝色渐变矩形 + "Ai" 字样（与左右图标同高对齐） */
  :deep(.wd-tabbar-item.tabbar-mid) {
    .wd-tabbar-item__body-icon {
      width: 40px;
      height: 32px;
      border-radius: 9px;
      background: linear-gradient(135deg, #2563eb 0%, #0ea5e9 100%);
      display: flex;
      align-items: center;
      justify-content: center;
      transform: translateY(2px);
      image {
        display: none !important;
      }
    }
    .wd-tabbar-item__body-icon::before {
      content: 'Ai';
      color: #ffffff;
      font-size: 17px;
      font-weight: 700;
      line-height: 1;
      letter-spacing: -0.5px;
    }
    .wd-tabbar-item__text {
      color: #2563eb;
      font-weight: 600;
    }
  }
}
</style>
