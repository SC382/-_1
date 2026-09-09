<!-- 系统首页：数据驾驶舱（医疗质感版：白卡+柔和阴影+图标圆底，克制状态色，数字主角）
     保留：真实接口 / 数字滚动 / 骨架屏 / ResizeObserver -->
<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { ElMessage } from "element-plus";
import {
  Odometer,
  OfficeBuilding,
  User,
  Document,
  CircleCheck,
  TrendCharts,
  PieChart,
  Histogram,
  Refresh,
  FirstAidKit,
} from "@element-plus/icons-vue";
import CpxStatsAPI, { type DashboardStats, type QcMetric } from "@/api/cpx/stats";
import { echarts } from "@/plugins/echarts";
import type { EChartsOption } from "@/plugins/echarts";

defineOptions({ name: "CpxDashboard" });

// ── 医疗克制色板 ──
const C = {
  blue: "#2563EB",
  green: "#059669",
  amber: "#D97706",
  red: "#DC2626",
  indigo: "#4F46E5",
  ink: "#111827",
  gray: "#6B7280",
  line: "#E5E7EB",
};

const loading = ref(false);
const stats = ref<DashboardStats | null>(null);
const updatedAt = ref("");

const trendRef = ref<HTMLDivElement>();
const auditChartRef = ref<HTMLDivElement>();
const rankChartRef = ref<HTMLDivElement>();
const trendMode = ref<"day" | "month">("day");

let trendChart: ReturnType<typeof echarts.init> | null = null;
let auditChart: ReturnType<typeof echarts.init> | null = null;
let rankChart: ReturnType<typeof echarts.init> | null = null;
let resizeObserver: ResizeObserver | null = null;

async function loadData() {
  loading.value = true;
  try {
    const res = await CpxStatsAPI.dashboard();
    stats.value = res.data.data;
    updatedAt.value = new Date().toLocaleTimeString("zh-CN", { hour12: false });
    await nextTick();
    renderCharts();
  } catch {
    ElMessage.error("驾驶舱数据加载失败");
  } finally {
    loading.value = false;
  }
}

