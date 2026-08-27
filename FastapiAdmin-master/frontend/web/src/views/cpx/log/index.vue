<!-- 操作日志管理（仅系统管理员）：筛选 + 日志列表 + 只读详情弹窗 -->
<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import HospitalAPI, { type HospitalTable } from "@/api/cpx/hospital";
import LogAPI, { type LogTable, type RoleOption } from "@/api/cpx/log";

defineOptions({ name: "CpxLog" });

const loading = ref(false);
const data = ref<LogTable[]>([]);
const total = ref(0);

const query = reactive({
  page_no: 1,
  page_size: 10,
  user_name: "",
  role_id: undefined as number | undefined,
  hospital_id: undefined as number | undefined,
  module: "",
  dateRange: [] as string[],
});

const MODULE_OPTIONS = ["认证管理", "医院管理", "用户管理", "模板管理", "病例管理", "审核管理"];
const roleOptions = ref<RoleOption[]>([]);
const hospitalOptions = ref<HospitalTable[]>([]);

/** 操作时间快捷选项 */
const quickRange = ref("");
function applyQuickRange() {
  const now = new Date();
  const fmt = (d: Date) => {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    return `${y}-${m}-${day}`;
  };
  if (quickRange.value === "today") {
    query.dateRange = [fmt(now), fmt(now)];
  } else if (quickRange.value === "week") {
    const day = now.getDay() === 0 ? 7 : now.getDay();
    const monday = new Date(now);
    monday.setDate(now.getDate() - day + 1);
    query.dateRange = [fmt(monday), fmt(now)];
  } else if (quickRange.value === "month") {
    const first = new Date(now.getFullYear(), now.getMonth(), 1);
    query.dateRange = [fmt(first), fmt(now)];
  } else {
    query.dateRange = [];
  }
  handleSearch();
}

async function fetchData() {
  loading.value = true;
  try {
    const res = await LogAPI.list({
      page_no: query.page_no,
      page_size: query.page_size,
      user_name: query.user_name || undefined,
      role_id: query.role_id,
      hospital_id: query.hospital_id,
      module: query.module || undefined,
      start_time: query.dateRange?.[0],
      end_time: query.dateRange?.[1],
    });
    data.value = res.data.data.items;
    total.value = res.data.data.total;
  } finally {
    loading.value = false;
  }
}
function handleSearch() {
  query.page_no = 1;
  fetchData();
}
function handleReset() {
  Object.assign(query, { page_no: 1, page_size: 10, user_name: "", role_id: undefined, hospital_id: undefined, module: "", dateRange: [] });
  quickRange.value = "";
  fetchData();
}

// ── 详情弹窗（只读）───────────────────────────────────
const detailVisible = ref(false);
const detailRow = ref<LogTable | null>(null);
function openDetail(row: LogTable) {
  detailRow.value = row;
  detailVisible.value = true;
}

const resultText = (r?: string) => (r === "fail" ? "失败" : "成功");
const resultTagType = (r?: string) => (r === "fail" ? "danger" : "success");

const roleName = computed(() => (id?: number) => roleOptions.value.find((r) => r.id === id)?.role_name ?? "");

onMounted(async () => {
  fetchData();
  const [r1, r2] = await Promise.allSettled([LogAPI.roles(), HospitalAPI.list({ page_no: 1, page_size: 100 })]);
  if (r1.status === "fulfilled") roleOptions.value = r1.value.data.data;
  if (r2.status === "fulfilled") hospitalOptions.value = r2.value.data.data.items;
});
</script>

