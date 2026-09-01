<template>
  <div class="fa-search-item">
    <label v-if="label" class="fa-search-item__label">{{ label }}</label>
    <div class="fa-search-item__control">
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  label?: string;
}>();
</script>