function useCountUp(targetRef: Ref<number>, duration = 800) {
  const display = ref(0);
  let raf = 0;
  const run = () => {
    cancelAnimationFrame(raf);
    const to = Number(targetRef.value) || 0;
    const from = display.value;
    if (to === from) return;
    const t0 = performance.now();
    const tick = (t: number) => {
      const p = Math.min(1, (t - t0) / duration);
      const eased = 1 - Math.pow(1 - p, 3);
      display.value = Math.round(from + (to - from) * eased);
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
  };
  watch(targetRef, run, { immediate: true });
  return display;
}

const s = computed(() => stats.value);
const counterMap = {
  医院总数: useCountUp(computed(() => s.value?.hospital_stats.total ?? 0)),
  正常运行: useCountUp(computed(() => s.value?.hospital_stats.active ?? 0)),
  禁用医院: useCountUp(computed(() => s.value?.hospital_stats.disabled ?? 0)),
  医生数量: useCountUp(computed(() => s.value?.user_stats.doctor ?? 0)),
  审核员数量: useCountUp(computed(() => s.value?.user_stats.auditor ?? 0)),
  病例总数: useCountUp(computed(() => s.value?.case_stats.total ?? 0)),
  今日新增: useCountUp(computed(() => s.value?.case_stats.today ?? 0)),
  待审核: useCountUp(computed(() => s.value?.case_stats.pending ?? 0)),
  已完成: useCountUp(computed(() => s.value?.case_stats.completed ?? 0)),
  审核总数: useCountUp(computed(() => s.value?.audit_stats.total ?? 0)),
  通过数量: useCountUp(computed(() => s.value?.audit_stats.pass ?? 0)),
  驳回数量: useCountUp(computed(() => s.value?.audit_stats.reject ?? 0)),
};

// ── 指标卡（白卡 + 图标圆底，无渐变头）──
const cards = computed(() => [
  {
    title: "医院统计",
    icon: OfficeBuilding,
    bg: "#EFF6FF",
    color: C.blue,
    items: [
      { label: "医院总数", color: C.blue },
      { label: "正常运行", color: C.green },
      { label: "禁用医院", color: C.red },
    ],
  },
  {
    title: "用户统计",
    icon: User,
    bg: "#EEF2FF",
    color: C.indigo,
    items: [
      { label: "医生数量", color: C.indigo },
      { label: "审核员数量", color: C.blue },
    ],
  },
  {
    title: "病例统计",
    icon: Document,
    bg: "#ECFDF5",
    color: C.green,
    items: [
      { label: "病例总数", color: C.ink },
      { label: "今日新增", color: C.blue },
      { label: "待审核", color: C.amber },
      { label: "已完成", color: C.green },
    ],
  },
  {
    title: "审核统计",
    icon: CircleCheck,
    bg: "#FEF2F2",
    color: C.red,
    items: [
      { label: "审核总数", color: C.ink },
      { label: "通过数量", color: C.green },
      { label: "驳回数量", color: C.amber },
    ],
  },
]);

// ── 运行概览（柔和色块行）──
const overviewRows = computed(() => [
  {
    icon: OfficeBuilding,
    bg: "#EFF6FF",
    color: C.blue,
    title: "医院运行",
    desc: `${s.value?.hospital_stats.active ?? 0} 家正常运行 / ${s.value?.hospital_stats.total ?? 0} 家总计`,
  },
  {
    icon: FirstAidKit,
    bg: "#ECFDF5",
    color: C.green,
    title: "医生团队",
    desc: `${s.value?.user_stats.doctor ?? 0} 名医生 · ${s.value?.user_stats.auditor ?? 0} 名审核员`,
  },
  {
    icon: Document,
    bg: "#FFFBEB",
    color: C.amber,
    title: "审核进度",
    desc: `${s.value?.case_stats.pending ?? 0} 份待审核 · ${s.value?.case_stats.completed ?? 0} 份已完成`,
  },
  {
    icon: CircleCheck,
    bg: "#FEF2F2",
    color: C.red,
    title: "今日动态",
    desc: `今日新增 ${s.value?.case_stats.today ?? 0} 份病例`,
  },
]);

// ── 质控指标 ──
const qc = computed(() => stats.value?.qc_stats ?? null);
function qcMainText(m: QcMetric) {
  if (m.rate != null) return `${m.rate}%`;
  if (m.median_min != null) return `${m.median_min}`;
  return "--";
}
function qcSubText(m: QcMetric) {
  if (m.rate != null) return `达标 ${m.pass}/${m.eligible} · ≤${m.limit} 分钟`;
  return `中位时长 · 无阈值`;
}
function qcColor(m: QcMetric) {
  const r = m.rate;
  if (r == null) return C.blue;
  if (r >= 90) return C.green;
  if (r >= 70) return C.amber;
  return C.red;
}

// ── 图表 ──
const tooltipStyle = { backgroundColor: "#ffffff", borderColor: C.line, textStyle: { color: C.ink, fontSize: 12 } };
const axisStyle = { color: C.gray, fontSize: 12 };

function trendOption(): EChartsOption {
  const isDay = trendMode.value === "day";
  const xAxis = isDay ? s.value?.case_trend.xAxis ?? [] : s.value?.case_trend_monthly.xAxis ?? [];
  const data = isDay ? s.value?.case_trend.data ?? [] : s.value?.case_trend_monthly.data ?? [];
  return {
    tooltip: { trigger: "axis", ...tooltipStyle },
    grid: { left: 44, right: 24, top: 24, bottom: 28 },
    xAxis: {
      type: "category",
      data: xAxis,
      boundaryGap: false,
      axisLine: { lineStyle: { color: C.line } },
      axisTick: { show: false },
      axisLabel: axisStyle,
    },
    yAxis: {
      type: "value",
      minInterval: 1,
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { lineStyle: { color: "#F0F2F5" } },
      axisLabel: axisStyle,
    },
    series: [
      {
        name: isDay ? "日病例数" : "月病例数",
        type: "line",
        smooth: true,
        symbolSize: 6,
        data,
        lineStyle: { width: 2.5, color: C.blue },
        itemStyle: { color: C.blue },
        emphasis: { focus: "series" },
        areaStyle: {
          color: {
            type: "linear",
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: "rgba(37,99,235,0.14)" },
              { offset: 1, color: "rgba(37,99,235,0.01)" },
            ],
          },
        },
      },
    ],
  };
}