<template>
  <div class="cpx-page p-4">
    <ElCard shadow="never" class="mb-4">
      <div class="mb-3 flex flex-wrap items-center gap-3">
        <ElInput v-model="query.user_name" placeholder="操作用户姓名" clearable class="w-40" @keyup.enter="handleSearch" />
        <ElSelect v-model="query.role_id" placeholder="用户角色" clearable class="w-32">
          <ElOption v-for="r in roleOptions" :key="r.id" :label="r.role_name" :value="r.id" />
        </ElSelect>
        <ElSelect v-model="query.hospital_id" placeholder="所属医院" clearable filterable class="w-44">
          <ElOption v-for="h in hospitalOptions" :key="h.id" :label="h.hospital_name" :value="h.id" />
        </ElSelect>
        <ElSelect v-model="query.module" placeholder="操作模块" clearable class="w-36">
          <ElOption v-for="m in MODULE_OPTIONS" :key="m" :label="m" :value="m" />
        </ElSelect>
        <ElButton type="primary" @click="handleSearch">查询</ElButton>
        <ElButton @click="handleReset">重置</ElButton>
      </div>
      <div class="flex flex-wrap items-center gap-3 border-t border-gray-100 pt-3">
        <span class="text-sm text-gray-500">操作时间：</span>
        <ElRadioGroup v-model="quickRange" @change="applyQuickRange">
          <ElRadioButton value="today">今日</ElRadioButton>
          <ElRadioButton value="week">本周</ElRadioButton>
          <ElRadioButton value="month">本月</ElRadioButton>
        </ElRadioGroup>
        <ElDatePicker
          v-model="query.dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始时间"
          end-placeholder="结束时间"
          value-format="YYYY-MM-DD"
          class="!w-64"
          @change="handleSearch"
        />
      </div>
    </ElCard>

    <ElCard shadow="never">
      <ElTable v-loading="loading" :data="data" border stripe>
        <ElTableColumn type="index" label="#" width="55" />
        <ElTableColumn prop="real_name" label="操作用户" min-width="100">
          <template #default="{ row }">{{ (row as LogTable).real_name || (row as LogTable).username || "-" }}</template>
        </ElTableColumn>
        <ElTableColumn prop="role_name" label="用户角色" width="100" align="center">
          <template #default="{ row }">
            <ElTag v-if="(row as LogTable).role_name" size="small" type="info" effect="plain">{{ (row as LogTable).role_name }}</ElTag>
            <span v-else>-</span>
          </template>
        </ElTableColumn>
        <ElTableColumn prop="hospital_name" label="所属医院" min-width="130" show-overflow-tooltip>
          <template #default="{ row }">{{ (row as LogTable).hospital_name || "平台总部" }}</template>
        </ElTableColumn>
        <ElTableColumn prop="module" label="操作模块" width="110" align="center" />
        <ElTableColumn prop="operation" label="操作类型" width="110" align="center" />
        <ElTableColumn prop="description" label="操作内容" min-width="220" show-overflow-tooltip />
        <ElTableColumn prop="create_time" label="操作时间" min-width="160" />
        <ElTableColumn prop="ip_address" label="IP地址" width="130" show-overflow-tooltip>
          <template #default="{ row }">{{ (row as LogTable).ip_address || "-" }}</template>
        </ElTableColumn>
        <ElTableColumn prop="result" label="操作结果" width="90" align="center">
          <template #default="{ row }">
            <ElTag :type="resultTagType((row as LogTable).result)" size="small">
              {{ resultText((row as LogTable).result) }}
            </ElTag>
          </template>
        </ElTableColumn>
        <ElTableColumn label="操作" width="110" fixed="right">
          <template #default="{ row }">
            <ElButton link type="primary" size="small" @click="openDetail(row as LogTable)">
              <span class="i-ri:file-search-line mr-1" />日志详情
            </ElButton>
          </template>
        </ElTableColumn>
      </ElTable>

      <div class="mt-4 flex justify-end">
        <ElPagination
          v-model:current-page="query.page_no"
          v-model:page-size="query.page_size"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          @current-change="fetchData"
          @size-change="handleSearch"
        />
      </div>
    </ElCard>

    <!-- 日志详情弹窗（只读） -->
    <ElDialog v-model="detailVisible" title="日志详情" width="560px" :close-on-click-modal="false">
      <ElDescriptions v-if="detailRow" :column="1" border>
        <ElDescriptionsItem label="操作用户">
          {{ detailRow.real_name || detailRow.username || "-" }}
        </ElDescriptionsItem>
        <ElDescriptionsItem label="用户角色">{{ detailRow.role_name || "-" }}</ElDescriptionsItem>
        <ElDescriptionsItem label="所属医院">{{ detailRow.hospital_name || "平台总部" }}</ElDescriptionsItem>
        <ElDescriptionsItem label="操作模块">{{ detailRow.module || "-" }}</ElDescriptionsItem>
        <ElDescriptionsItem label="操作类型">{{ detailRow.operation || "-" }}</ElDescriptionsItem>
        <ElDescriptionsItem label="详细操作描述">
          <div class="whitespace-pre-wrap">{{ detailRow.description || "-" }}</div>
        </ElDescriptionsItem>
        <ElDescriptionsItem label="操作IP地址">{{ detailRow.ip_address || "-" }}</ElDescriptionsItem>
        <ElDescriptionsItem label="操作时间">{{ detailRow.create_time || "-" }}</ElDescriptionsItem>
        <ElDescriptionsItem label="操作结果">
          <ElTag :type="resultTagType(detailRow.result)" size="small">{{ resultText(detailRow.result) }}</ElTag>
        </ElDescriptionsItem>
      </ElDescriptions>
      <template #footer>
        <ElButton type="primary" @click="detailVisible = false">关闭</ElButton>
      </template>
    </ElDialog>
  </div>
</template>
