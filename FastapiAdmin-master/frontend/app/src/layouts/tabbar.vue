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
    height="36px"
    custom-class="tabbar-gap"
  />
  <wd-tabbar
    :model-value="activeTabbar.name" bordered safe-area-inset-bottom fixed custom-class="app-tabbar"
    @change="handleTabbarChange"
  >
    <wd-tabbar-item
      v-for="(item, index) in tabbarList" :key="index" :name="item.name"
      :value="getTabbarItemValue(item.name)" :icon="item.icon"
    />
  </wd-tabbar>
</template>

<style lang="scss">
/* 底部导航：纯线性 outline 图标，无文字标签；中间 AI Tab 使用「鲲仑·平安」绿色笑脸机器人头像 */
.app-tabbar {
  --wot-tabbar-height: 44px;
  --wot-tabbar-item-icon-size: 10px;
  --wot-tabbar-item-color-active: #183fa1;
  --wot-tabbar-item-color-inactive: #9ca3af;
  :deep(.wd-tabbar-item__body) {
    padding-top: 0;
    padding-bottom: 0;
  }
  :deep(.wd-tabbar-item__body-icon) {
    image {
      width: 34px !important;
      height: 34px !important;
      display: block;
    }
  }
  :deep(.wd-tabbar-item__text) {
    display: none !important;
  }
}
</style>