function auditOption(): EChartsOption {
  const pass = s.value?.audit_stats.pass ?? 0;
  const reject = s.value?.audit_stats.reject ?? 0;
  const total = s.value?.audit_stats.total ?? 0;
  const passRate = s.value?.audit_stats.pass_rate ?? 0;
  return {
    tooltip: {
      trigger: "item",
      ...tooltipStyle,
      formatter: (p: unknown) => {
        const d = p as { name: string; value: number; percent: number };
        return `${d.name}：${d.value} 条（${d.percent}%）`;
      },
    },
    legend: { bottom: 0, textStyle: { color: C.gray, fontSize: 12 }, itemWidth: 12, itemHeight: 12 },
    title: {
      text: `${passRate}%`,
      subtext: total ? "审核通过率" : "暂无审核数据",
      left: "center",
      top: "36%",
      textStyle: { fontSize: 30, fontWeight: 600, color: C.blue },
      subtextStyle: { fontSize: 12, color: C.gray },
    },
    series: [
      {
        name: "审核结果",
        type: "pie",
        radius: ["54%", "74%"],
        center: ["50%", "45%"],
        avoidLabelOverlap: false,
        label: { show: false },
        emphasis: { label: { show: false }, scaleSize: 4 },
        data: [
          { name: "通过", value: pass, itemStyle: { color: C.green } },
          { name: "驳回", value: reject, itemStyle: { color: C.red } },
        ],
      },
    ],
  };
}

function rankOption(): EChartsOption {
  const list = s.value?.hospital_ranking ?? [];
  const names = list.map((i) => i.name).reverse();
  const values = list.map((i) => i.value).reverse();
  return {
    tooltip: { trigger: "axis", axisPointer: { type: "shadow" }, ...tooltipStyle },
    grid: { left: 10, right: 44, top: 8, bottom: 8, containLabel: true },
    xAxis: { type: "value", minInterval: 1, axisLabel: axisStyle, splitLine: { lineStyle: { color: "#F0F2F5" } } },
    yAxis: {
      type: "category",
      data: names,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { ...axisStyle, color: "#374151" },
    },
    series: [
      {
        name: "病例数",
        type: "bar",
        data: values,
        barWidth: 12,
        itemStyle: { borderRadius: [0, 6, 6, 0], color: C.blue },
        emphasis: { focus: "series" },
        label: { show: true, position: "right", color: C.gray, fontSize: 12 },
      },
    ],
  };
}

function renderCharts() {
  if (!trendChart && trendRef.value) trendChart = echarts.init(trendRef.value);
  trendChart?.setOption(trendOption(), true);
  if (!auditChart && auditChartRef.value) auditChart = echarts.init(auditChartRef.value);
  auditChart?.setOption(auditOption(), true);
  if (!rankChart && rankChartRef.value) rankChart = echarts.init(rankChartRef.value);
  rankChart?.setOption(rankOption(), true);
}

function onTrendModeChange() {
  renderCharts();
}

function disposeCharts() {
  trendChart?.dispose();
  auditChart?.dispose();
  rankChart?.dispose();
  trendChart = auditChart = rankChart = null;
}

onMounted(() => {
  loadData();
  resizeObserver = new ResizeObserver(() => {
    trendChart?.resize();
    auditChart?.resize();
    rankChart?.resize();
  });
  if (trendRef.value) resizeObserver.observe(trendRef.value);
  if (auditChartRef.value) resizeObserver.observe(auditChartRef.value);
  if (rankChartRef.value) resizeObserver.observe(rankChartRef.value);
});

onBeforeUnmount(() => {
  resizeObserver?.disconnect();
  disposeCharts();
});
</script>

