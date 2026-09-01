<!-- 统一搜索输入框：左侧放大镜图标 + 圆角浅灰背景 -->
<template>
  <ElInput class="fa-search-input" :prefix-icon="Search" v-bind="$attrs" />
</template>

<script setup lang="ts">
import { Search } from "@element-plus/icons-vue";

defineOptions({ name: "FaSearchInput" });
</script>

<style lang="scss" scoped>
.fa-search-input {
  :deep(.el-input__wrapper) {
    background-color: #f5f7fa;
    border-radius: 8px;
    box-shadow: 0 0 0 1px transparent inset;
    transition: all 0.2s ease;

    &:hover,
    &:focus-within {
      background-color: #ffffff;
      box-shadow: 0 0 0 1px #d1d5db inset;
    }
  }

  :deep(.el-input__inner) {
    color: #374151;

    &::placeholder {
      color: #9ca3af;
    }
  }

  :deep(.el-input__icon) {
    color: #9ca3af;
  }
}
</style>
