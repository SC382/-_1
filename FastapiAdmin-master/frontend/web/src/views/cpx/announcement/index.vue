<!-- 公告管理（仅系统管理员）：Web 端发布公告，App 端首页 banner + 详情查看 -->
<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from "element-plus";
import AnnouncementAPI, { type AnnouncementForm, type AnnouncementItem, type AnnouncementStatus, type AnnouncementType } from "@/api/cpx/announcement";

defineOptions({ name: "CpxAnnouncement" });

const loading = ref(false);
const data = ref<AnnouncementItem[]>([]);
const total = ref(0);
const query = reactive({
  page_no: 1,
  page_size: 10,
  keyword: "",
  status: undefined as string | undefined,
  type: undefined as string | undefined,
});

const TYPE_OPTIONS: { label: string; value: AnnouncementType }[] = [
  { label: "系统公告", value: "system" },
  { label: "版本更新", value: "version" },
  { label: "活动通知", value: "activity" },
  { label: "普通通知", value: "notice" },
];
const STATUS_OPTIONS: { label: string; value: AnnouncementStatus; tag: "info" | "success" | "danger" }[] = [
  { label: "草稿", value: "draft", tag: "info" },
  { label: "已发布", value: "published", tag: "success" },
  { label: "已下线", value: "offline", tag: "danger" },
];
const typeLabel = (t?: string) => TYPE_OPTIONS.find((o) => o.value === t)?.label ?? t ?? "-";
const statusInfo = (s?: string) => STATUS_OPTIONS.find((o) => o.value === s) ?? { label: s ?? "-", value: s ?? "", tag: "info" as const };