<template>
  <div class="cpx-page dashboard px-4 py-5 md:px-6">
    <!-- 页头：浅蓝渐变 Hero（紧凑） -->
    <header class="hero relative mb-5 overflow-hidden rounded-2xl px-4 py-3 ring-1 ring-blue-100/60">
      <div class="relative z-10 flex flex-wrap items-center justify-between gap-2">
        <div class="flex items-center gap-2.5">
          <div class="flex h-9 w-9 items-center justify-center rounded-lg bg-white shadow-sm ring-1 ring-blue-100">
            <ElIcon :size="18" color="#2563EB"><Odometer /></ElIcon>
          </div>
          <div>
            <h2 class="text-base font-semibold tracking-tight text-gray-900">数据驾驶舱</h2>
            <p class="mt-0.5 text-xs text-gray-500">
              胸痛中心运行概览 · 更新于 <span class="tabular-nums text-gray-600">{{ updatedAt || "--" }}</span>
            </p>
          </div>
        </div>
        <ElButton size="small" round plain :loading="loading" @click="loadData">
          <ElIcon :size="14" class="mr-1"><Refresh /></ElIcon>{{ loading ? "刷新中" : "刷新" }}
        </ElButton>
      </div>
      <!-- 装饰图标（缩小） -->
      <ElIcon :size="80" color="rgba(255,255,255,0.5)" class="pointer-events-none absolute -right-2 -top-4"><FirstAidKit /></ElIcon>
      <ElIcon :size="36" color="rgba(147,197,253,0.4)" class="pointer-events-none absolute -bottom-3 right-24"><FirstAidKit /></ElIcon>
      <ElIcon :size="16" color="rgba(147,197,253,0.5)" class="pointer-events-none absolute right-40 top-2"><TrendCharts /></ElIcon>
    </header>

    <!-- 骨架屏 -->
    <template v-if="!stats">
      <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <div v-for="i in 4" :key="i" class="rounded-2xl bg-[#F4F8FC] p-5 shadow-sm ring-1 ring-black/5">
          <ElSkeleton :rows="4" animated />
        </div>
      </div>
      <div class="mt-4 grid gap-4 lg:grid-cols-3">
        <div class="rounded-2xl bg-[#F4F8FC] p-5 shadow-sm ring-1 ring-black/5 lg:col-span-2">
          <ElSkeleton :rows="6" animated />
        </div>
        <div class="rounded-2xl bg-[#F4F8FC] p-5 shadow-sm ring-1 ring-black/5">
          <ElSkeleton :rows="6" animated />
        </div>
      </div>
    </template>

    <template v-else>
      <!-- 指标卡：白卡 + 图标圆底 -->
      <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <div
          v-for="card in cards"
          :key="card.title"
          class="relative overflow-hidden rounded-2xl p-5 shadow-sm ring-1 ring-black/5 transition-shadow duration-200 hover:shadow-md"
          :style="{ backgroundColor: card.bg }"
        >
          <span
            class="pointer-events-none absolute -right-3 -top-3 opacity-[0.08]"
            :style="{ color: card.color, fontSize: '72px' }"
          >
            <ElIcon :size="72"><component :is="card.icon" /></ElIcon>
          </span>
          <div class="relative flex items-center gap-2.5">
            <div class="flex h-9 w-9 items-center justify-center rounded-lg bg-white/90 ring-1 ring-black/5">
              <ElIcon :size="18" :style="{ color: card.color }"><component :is="card.icon" /></ElIcon>
            </div>
            <span class="text-sm font-medium text-gray-600">{{ card.title }}</span>
          </div>
          <div class="relative mt-5 grid gap-x-3 gap-y-5" :class="card.items.length > 3 ? 'grid-cols-2' : card.items.length > 2 ? 'grid-cols-3' : 'grid-cols-2'">
            <div v-for="item in card.items" :key="item.label">
              <div class="text-2xl font-semibold leading-none tabular-nums" :style="{ color: item.color }">
                {{ counterMap[item.label]?.value ?? 0 }}
              </div>
              <div class="mt-1.5 text-xs text-gray-400">{{ item.label }}</div>
            </div>
          </div>
          <div v-if="card.title === '审核统计'" class="mt-4 space-y-2 border-t border-gray-100 pt-3.5">
            <div class="flex items-center justify-between text-xs">
              <span class="text-gray-400">通过率</span>
              <span class="font-medium tabular-nums text-emerald-600">{{ s?.audit_stats.pass_rate ?? 0 }}%</span>
            </div>
            <ElProgress :percentage="s?.audit_stats.pass_rate ?? 0" :stroke-width="6" color="#059669" :show-text="false" />
            <div class="flex items-center justify-between text-xs pt-1">
              <span class="text-gray-400">驳回率</span>
              <span class="font-medium tabular-nums text-red-500">{{ s?.audit_stats.reject_rate ?? 0 }}%</span>
            </div>
            <ElProgress :percentage="s?.audit_stats.reject_rate ?? 0" :stroke-width="6" color="#DC2626" :show-text="false" />
          </div>
        </div>
      </div>

      <!-- 胸痛质控指标 -->
      <div class="mt-4 rounded-2xl bg-[#F4F8FC] p-5 shadow-sm ring-1 ring-black/5">
        <div class="mb-3 flex flex-wrap items-center justify-between gap-2">
          <h3 class="flex items-center gap-1.5 text-sm font-medium text-gray-700">
            <ElIcon :size="14" color="#DC2626"><FirstAidKit /></ElIcon>胸痛质控指标
          </h3>
          <span class="text-xs text-gray-400">
            纳入已上报 {{ qc?.case_total ?? 0 }} 例
            <template v-if="(qc?.time_issue_cases ?? 0) > 0">
              · <span class="text-red-500">{{ qc?.time_issue_cases }} 例时间倒挂</span>
            </template>
          </span>
        </div>
        <div v-if="!qc?.metrics?.length" class="py-6 text-center text-sm text-gray-400">暂无质控数据</div>
        <div v-else class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
          <div
            v-for="m in qc.metrics"
            :key="m.key"
            class="rounded-xl bg-white p-4 ring-1 ring-black/5 transition-shadow duration-200 hover:shadow-md"
          >
            <div class="flex items-center justify-between gap-1.5">
              <span class="truncate text-xs text-gray-500" :title="`${m.name}：${m.desc}`">{{ m.name }}</span>
              <span class="shrink-0 rounded bg-blue-50 px-1.5 py-0.5 text-[10px] font-medium text-blue-600">{{ m.key }}</span>
            </div>
            <div class="mt-2.5 flex items-baseline gap-1">
              <span class="text-2xl font-semibold leading-none tabular-nums" :style="{ color: qcColor(m) }">
                {{ qcMainText(m) }}
              </span>
              <span v-if="m.rate != null" class="text-xs text-gray-400">达标率</span>
              <span v-else class="text-xs text-gray-400">分钟（中位）</span>
            </div>
            <div class="mt-1.5 truncate text-xs text-gray-400" :title="qcSubText(m)">{{ qcSubText(m) }}</div>
            <ElProgress
              v-if="m.rate != null"
              class="mt-2.5"
              :percentage="m.rate ?? 0"
              :stroke-width="5"
              :color="qcColor(m)"
              :show-text="false"
            />
          </div>
        </div>
      </div>

      <!-- 趋势 + 审核环图 -->
      <div class="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div class="rounded-2xl bg-[#F4F8FC] p-5 shadow-sm ring-1 ring-black/5 lg:col-span-2">
          <div class="mb-2 flex flex-wrap items-center justify-between gap-2">
            <h3 class="flex items-center gap-1.5 text-sm font-medium text-gray-700">
              <ElIcon :size="14" color="#2563EB"><TrendCharts /></ElIcon>病例趋势
            </h3>
            <ElRadioGroup v-model="trendMode" size="small" @change="onTrendModeChange">
              <ElRadioButton value="day">日病例数量</ElRadioButton>
              <ElRadioButton value="month">月病例数量</ElRadioButton>
            </ElRadioGroup>
          </div>
          <div v-loading="loading && !!stats" ref="trendRef" class="h-72 w-full" />
        </div>
        <div class="rounded-2xl bg-[#F4F8FC] p-5 shadow-sm ring-1 ring-black/5">
          <h3 class="mb-2 flex items-center gap-1.5 text-sm font-medium text-gray-700">
            <ElIcon :size="14" color="#059669"><PieChart /></ElIcon>审核情况
          </h3>
          <div v-loading="loading && !!stats" ref="auditChartRef" class="h-72 w-full" />
        </div>
      </div>

      <!-- 排行 + 运行概览 -->
      <div class="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div class="rounded-2xl bg-[#F4F8FC] p-5 shadow-sm ring-1 ring-black/5">
          <h3 class="mb-2 flex items-center gap-1.5 text-sm font-medium text-gray-700">
            <ElIcon :size="14" color="#4F46E5"><Histogram /></ElIcon>医院病例排行
          </h3>
          <div v-loading="loading && !!stats" ref="rankChartRef" class="h-64 w-full" />
        </div>
        <div class="rounded-2xl bg-[#F4F8FC] p-5 shadow-sm ring-1 ring-black/5">
          <h3 class="mb-4 flex items-center gap-1.5 text-sm font-medium text-gray-700">
            <ElIcon :size="14" color="#D97706"><Odometer /></ElIcon>运行概览
          </h3>
          <div class="grid gap-3 sm:grid-cols-2">
            <div
              v-for="row in overviewRows"
              :key="row.title"
              class="flex items-center gap-3 rounded-xl p-3.5 transition-transform duration-200 hover:-translate-y-0.5"
              :style="{ backgroundColor: row.bg }"
            >
              <span :style="{ color: row.color, fontSize: '20px' }">
                <ElIcon :size="20"><component :is="row.icon" /></ElIcon>
              </span>
              <div class="min-w-0">
                <div class="text-sm font-medium text-gray-700">{{ row.title }}</div>
                <div class="mt-0.5 truncate text-xs text-gray-500">{{ row.desc }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.dashboard {
  max-width: 1280px;
  margin: 0 auto;
  background: #f5f7fa;
  border-radius: 16px;
}
.hero {
  background: linear-gradient(135deg, #eff6ff 0%, #eef2ff 55%, #f5f3ff 100%);
}
</style>
