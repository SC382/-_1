<!-- 胸痛学院内容管理（仅系统管理员）：发布 PPT / 视频 / 文档等学习资源 -->
<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { ElMessage, ElMessageBox, type FormInstance, type FormRules, type UploadRawFile } from "element-plus";
import AcademyAPI, { type AcademyForm, type AcademyItem, type AcademyType } from "@/api/cpx/academy";

defineOptions({ name: "CpxAcademy" });

const loading = ref(false);
const data = ref<AcademyItem[]>([]);
const total = ref(0);
const query = reactive({
  page_no: 1,
  page_size: 10,
  keyword: "",
  content_type: undefined as string | undefined,
  category: undefined as string | undefined,
  published: undefined as number | undefined,
});

const TYPE_OPTIONS: { label: string; value: AcademyType }[] = [
  { label: "视频", value: "video" },
  { label: "PPT", value: "ppt" },
  { label: "Word 文档", value: "doc" },
  { label: "PDF", value: "pdf" },
  { label: "其他", value: "other" },
];
const typeLabel = (t?: string) => TYPE_OPTIONS.find((o) => o.value === t)?.label ?? t ?? "-";
const typeColor = (t?: string) => {
  if (t === "video") return "danger";
  if (t === "ppt") return "warning";
  if (t === "pdf") return "success";
  if (t === "doc") return "primary";
  return "info";
};
function fmtSize(n?: number | null) {
  if (!n) return "-";
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1024 / 1024).toFixed(1)} MB`;
}

async function fetchData() {
  loading.value = true;
  try {
    const res = await AcademyAPI.list({ ...query });
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
  query.content_type = undefined;
  query.category = undefined;
  query.published = undefined;
  query.page_no = 1;
  fetchData();
}

// ── 新增 / 编辑 ────────────────────────────────────────
const dialog = reactive({ visible: false, title: "新增内容", mode: "create" as "create" | "edit" });
const saving = ref(false);
const formRef = ref<FormInstance>();
const form = reactive<AcademyForm>({
  title: "",
  content_type: "other",
  category: "",
  summary: "",
  file_path: "",
  file_name: "",
  file_size: 0,
  published: 0,
  sort_num: 0,
});
const rules: FormRules = {
  title: [{ required: true, message: "请输入标题", trigger: "blur" }],
  file_path: [{ required: true, message: "请先上传文件", trigger: "change" }],
};

const uploading = ref(false);

function openCreate() {
  dialog.mode = "create";
  dialog.title = "新增内容";
  Object.assign(form, { title: "", content_type: "other", category: "", summary: "", file_path: "", file_name: "", file_size: 0, published: 0, sort_num: 0 });
  dialog.visible = true;
}
function openEdit(row: AcademyItem) {
  dialog.mode = "edit";
  dialog.title = "编辑内容";
  Object.assign(form, {
    id: row.id,
    title: row.title,
    content_type: row.content_type,
    category: row.category ?? "",
    summary: row.summary ?? "",
    file_path: row.file_path,
    file_name: row.file_name ?? "",
    file_size: row.file_size ?? 0,
    published: row.published ?? 0,
    sort_num: row.sort_num ?? 0,
  });
  dialog.visible = true;
}

async function handleUpload(file: UploadRawFile) {
  uploading.value = true;
  try {
    const res = await AcademyAPI.upload(file);
    const d = res.data.data;
    form.file_path = d.file_path;
    form.file_name = d.file_name;
    form.file_size = d.file_size;
    form.content_type = d.content_type;
    ElMessage.success(`上传成功（识别为${typeLabel(d.content_type)}）`);
  } catch {
    /* 错误已提示 */
  } finally {
    uploading.value = false;
  }
  return false; // 阻止 element-plus 默认上传
}

async function save() {
  const valid = await formRef.value?.validate().catch(() => false);
  if (!valid) return;
  saving.value = true;
  try {
    if (dialog.mode === "edit" && form.id) {
      await AcademyAPI.update(form.id, { ...form });
      ElMessage.success("修改成功");
    } else {
      await AcademyAPI.create({ ...form });
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

// ── 发布切换 / 删除 ────────────────────────────────────
async function togglePublish(row: AcademyItem) {
  const action = row.published === 1 ? "下架" : "发布";
  try {
    await ElMessageBox.confirm(`确认${action}「${row.title}」？`, "提示", {
      type: "warning",
      confirmButtonText: action,
      cancelButtonText: "取消",
    });
  } catch {
    return;
  }
  try {
    const res = await AcademyAPI.publish(row.id);
    ElMessage.success(`${res.data.data.published === 1 ? "发布" : "下架"}成功`);
    fetchData();
  } catch {
    /* 错误已提示 */
  }
}

async function handleDelete(row: AcademyItem) {
  try {
    await ElMessageBox.confirm(`确认删除「${row.title}」？将同时删除已上传的文件，不可恢复。`, "删除确认", {
      type: "error",
      confirmButtonText: "删除",
      cancelButtonText: "取消",
    });
  } catch {
    return;
  }
  try {
    await AcademyAPI.remove(row.id);
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
        <ElInput v-model="query.keyword" placeholder="标题关键字" clearable class="w-56" @keyup.enter="handleSearch" />
        <ElSelect v-model="query.content_type" placeholder="内容类型" clearable class="w-32">
          <ElOption v-for="o in TYPE_OPTIONS" :key="o.value" :label="o.label" :value="o.value" />
        </ElSelect>
        <ElInput v-model="query.category" placeholder="分类" clearable class="w-32" @keyup.enter="handleSearch" />
        <ElSelect v-model="query.published" placeholder="发布状态" clearable class="w-32">
          <ElOption label="已发布" :value="1" />
          <ElOption label="草稿" :value="0" />
        </ElSelect>
        <ElButton type="primary" @click="handleSearch">查询</ElButton>
        <ElButton @click="handleReset">重置</ElButton>
        <div class="flex-1" />
        <ElButton type="primary" @click="openCreate">
          <span class="i-ri:file-add-line mr-1" />发布内容
        </ElButton>
      </div>
    </ElCard>

    <ElCard shadow="never">
      <ElTable v-loading="loading" :data="data" border stripe>
        <ElTableColumn type="index" label="#" width="55" />
        <ElTableColumn prop="title" label="标题" min-width="200" show-overflow-tooltip />
        <ElTableColumn label="类型" width="110" align="center">
          <template #default="{ row }">
            <ElTag :type="typeColor((row as AcademyItem).content_type)" size="small" effect="light">
              {{ typeLabel((row as AcademyItem).content_type) }}
            </ElTag>
          </template>
        </ElTableColumn>
        <ElTableColumn prop="category" label="分类" width="110" align="center">
          <template #default="{ row }">
            {{ (row as AcademyItem).category || "-" }}
          </template>
        </ElTableColumn>
        <ElTableColumn label="文件" min-width="170" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="text-gray-600">{{ (row as AcademyItem).file_name || "-" }}</span>
            <span class="ml-1 text-xs text-gray-400">{{ fmtSize((row as AcademyItem).file_size) }}</span>
          </template>
        </ElTableColumn>
        <ElTableColumn prop="view_count" label="浏览" width="70" align="center" />
        <ElTableColumn label="发布状态" width="100" align="center">
          <template #default="{ row }">
            <ElTag :type="(row as AcademyItem).published === 1 ? 'success' : 'info'" size="small">
              {{ (row as AcademyItem).published === 1 ? "已发布" : "草稿" }}
            </ElTag>
          </template>
        </ElTableColumn>
        <ElTableColumn prop="create_time" label="创建时间" min-width="160" />
        <ElTableColumn label="操作" width="230" fixed="right">
          <template #default="{ row }">
            <ElButton link type="primary" size="small" @click="openEdit(row as AcademyItem)">编辑</ElButton>
            <ElButton link :type="(row as AcademyItem).published === 1 ? 'warning' : 'success'" size="small" @click="togglePublish(row as AcademyItem)">
              {{ (row as AcademyItem).published === 1 ? "下架" : "发布" }}
            </ElButton>
            <ElButton link type="danger" size="small" @click="handleDelete(row as AcademyItem)">删除</ElButton>
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
        <ElFormItem label="标题" prop="title">
          <ElInput v-model="form.title" placeholder="如：胸痛中心建设指南" maxlength="200" />
        </ElFormItem>
        <ElFormItem label="文件上传" prop="file_path">
          <ElUpload
            :auto-upload="false"
            :show-file-list="false"
            accept=".mp4,.mov,.ppt,.pptx,.doc,.docx,.pdf,.xls,.xlsx,.txt,.zip,.png,.jpg,.jpeg,.gif,.webp"
            :on-change="(file: any) => handleUpload(file.raw as UploadRawFile)"
          >
            <ElButton type="primary" plain :loading="uploading">
              <span class="i-ri:upload-2-line mr-1" />选择文件上传
            </ElButton>
            <span class="ml-3 text-xs text-gray-400">支持视频 / PPT / Word / PDF / Excel / 图片 / 文本；视频 ≤300MB，其他 ≤60MB</span>
          </ElUpload>
          <div v-if="form.file_name" class="mt-2 flex items-center gap-2 text-sm">
            <ElTag :type="typeColor(form.content_type)" size="small" effect="light">{{ typeLabel(form.content_type) }}</ElTag>
            <span class="text-gray-600">{{ form.file_name }}</span>
            <span class="text-xs text-gray-400">{{ fmtSize(form.file_size) }}</span>
          </div>
        </ElFormItem>
        <ElFormItem label="内容类型">
          <ElSelect v-model="form.content_type" class="w-full">
            <ElOption v-for="o in TYPE_OPTIONS" :key="o.value" :label="o.label" :value="o.value" />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="分类">
          <ElInput v-model="form.category" placeholder="如：指南共识 / 培训课程 / 学术会议" maxlength="50" />
        </ElFormItem>
        <ElFormItem label="简介">
          <ElInput v-model="form.summary" type="textarea" :rows="3" placeholder="资源简介（选填）" />
        </ElFormItem>
        <ElFormItem label="排序">
          <ElInputNumber v-model="form.sort_num" :min="0" :max="999" />
          <span class="ml-2 text-xs text-gray-400">数字越小越靠前</span>
        </ElFormItem>
        <ElFormItem label="发布状态">
          <ElRadioGroup v-model="form.published">
            <ElRadio :value="1">立即发布</ElRadio>
            <ElRadio :value="0">存为草稿</ElRadio>
          </ElRadioGroup>
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="dialog.visible = false">取消</ElButton>
        <ElButton type="primary" :loading="saving" @click="save">确定</ElButton>
      </template>
    </ElDialog>
  </div>
</template>
