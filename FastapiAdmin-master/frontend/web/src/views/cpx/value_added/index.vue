<!-- 增值服务管理（仅系统管理员）：Web 端上线/下线服务，App 端首页区块卡片展示 + 跳转 -->
<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from "element-plus";
import ValueAddedAPI, { type ValueAddedForm, type ValueAddedItem, type ValueAddedLinkType, type ValueAddedStatus } from "@/api/cpx/value_added";

defineOptions({ name: "CpxValueAdded" });

const loading = ref(false);
const data = ref<ValueAddedItem[]>([]);
const total = ref(0);
const query = reactive({
  page_no: 1,
  page_size: 10,
  keyword: "",
  status: undefined as string | undefined,
});

const LINK_TYPE_OPTIONS: { label: string; value: ValueAddedLinkType }[] = [
  { label: "内部 H5", value: "h5" },
  { label: "外链", value: "external" },
  { label: "App 内页", value: "internal" },
];
const STATUS_OPTIONS: { label: string; value: ValueAddedStatus; tag: "info" | "success" | "danger" }[] = [
  { label: "草稿", value: "draft", tag: "info" },
  { label: "已上线", value: "online", tag: "success" },
  { label: "已下线", value: "offline", tag: "danger" },
];
const linkTypeLabel = (t?: string) => LINK_TYPE_OPTIONS.find((o) => o.value === t)?.label ?? t ?? "-";
const statusInfo = (s?: string) => STATUS_OPTIONS.find((o) => o.value === s) ?? { label: s ?? "-", value: s ?? "", tag: "info" as const };