async function fetchData() {
  loading.value = true;
  try {
    const res = await AnnouncementAPI.list({ ...query });
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
  query.type = undefined;
  query.page_no = 1;
  fetchData();
}

// ── 新增 / 编辑 ────────────────────────────────────────
const dialog = reactive({ visible: false, title: "新增公告", mode: "create" as "create" | "edit" });
const saving = ref(false);
const formRef = ref<FormInstance>();
const form = reactive<AnnouncementForm>({
  title: "",
  subtitle: "",
  content: "",
  cover: "",
  type: "notice",
  sort_order: 0,
  expires_at: null,
  remark: "",
});
const rules: FormRules = {
  title: [{ required: true, message: "请输入公告标题", trigger: "blur" }],
};

function openCreate() {
  dialog.mode = "create";
  dialog.title = "新增公告";
  Object.assign(form, { title: "", subtitle: "", content: "", cover: "", type: "notice", sort_order: 0, expires_at: null, remark: "" });
  dialog.visible = true;
}
function openEdit(row: AnnouncementItem) {
  dialog.mode = "edit";
  dialog.title = "编辑公告";
  Object.assign(form, {
    id: row.id,
    title: row.title,
    subtitle: row.subtitle ?? "",
    content: row.content ?? "",
    cover: row.cover ?? "",
    type: row.type ?? "notice",
    sort_order: row.sort_order ?? 0,
    expires_at: row.expires_at ?? null,
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
      await AnnouncementAPI.update(form.id, { ...form });
      ElMessage.success("修改成功");
    } else {
      await AnnouncementAPI.create({ ...form });
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

// ── 发布 / 下线 / 删除 ─────────────────────────────────
async function handlePublish(row: AnnouncementItem) {
  try {
    await ElMessageBox.confirm(`确认发布「${row.title}」？发布后 App 端首页即可见。`, "提示", {
      type: "warning",
      confirmButtonText: "发布",
      cancelButtonText: "取消",
    });
  } catch {
    return;
  }
  try {
    await AnnouncementAPI.publish(row.id);
    ElMessage.success("发布成功");
    fetchData();
  } catch {
    /* 错误已提示 */
  }
}

async function handleOffline(row: AnnouncementItem) {
  try {
    await ElMessageBox.confirm(`确认下线「${row.title}」？下线后 App 端不再展示。`, "提示", {
      type: "warning",
      confirmButtonText: "下线",
      cancelButtonText: "取消",
    });
  } catch {
    return;
  }
  try {
    await AnnouncementAPI.offline(row.id);
    ElMessage.success("已下线");
    fetchData();
  } catch {
    /* 错误已提示 */
  }
}

async function handleDelete(row: AnnouncementItem) {
  try {
    await ElMessageBox.confirm(`确认删除「${row.title}」？不可恢复。`, "删除确认", {
      type: "error",
      confirmButtonText: "删除",
      cancelButtonText: "取消",
    });
  } catch {
    return;
  }
  try {
    await AnnouncementAPI.remove(row.id);
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
        <ElInput v-model="query.keyword" placeholder="公告标题" clearable class="w-56" @keyup.enter="handleSearch" />
        <ElSelect v-model="query.type" placeholder="公告类型" clearable class="w-36">
          <ElOption v-for="o in TYPE_OPTIONS" :key="o.value" :label="o.label" :value="o.value" />
        </ElSelect>
        <ElSelect v-model="query.status" placeholder="状态" clearable class="w-32">
          <ElOption v-for="o in STATUS_OPTIONS" :key="o.value" :label="o.label" :value="o.value" />
        </ElSelect>
        <ElButton type="primary" @click="handleSearch">查询</ElButton>
        <ElButton @click="handleReset">重置</ElButton>
        <div class="flex-1" />
        <ElButton type="primary" @click="openCreate">
          <span class="i-ri:megaphone-line mr-1" />发布公告
        </ElButton>
      </div>
    </ElCard>

    <ElCard shadow="never">
      <ElTable v-loading="loading" :data="data" border stripe>
        <ElTableColumn type="index" label="#" width="55" />
        <ElTableColumn prop="title" label="标题" min-width="220" show-overflow-tooltip />
        <ElTableColumn label="类型" width="110" align="center">
          <template #default="{ row }">
            <ElTag size="small" effect="light">{{ typeLabel((row as AnnouncementItem).type) }}</ElTag>
          </template>
        </ElTableColumn>
        <ElTableColumn label="状态" width="100" align="center">
          <template #default="{ row }">
            <ElTag :type="statusInfo((row as AnnouncementItem).status).tag" size="small">
              {{ statusInfo((row as AnnouncementItem).status).label }}
            </ElTag>
          </template>
        </ElTableColumn>
        <ElTableColumn prop="sort_order" label="排序" width="70" align="center" />
        <ElTableColumn prop="published_at" label="发布时间" min-width="160">
          <template #default="{ row }">
            {{ (row as AnnouncementItem).published_at || "-" }}
          </template>
        </ElTableColumn>
        <ElTableColumn prop="create_time" label="创建时间" min-width="160" />
        <ElTableColumn label="操作" width="230" fixed="right">
          <template #default="{ row }">
            <ElButton link type="primary" size="small" @click="openEdit(row as AnnouncementItem)">编辑</ElButton>
            <ElButton v-if="(row as AnnouncementItem).status === 'draft' || (row as AnnouncementItem).status === 'offline'" link type="success" size="small" @click="handlePublish(row as AnnouncementItem)">发布</ElButton>
            <ElButton v-if="(row as AnnouncementItem).status === 'published'" link type="warning" size="small" @click="handleOffline(row as AnnouncementItem)">下线</ElButton>
            <ElButton link type="danger" size="small" @click="handleDelete(row as AnnouncementItem)">删除</ElButton>
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
    <ElDialog v-model="dialog.visible" :title="dialog.title" width="680px" :close-on-click-modal="false">
      <ElForm ref="formRef" :model="form" :rules="rules" label-width="90px">
        <ElFormItem label="公告标题" prop="title">
          <ElInput v-model="form.title" placeholder="如：版本更新(20260804)：随访管理(AI版)" maxlength="80" />
        </ElFormItem>
        <ElFormItem label="副标题">
          <ElInput v-model="form.subtitle" placeholder="banner 内展示的简短说明（选填）" maxlength="120" />
        </ElFormItem>
        <ElFormItem label="公告类型">
          <ElSelect v-model="form.type" class="w-full">
            <ElOption v-for="o in TYPE_OPTIONS" :key="o.value" :label="o.label" :value="o.value" />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="公告内容">
          <ElInput v-model="form.content" type="textarea" :rows="6" placeholder="公告正文（支持 HTML / 换行文本），App 详情页展示" />
        </ElFormItem>
        <ElFormItem label="封面图">
          <ElInput v-model="form.cover" placeholder="封面图 URL（选填）" maxlength="500" />
        </ElFormItem>
        <ElFormItem label="排序">
          <ElInputNumber v-model="form.sort_order" :min="0" :max="9999" />
          <span class="ml-2 text-xs text-gray-400">数值越大越靠前</span>
        </ElFormItem>
        <ElFormItem label="失效时间">
          <ElDatePicker v-model="form.expires_at" type="datetime" placeholder="选填，过期后 App 端自动隐藏" style="width: 240px" />
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
