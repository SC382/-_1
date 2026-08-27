<!-- 审核工作台 -->
<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import AuditAPI, { type AuditWorkbench } from "@/api/cpx/audit";

defineOptions({ name: "CpxAuditWorkbench" });

const router = useRouter();
const stats = ref<AuditWorkbench>({ pending_count: 0, today_audit_count: 0, pass_count: 0, reject_count: 0 });

const cards = [
  { key: "pending_count", title: "待审核病例", color: "from-amber-400 to-orange-500", icon: "i-ri:inbox-line" },
  { key: "today_audit_count", title: "今日审核", color: "from-sky-400 to-blue-500", icon: "i-ri:calendar-check-line" },
  { key: "pass_count", title: "已通过", color: "from-emerald-400 to-green-500", icon: "i-ri:checkbox-circle-line" },
  { key: "reject_count", title: "已驳回", color: "from-rose-400 to-red-500", icon: "i-ri:close-circle-line" },
] as const;

onMounted(async () => {
  const res = await AuditAPI.workbench();
  stats.value = res.data.data;
});
</script>

<template>
  <div class="cpx-page p-4">
    <div class="mb-4 flex items-center justify-between">
      <h2 class="text-lg font-bold text-gray-700">审核工作台</h2>
      <ElButton type="primary" @click="router.push('/cpx/audit/pending')">前往待审核</ElButton>
    </div>

    <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <div
        v-for="c in cards"
        :key="c.key"
        class="flex cursor-pointer items-center justify-between rounded-xl bg-gradient-to-br p-5 text-white shadow-lg transition-transform hover:scale-[1.02]"
        :class="c.color"
        @click="router.push(c.key === 'pending_count' ? '/cpx/audit/pending' : '/cpx/audit/history')"
      >
        <div>
          <div class="text-3xl font-bold">{{ stats[c.key] }}</div>
          <div class="mt-1 text-sm opacity-90">{{ c.title }}</div>
        </div>
        <span :class="[c.icon, 'text-4xl opacity-80']" />
      </div>
    </div>

    <ElCard shadow="never" class="mt-4">
      <div class="py-8 text-center text-gray-400">
        <div class="mb-2 text-4xl"><span class="i-ri:file-check-line" /></div>
        <p>请前往「待审核病例」处理新提交的病例</p>
      </div>
    </ElCard>
  </div>
</template>
