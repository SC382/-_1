<!-- 系统首页：胸痛中心数据驾驶舱（渐进优化版：数字滚动 / 骨架屏 / 图表体验） -->
<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { ElMessage } from "element-plus";
import CpxStatsAPI, { type DashboardStats } from "@/api/cpx/stats";
import { echarts } from "@/plugins/echarts";
import type { EChartsOption } from "@/plugins/echarts";

defineOptions({ name: "CpxDashboard" });

const loading = ref(false);
const stats = ref<DashboardStats | null>(null);
const updatedAt = ref("");

// ── 图表容器 ──
const trendRef = ref<HTMLDivElement>();
const auditChartRef = ref<HTMLDivElement>();
const rankChartRef = ref<HTMLDivElement>();
const trendMode = ref<"day" | "month">("day");

let trendChart: ReturnType<typeof echarts.init> | null = null;
let auditChart: ReturnType<typeof echarts.init> | null = null;
let rankChart: ReturnType<typeof echarts.init> | null = null;
let resizeObserver: ResizeObserver | null = null;

// ── 数据加载 ──
async function loadData() {
  loading.value = true;
  try {
    const res = await CpxStatsAPI.dashboard();
    stats.value = res.data.data;
    updatedAt.value = new Date().toLocaleTimeString("zh-CN", { hour12: false });
    await nextTick();
    renderCharts();
  } catch (error) {
    ElMessage.error("驾驶舱数据加载失败");
  } finally {
    loading.value = false;
  }
}

// ── 数字滚动动画（0 → 目标值，ease-out-cubic）──
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
  // watch 必须在 setup 顶层调用，绑定到组件 effect scope；
  // 否则 watcher 会立即清理，target 从 0→N 时无回调，display 永远 0
  watch(targetRef, run, { immediate: true });
  return display;
}

// ── 统计卡片数据（数字滚动）──
const s = computed(() => stats.value);
const cards = computed(() => [
  {
    title: "医院统计",
    icon: "i-ri:hospital-line",
    gradient: "from-sky-400 to-blue-500",
    items: [
      { label: "医院总数", color: "#409EFF" },
      { label: "正常运行", color: "#67C23A" },
      { label: "禁用医院", color: "#F56C6C" },
    ],
  },
  {
    title: "用户统计",
    icon: "i-ri:team-line",
    gradient: "from-indigo-400 to-violet-500",
    items: [
      { label: "医生数量", color: "#6366F1" },
      { label: "审核员数量", color: "#8B5CF6" },
    ],
  },
  {
    title: "病例统计",
    icon: "i-ri:clipboard-line",
    gradient: "from-emerald-400 to-green-500",
    items: [
      { label: "病例总数", color: "#10B981" },
      { label: "今日新增", color: "#F59E0B" },
      { label: "待审核", color: "#F97316" },
      { label: "已完成", color: "#3B82F6" },
    ],
  },
  {
    title: "审核统计",
    icon: "i-ri:file-check-line",
    gradient: "from-rose-400 to-red-500",
    items: [
      { label: "审核总数", color: "#EF4444" },
      { label: "通过数量", color: "#10B981" },
      { label: "驳回数量", color: "#F97316" },
    ],
  },
]);

// ── 顶层为每个指标预创建 counter（watch 必须在 setup 顶层调用）──
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

// ── 图表渲染（tooltip 统一白底黑字 + hover 高亮）──
const axisStyle = { color: "#6b7280", fontSize: 12 };
const tooltipStyle = { backgroundColor: "#ffffff", borderColor: "#e5e7eb", textStyle: { color: "#111827", fontSize: 12 } };