async function fetchData() {
  loading.value = true;
  try {
    const res = await ValueAddedAPI.list({ ...query });
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
  query.keyword = "";
  query.status = undefined;
  query.page_no = 1;
  fetchData();
}

// ── 新增 / 编辑 ────────────────────────────────────────
const dialog = reactive({ visible: false, title: "新增服务", mode: "create" as "create" | "edit" });
const saving = ref(false);
const formRef = ref<FormInstance>();
const form = reactive<ValueAddedForm>({
  name: "",
  subtitle: "",
  icon: "",
  cover: "",
  link_type: "h5",
  link_url: "",
  sort_order: 0,
  remark: "",
});
const rules: FormRules = {
  name: [{ required: true, message: "请输入服务名称", trigger: "blur" }],
  link_url: [{ required: true, message: "请输入跳转地址", trigger: "blur" }],
};

function openCreate() {
  dialog.mode = "create";
  dialog.title = "新增服务";
  Object.assign(form, { name: "", subtitle: "", icon: "", cover: "", link_type: "h5", link_url: "", sort_order: 0, remark: "" });
  dialog.visible = true;
}
function openEdit(row: ValueAddedItem) {
  dialog.mode = "edit";
  dialog.title = "编辑服务";
  Object.assign(form, {
    id: row.id,
    name: row.name,
    subtitle: row.subtitle ?? "",
    icon: row.icon ?? "",
    cover: row.cover ?? "",
    link_type: row.link_type ?? "h5",
    link_url: row.link_url ?? "",
    sort_order: row.sort_order ?? 0,
    remark: row.remark ?? "",
  });
  dialog.visible = true;
}

async function save() {
  const valid = await formRef.value?.validate().catch(() => false);
  if (!valid) return;
  saving.value = true;
  try {
    if (dialog.mode === "edit" && form.id) {
      await ValueAddedAPI.update(form.id, { ...form });
      ElMessage.success("修改成功");
    } else {
      await ValueAddedAPI.create({ ...form });
      ElMessage.success("新增成功");
    }
    dialog.visible = false;
    fetchData();
  } catch {
    /* 错误已提示 */
  } finally {
    saving.value = false;
  }
}

// ── 上线 / 下线 / 删除 ─────────────────────────────────
async function handleOnline(row: ValueAddedItem) {
  try {
    await ElMessageBox.confirm(`确认上线「${row.name}」？上线后 App 端首页即可见。`, "提示", {
      type: "warning",
      confirmButtonText: "上线",
      cancelButtonText: "取消",
    });
  } catch {
    return;
  }
  try {
    await ValueAddedAPI.online(row.id);
    ElMessage.success("上线成功");
    fetchData();
  } catch {
    /* 错误已提示 */
  }
}

async function handleOffline(row: ValueAddedItem) {
  try {
    await ElMessageBox.confirm(`确认下线「${row.name}」？下线后 App 端不再展示。`, "提示", {
      type: "warning",
      confirmButtonText: "下线",
      cancelButtonText: "取消",
    });
  } catch {
    return;
  }
  try {
    await ValueAddedAPI.offline(row.id);
    ElMessage.success("已下线");
    fetchData();
  } catch {
    /* 错误已提示 */
  }
}

async function handleDelete(row: ValueAddedItem) {
  try {
    await ElMessageBox.confirm(`确认删除「${row.name}」？不可恢复。`, "删除确认", {
      type: "error",
      confirmButtonText: "删除",
      cancelButtonText: "取消",
    });
  } catch {
    return;
  }
  try {
    await ValueAddedAPI.remove(row.id);
    ElMessage.success("删除成功");
    fetchData();
  } catch {
    /* 错误已提示 */
  }
}

onMounted(fetchData);
</script>

<template>
  <div class="cpx-page p-4">
    <ElCard shadow="never" class="mb-4">
      <div class="flex flex-wrap items-center gap-3">
        <ElInput v-model="query.keyword" placeholder="服务名称" clearable class="w-56" @keyup.enter="handleSearch" />
        <ElSelect v-model="query.status" placeholder="状态" clearable class="w-32">
          <ElOption v-for="o in STATUS_OPTIONS" :key="o.value" :label="o.label" :value="o.value" />
        </ElSelect>
        <ElButton type="primary" @click="handleSearch">查询</ElButton>
        <ElButton @click="handleReset">重置</ElButton>
        <div class="flex-1" />
        <ElButton type="primary" @click="openCreate">
          <span class="i-ri:add-circle-line mr-1" />新增服务
        </ElButton>
      </div>
    </ElCard>

    <ElCard shadow="never">
      <ElTable v-loading="loading" :data="data" border stripe>
        <ElTableColumn type="index" label="#" width="55" />
        <ElTableColumn prop="name" label="服务名称" min-width="200" show-overflow-tooltip />
        <ElTableColumn label="跳转类型" width="100" align="center">
          <template #default="{ row }">
            <ElTag size="small" effect="light">{{ linkTypeLabel((row as ValueAddedItem).link_type) }}</ElTag>
          </template>
        </ElTableColumn>
        <ElTableColumn prop="link_url" label="跳转地址" min-width="220" show-overflow-tooltip>
          <template #default="{ row }">
            {{ (row as ValueAddedItem).link_url || "-" }}
          </template>
        </ElTableColumn>
        <ElTableColumn label="状态" width="100" align="center">
          <template #default="{ row }">
            <ElTag :type="statusInfo((row as ValueAddedItem).status).tag" size="small">
              {{ statusInfo((row as ValueAddedItem).status).label }}
            </ElTag>
          </template>
        </ElTableColumn>
        <ElTableColumn prop="sort_order" label="排序" width="70" align="center" />
        <ElTableColumn prop="create_time" label="创建时间" min-width="160" />
        <ElTableColumn label="操作" width="230" fixed="right">
          <template #default="{ row }">
            <ElButton link type="primary" size="small" @click="openEdit(row as ValueAddedItem)">编辑</ElButton>
            <ElButton v-if="(row as ValueAddedItem).status === 'draft' || (row as ValueAddedItem).status === 'offline'" link type="success" size="small" @click="handleOnline(row as ValueAddedItem)">上线</ElButton>
            <ElButton v-if="(row as ValueAddedItem).status === 'online'" link type="warning" size="small" @click="handleOffline(row as ValueAddedItem)">下线</ElButton>
            <ElButton link type="danger" size="small" @click="handleDelete(row as ValueAddedItem)">删除</ElButton>
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

    <!-- 新增/编辑弹窗 -->
    <ElDialog v-model="dialog.visible" :title="dialog.title" width="620px" :close-on-click-modal="false">
      <ElForm ref="formRef" :model="form" :rules="rules" label-width="90px">
        <ElFormItem label="服务名称" prop="name">
          <ElInput v-model="form.name" placeholder="如：智慧急诊预检分诊云平台" maxlength="100" />
        </ElFormItem>
        <ElFormItem label="副标题">
          <ElInput v-model="form.subtitle" placeholder="App 卡片展示的简短说明（选填）" maxlength="120" />
        </ElFormItem>
        <ElFormItem label="图标">
          <ElInput v-model="form.icon" placeholder="图标 URL 或本地图标路径（选填）" maxlength="500" />
        </ElFormItem>
        <ElFormItem label="封面图">
          <ElInput v-model="form.cover" placeholder="大卡片背景图 URL（选填）" maxlength="500" />
        </ElFormItem>
        <ElFormItem label="跳转类型">
          <ElSelect v-model="form.link_type" class="w-full">
            <ElOption v-for="o in LINK_TYPE_OPTIONS" :key="o.value" :label="o.label" :value="o.value" />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="跳转地址" prop="link_url">
          <ElInput v-model="form.link_url" placeholder="H5 路径 / 外链 https://... / App 内页 /pages/xxx/index" maxlength="500" />
        </ElFormItem>
        <ElFormItem label="排序">
          <ElInputNumber v-model="form.sort_order" :min="0" :max="9999" />
          <span class="ml-2 text-xs text-gray-400">数值越大越靠前</span>
        </ElFormItem>
        <ElFormItem label="备注">
          <ElInput v-model="form.remark" placeholder="内部备注（选填）" maxlength="500" />
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="dialog.visible = false">取消</ElButton>
        <ElButton type="primary" :loading="saving" @click="save">确定</ElButton>
      </template>
    </ElDialog>
  </div>
</template>