function trendOption(): EChartsOption {
  const isDay = trendMode.value === "day";
  const xAxis = isDay ? s.value?.case_trend.xAxis ?? [] : s.value?.case_trend_monthly.xAxis ?? [];
  const data = isDay ? s.value?.case_trend.data ?? [] : s.value?.case_trend_monthly.data ?? [];
  return {
    tooltip: { trigger: "axis", ...tooltipStyle },
    grid: { left: 40, right: 20, top: 30, bottom: 30 },
    xAxis: {
      type: "category",
      data: xAxis,
      boundaryGap: false,
      axisLine: { lineStyle: { color: "#DCDFE6" } },
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
        lineStyle: { width: 3, color: "#409EFF" },
        itemStyle: { color: "#409EFF" },
        emphasis: { focus: "series" },
        areaStyle: {
          color: {
            type: "linear",
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: "rgba(64,158,255,0.30)" },
              { offset: 1, color: "rgba(64,158,255,0.02)" },
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
    legend: { bottom: 0, textStyle: { color: "#606266", fontSize: 12 } },
    title: {
      text: `${passRate}%`,
      subtext: total ? "审核通过率" : "暂无审核数据",
      left: "center",
      top: "36%",
      textStyle: { fontSize: 24, fontWeight: 700, color: "#409EFF" },
      subtextStyle: { fontSize: 12, color: "#909399" },
    },
    series: [
      {
        name: "审核结果",
        type: "pie",
        radius: ["52%", "72%"],
        center: ["50%", "45%"],
        avoidLabelOverlap: false,
        label: { show: false },
        emphasis: { label: { show: false }, scaleSize: 6 },
        data: [
          { name: "通过", value: pass, itemStyle: { color: "#67C23A" } },
          { name: "驳回", value: reject, itemStyle: { color: "#F56C6C" } },
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
    grid: { left: 10, right: 40, top: 10, bottom: 10, containLabel: true },
    xAxis: { type: "value", minInterval: 1, axisLabel: axisStyle, splitLine: { lineStyle: { color: "#F0F2F5" } } },
    yAxis: {
      type: "category",
      data: names,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { ...axisStyle, color: "#606266" },
    },
    series: [
      {
        name: "病例数",
        type: "bar",
        data: values,
        barWidth: 14,
        itemStyle: {
          borderRadius: [0, 7, 7, 0],
          color: {
            type: "linear",
            x: 0,
            y: 0,
            x2: 1,
            y2: 0,
            colorStops: [
              { offset: 0, color: "#67C23A" },
              { offset: 1, color: "#409EFF" },
            ],
          },
        },
        emphasis: { focus: "series" },
        label: { show: true, position: "right", color: "#606266", fontSize: 12 },
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
  <div class="cpx-page p-4">
    <!-- 页头 -->
    <div class="mb-4 flex flex-wrap items-center justify-between gap-3">
      <div>
        <h2 class="flex items-center gap-2 text-lg font-bold text-gray-700">
          <span class="i-ri:dashboard-3-line text-xl text-blue-500" />
          首页
        </h2>
        <p class="mt-0.5 text-xs text-gray-400">管理员登录后查看整个胸痛中心系统运行情况</p>
      </div>
      <div class="flex items-center gap-2 text-xs text-gray-400">
        <span>更新于：{{ updatedAt || "--" }}</span>
        <ElButton size="small" type="primary" plain :loading="loading" @click="loadData">
          <span class="i-ri:refresh-line mr-1" />{{ loading ? "刷新中" : "刷新" }}
        </ElButton>
      </div>
    </div>

    <!-- 2.1 ~ 2.4 统计卡片（数字滚动） -->
    <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <!-- 首次加载骨架屏 -->
      <template v-if="!stats">
        <div v-for="i in 4" :key="i" class="overflow-hidden rounded-xl bg-white shadow-sm ring-1 ring-black/5">
          <ElSkeleton :rows="3" animated class="p-4" />
        </div>
      </template>

      <template v-else>
        <div
          v-for="card in cards"
          :key="card.title"
          class="card-hover overflow-hidden rounded-xl bg-white shadow-sm ring-1 ring-black/5 transition-shadow hover:shadow-md"
        >
          <div class="flex items-center gap-2 px-4 py-3" :class="`bg-gradient-to-r ${card.gradient}`">
            <span :class="[card.icon, 'text-lg text-white']" />
            <span class="text-sm font-semibold text-white">{{ card.title }}</span>
          </div>
          <div class="grid gap-2 p-4" :class="card.items.length > 2 ? 'grid-cols-3' : 'grid-cols-2'">
            <div v-for="item in card.items" :key="item.label" class="rounded-lg bg-gray-50 px-2 py-3 text-center transition-colors hover:bg-gray-100">
              <div class="text-xl font-bold leading-none tabular-nums" :style="{ color: item.color }">
                {{ counterMap[item.label]?.value ?? 0 }}
              </div>
              <div class="mt-1.5 text-xs text-gray-400">{{ item.label }}</div>
            </div>
          </div>
          <!-- 审核统计附加通过率/驳回率 -->
          <div v-if="card.title === '审核统计'" class="px-4 pb-4">
            <div class="mb-1 flex items-center justify-between text-xs text-gray-400">
              <span>通过率</span>
              <span class="font-medium text-emerald-500">{{ s?.audit_stats.pass_rate ?? 0 }}%</span>
            </div>
            <ElProgress :percentage="s?.audit_stats.pass_rate ?? 0" :stroke-width="8" color="#67C23A" :show-text="false" />
            <div class="mb-1 mt-2 flex items-center justify-between text-xs text-gray-400">
              <span>驳回率</span>
              <span class="font-medium text-red-500">{{ s?.audit_stats.reject_rate ?? 0 }}%</span>
            </div>
            <ElProgress :percentage="s?.audit_stats.reject_rate ?? 0" :stroke-width="8" color="#F56C6C" :show-text="false" />
          </div>
        </div>
      </template>
    </div>

    <!-- 2.5 图表区 -->
    <div class="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-3">
      <!-- 病例趋势图 -->
      <ElCard shadow="never" class="lg:col-span-2">
        <template #header>
          <div class="flex flex-wrap items-center justify-between">
            <span class="text-sm font-semibold text-gray-600">病例趋势图</span>
            <ElRadioGroup v-model="trendMode" size="small" @change="onTrendModeChange">
              <ElRadioButton value="day">日病例数量</ElRadioButton>
              <ElRadioButton value="month">月病例数量</ElRadioButton>
            </ElRadioGroup>
          </div>
        </template>
        <div v-loading="loading && !!stats" ref="trendRef" class="h-80 w-full" />
      </ElCard>

      <!-- 审核情况统计 -->
      <ElCard shadow="never">
        <template #header>
          <span class="text-sm font-semibold text-gray-600">审核情况统计</span>
        </template>
        <div v-loading="loading && !!stats" ref="auditChartRef" class="h-80 w-full" />
      </ElCard>
    </div>

    <div class="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
      <!-- 医院病例排行 -->
      <ElCard shadow="never">
        <template #header>
          <span class="text-sm font-semibold text-gray-600">医院病例排行（Top 10）</span>
        </template>
        <div v-loading="loading && !!stats" ref="rankChartRef" class="h-80 w-full" />
      </ElCard>

      <!-- 运行概览说明 -->
      <ElCard shadow="never">
        <template #header>
          <span class="text-sm font-semibold text-gray-600">运行概览</span>
        </template>
        <div class="space-y-4 py-2">
          <div class="flex items-center gap-3 rounded-lg bg-sky-50 p-3 transition-colors hover:bg-sky-100">
            <span class="i-ri:building-2-line text-2xl text-sky-500" />
            <div>
              <div class="text-sm font-medium text-gray-600">医院运行</div>
              <div class="text-xs text-gray-400">
                {{ s?.hospital_stats.active ?? 0 }} 家正常运行 / {{ s?.hospital_stats.total ?? 0 }} 家总计
              </div>
            </div>
          </div>
          <div class="flex items-center gap-3 rounded-lg bg-emerald-50 p-3 transition-colors hover:bg-emerald-100">
            <span class="i-ri:stethoscope-line text-2xl text-emerald-500" />
            <div>
              <div class="text-sm font-medium text-gray-600">医生团队</div>
              <div class="text-xs text-gray-400">{{ s?.user_stats.doctor ?? 0 }} 名医生在线填报病例</div>
            </div>
          </div>
          <div class="flex items-center gap-3 rounded-lg bg-amber-50 p-3 transition-colors hover:bg-amber-100">
            <span class="i-ri:file-shield-line text-2xl text-amber-500" />
            <div>
              <div class="text-sm font-medium text-gray-600">审核进度</div>
              <div class="text-xs text-gray-400">
                {{ s?.case_stats.pending ?? 0 }} 份待审核 / {{ s?.case_stats.completed ?? 0 }} 份已完成
              </div>
            </div>
          </div>
          <div class="flex items-center gap-3 rounded-lg bg-rose-50 p-3 transition-colors hover:bg-rose-100">
            <span class="i-ri:heart-pulse-line text-2xl text-rose-500" />
            <div>
              <div class="text-sm font-medium text-gray-600">今日动态</div>
              <div class="text-xs text-gray-400">今日新增 {{ s?.case_stats.today ?? 0 }} 份病例</div>
            </div>
          </div>
        </div>
      </ElCard>
    </div>
  </div>
</template>
