<!-- 病例填报模板管理（仅系统管理员）：模板列表 ⇄ 可视化表单设计器 -->
<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch, nextTick } from "vue";
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from "element-plus";
import TemplateAPI, {
  type TemplateDetail,
  type TemplateField,
  type TemplateFieldForm,
  type TemplateForm,
  type TemplateTable,
} from "@/api/cpx/template";
import FaSearchInput from "@/components/forms/fa-search-input/index.vue";
import FaSearchItem from "@/components/forms/fa-search-item/index.vue";

defineOptions({ name: "CpxTemplate" });

// ── 视图切换（模板列表 / 表单设计器）────────────────
const viewMode = ref<"list" | "designer">("list");
const currentTemplate = ref<TemplateDetail | null>(null);

// ── 模板列表 ────────────────────────────────────────────
const loading = ref(false);
const data = ref<TemplateTable[]>([]);
const total = ref(0);
const query = reactive({
  page_no: 1,
  page_size: 10,
  keyword: "",
  status: undefined as number | undefined,
});

async function fetchData() {
  loading.value = true;
  try {
    const res = await TemplateAPI.list({ ...query });
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

// ── 创建/编辑模板基础信息弹窗 ──────────────────────────
const templateDialog = reactive({ visible: false, title: "创建模板", mode: "create" as "create" | "edit" });
const templateSaving = ref(false);
const templateFormRef = ref<FormInstance>();
const templateForm = reactive<TemplateForm>({ template_name: "", version: "1.0", status: 1 });
const templateRules: FormRules = {
  template_name: [{ required: true, message: "请输入模板名称", trigger: "blur" }],
  version: [{ required: true, message: "请输入模板版本", trigger: "blur" }],
};

function openTemplateCreate() {
  templateDialog.mode = "create";
  templateDialog.title = "创建模板";
  Object.assign(templateForm, { id: undefined, template_name: "", version: "1.0", status: 1 });
  templateDialog.visible = true;
}
function openTemplateEdit(row: TemplateTable) {
  templateDialog.mode = "edit";
  templateDialog.title = "编辑模板";
  Object.assign(templateForm, {
    id: row.id,
    template_name: row.template_name,
    version: row.version ?? "",
    status: row.status ?? 1,
  });
  templateDialog.visible = true;
}
async function saveTemplate() {
  const valid = await templateFormRef.value?.validate().catch(() => false);
  if (!valid) return;
  templateSaving.value = true;
  try {
    if (templateDialog.mode === "edit" && templateForm.id) {
      await TemplateAPI.update(templateForm.id, { ...templateForm });
      ElMessage.success("修改成功");
    } else {
      await TemplateAPI.create({ ...templateForm });
      ElMessage.success("创建成功，模板默认为未发布状态");
    }
    templateDialog.visible = false;
    fetchData();
  } catch {
    /* 错误已由拦截器提示 */
  } finally {
    templateSaving.value = false;
  }
}

// ── 列表行的发布 / 启用禁用 ────────────────────────────
async function handlePublish(row: TemplateTable) {
  try {
    await ElMessageBox.confirm(
      `确认发布模板「${row.template_name}」？\n发布后字段将被锁定，如需改动请新建版本。`,
      "发布确认",
      { type: "warning", confirmButtonText: "确认发布", cancelButtonText: "取消" }
    );
  } catch {
    return;
  }
  await TemplateAPI.publish(row.id);
  ElMessage.success("发布成功");
  fetchData();
}
async function handleUnpublish(row: TemplateTable) {
  try {
    await ElMessageBox.confirm(
      `确认取消发布模板「${row.template_name}」？\n仅当该模板未被任何病例使用时才能取消，取消后医生端将不再显示该模板。`,
      "取消发布确认",
      { type: "warning", confirmButtonText: "确认取消发布", cancelButtonText: "取消" }
    );
  } catch {
    return;
  }
  try {
    await TemplateAPI.unpublish(row.id);
    ElMessage.success("已取消发布，模板回退为草稿");
    fetchData();
  } catch {
    /* 错误已由拦截器提示（如：已被病例使用） */
  }
}
async function handleDeleteTemplate(row: TemplateTable) {
  try {
    await ElMessageBox.confirm(
      `确认删除模板「${row.template_name}」？\n将连带删除其下所有字段，且仅当该模板未被任何病例使用时才可删除，此操作不可恢复。`,
      "删除模板",
      { type: "error", confirmButtonText: "删除", cancelButtonText: "取消" }
    );
  } catch {
    return;
  }
  try {
    await TemplateAPI.remove(row.id);
    ElMessage.success("模板已删除");
    fetchData();
  } catch {
    /* 错误已由拦截器提示（如：已被病例使用） */
  }
}
async function toggleStatus(row: TemplateTable) {
  const action = row.status === 1 ? "禁用" : "启用";
  try {
    await ElMessageBox.confirm(`确定要${action}模板「${row.template_name}」吗？`, "提示", {
      type: "warning",
      confirmButtonText: "确定",
      cancelButtonText: "取消",
    });
  } catch {
    return;
  }
  await TemplateAPI.update(row.id, { status: row.status === 1 ? 0 : 1 });
  ElMessage.success(`${action}成功`);
  fetchData();
}

// ── 进入设计器 ────────────────────────────────────────
const fields = ref<TemplateField[]>([]);
const activeTab = ref<string>("");
const designerLoading = ref(false);
const isPublished = computed(() => currentTemplate.value?.published === 1);

interface CategoryItem {
  name: string;
  order: number;
  count: number;
}
const categories = computed<CategoryItem[]>(() => {
  const map = new Map<string, CategoryItem>();
  fields.value.forEach((f) => {
    const k = f.tab_name || "未分类";
    if (!map.has(k))
      map.set(k, { name: k, order: f.tab_order || 0, count: 0 });
    map.get(k)!.count++;
  });
  return Array.from(map.values()).sort((a, b) => a.order - b.order);
});

const fieldsInActiveTab = computed(() => {
  return fields.value
    .filter((f) => (f.tab_name || "未分类") === activeTab.value)
    .sort((a, b) => (a.sort_num || 0) - (b.sort_num || 0));
});

watch(categories, (cats) => {
  // 切换或新增分类时，若当前 activeTab 不在列表里则自动切到第一个
  if (!cats.find((c) => c.name === activeTab.value)) {
    activeTab.value = cats[0]?.name || "";
  }
});

async function enterDesigner(row: TemplateTable) {
  viewMode.value = "designer";
  designerLoading.value = true;
  try {
    const res = await TemplateAPI.detail(row.id);
    currentTemplate.value = res.data.data;
    fields.value = (res.data.data.fields ?? []).slice();
    activeTab.value = categories.value[0]?.name || "";
  } finally {
    designerLoading.value = false;
  }
}

function backToList() {
  viewMode.value = "list";
  currentTemplate.value = null;
  fields.value = [];
  fetchData();
}

async function refreshDesigner() {
  if (!currentTemplate.value) return;
  const res = await TemplateAPI.detail(currentTemplate.value.id);
  currentTemplate.value = res.data.data;
  fields.value = (res.data.data.fields ?? []).slice();
  // activeTab 由 watcher 校正
}

// ── 分类管理 ──────────────────────────────────────────

const catDialog = reactive({
  visible: false,
  title: "新建分类",
  mode: "create" as "create" | "edit",
});
const catForm = reactive({ name: "", order: 0, originalName: "" });
const catFormRef = ref<FormInstance>();
const catRules: FormRules = {
  name: [{ required: true, message: "请输入分类名", trigger: "blur" }],
};

function openAddCategory() {
  catDialog.mode = "create";
  catDialog.title = "新建分类";
  Object.assign(catForm, {
    name: "",
    order: (categories.value[categories.value.length - 1]?.order ?? -1) + 1,
    originalName: "",
  });
  catDialog.visible = true;
}
function openEditCategory(c: CategoryItem) {
  catDialog.mode = "edit";
  catDialog.title = "编辑分类";
  Object.assign(catForm, { name: c.name, order: c.order, originalName: c.name });
  catDialog.visible = true;
}
async function saveCategory() {
  if (!currentTemplate.value) return;
  const valid = await catFormRef.value?.validate().catch(() => false);
  if (!valid) return;
  try {
    if (catDialog.mode === "create") {
      // 新建分类：直接将当前 activeTab 切换为新名（需添加至少一个字段后该分类才出现在列表）
      activeTab.value = catForm.name.trim();
      ElMessage.success(`已切到新分类「${catForm.name}」，请添加字段`);
    } else {
      if (!catForm.originalName || catForm.name === catForm.originalName) {
        catDialog.visible = false;
        return;
      }
      await TemplateAPI.renameTab({
        template_id: currentTemplate.value.id,
        old_name: catForm.originalName,
        new_name: catForm.name.trim(),
        tab_order: catForm.order,
      });
      ElMessage.success("分类已重命名");
      await refreshDesigner();
      activeTab.value = catForm.name.trim();
    }
    catDialog.visible = false;
  } catch {
    /* 错误已提示 */
  }
}

async function deleteCategory(c: CategoryItem) {
  if (!currentTemplate.value) return;
  try {
    await ElMessageBox.confirm(
      `确认删除分类「${c.name}」及其下 ${c.count} 个字段？此操作不可恢复。`,
      "删除确认",
      { type: "warning", confirmButtonText: "删除", cancelButtonText: "取消" }
    );
  } catch {
    return;
  }
  try {
    await TemplateAPI.deleteTab({ template_id: currentTemplate.value.id, tab_name: c.name });
    ElMessage.success(`已删除分类「${c.name}」`);
    await refreshDesigner();
  } catch {
    /* 错误已提示 */
  }
}

// ── 字段管理 ──────────────────────────────────────────

const FIELD_TYPE_OPTIONS = [
  { label: "文本", value: "text" },
  { label: "数字", value: "number" },
  { label: "日期", value: "date" },
  { label: "时间", value: "time" },
  { label: "日期时间", value: "datetime" },
  { label: "选择", value: "select" },
  { label: "图片", value: "image" },
];
function typeLabel(t?: string) {
  return FIELD_TYPE_OPTIONS.find((o) => o.value === t)?.label ?? t ?? "-";
}

const fieldDialog = reactive({
  visible: false,
  title: "新增字段",
  mode: "create" as "create" | "edit",
});
const fieldSaving = ref(false);
const fieldFormRef = ref<FormInstance>();
const fieldForm = reactive({
  id: undefined as number | undefined,
  field_name: "",
  field_code: "",
  field_type: "text",
  required_flag: 0,
  sort_num: 0,
  optionsText: "",
  tab_name: "",
  tab_order: 0,
});
const fieldRules = computed<FormRules>(() => ({
  field_name: [{ required: true, message: "请输入字段名称", trigger: "blur" }],
  field_code: [
    { required: true, message: "请输入字段编码", trigger: "blur" },
    { pattern: /^[a-z][a-z0-9_]*$/, message: "编码须以小写字母开头，仅含字母/数字/下划线", trigger: "blur" },
  ],
  field_type: [{ required: true, message: "请选择字段类型", trigger: "change" }],
  tab_name: [{ required: true, message: "请选择或输入分类", trigger: "change" }],
}));

function openAddField() {
  if (!activeTab.value) {
    ElMessage.warning("请先选择或新建一个分类");
    return;
  }
  fieldDialog.mode = "create";
  fieldDialog.title = "新增字段";
  const inTab = fieldsInActiveTab.value;
  Object.assign(fieldForm, {
    id: undefined,
    field_name: "",
    field_code: "",
    field_type: "text",
    required_flag: 0,
    sort_num: (inTab[inTab.length - 1]?.sort_num ?? 0) + 1,
    optionsText: "",
    tab_name: activeTab.value,
    tab_order: categories.value.find((c) => c.name === activeTab.value)?.order ?? 0,
  });
  fieldDialog.visible = true;
}
function openEditField(f: TemplateField) {
  fieldDialog.mode = "edit";
  fieldDialog.title = "修改字段";
  Object.assign(fieldForm, {
    id: f.id,
    field_name: f.field_name,
    field_code: f.field_code,
    field_type: f.field_type,
    required_flag: f.required_flag ?? 0,
    sort_num: f.sort_num ?? 0,
    optionsText: Array.isArray(f.field_options) ? (f.field_options as string[]).join("\n") : "",
    tab_name: f.tab_name || "未分类",
    tab_order: f.tab_order || 0,
  });
  fieldDialog.visible = true;
}
async function saveField() {
  if (!currentTemplate.value) return;
  const valid = await fieldFormRef.value?.validate().catch(() => false);
  if (!valid) return;

  const optionsText = fieldForm.optionsText.trim();
  if (fieldForm.field_type === "select" && !optionsText) {
    ElMessage.warning("选择类型请配置下拉选项（每行一个）");
    return;
  }

  fieldSaving.value = true;
  try {
    const payload: TemplateFieldForm = {
      template_id: currentTemplate.value.id,
      tab_name: fieldForm.tab_name,
      tab_order: fieldForm.tab_order || 0,
      field_name: fieldForm.field_name,
      field_code: fieldForm.field_code,
      field_type: fieldForm.field_type,
      required_flag: fieldForm.required_flag,
      sort_num: fieldForm.sort_num,
      field_options:
        fieldForm.field_type === "select"
          ? optionsText.split("\n").map((s) => s.trim()).filter(Boolean)
          : null,
    };
    if (fieldDialog.mode === "edit" && fieldForm.id) {
      await TemplateAPI.updateField(fieldForm.id, payload);
      ElMessage.success("修改成功");
    } else {
      await TemplateAPI.addField(payload);
      ElMessage.success("新增成功");
    }
    fieldDialog.visible = false;
    await refreshDesigner();
    activeTab.value = fieldForm.tab_name;
  } catch {
    /* 错误已提示 */
  } finally {
    fieldSaving.value = false;
  }
}
async function deleteField(f: TemplateField) {
  try {
    await ElMessageBox.confirm(`确定删除字段「${f.field_name}」吗？`, "删除确认", {
      type: "warning",
      confirmButtonText: "删除",
      cancelButtonText: "取消",
    });
  } catch {
    return;
  }
  await TemplateAPI.deleteField(f.id);
  ElMessage.success("删除成功");
  await refreshDesigner();
}

// ── 复制标准 / 发布 ──────────────────────────────────

async function copyStandard() {
  if (!currentTemplate.value) return;
  try {
    await ElMessageBox.confirm(
      "将从内置标准模板复制 7 个分类、约 60 个字段，**覆盖**当前模板已有字段。继续？",
      "复制标准模板",
      { type: "warning", confirmButtonText: "确认复制", cancelButtonText: "取消" }
    );
  } catch {
    return;
  }
  try {
    const res = await TemplateAPI.copyStandard(currentTemplate.value.id);
    ElMessage.success(`已复制 ${res.data.data.copied} 个标准字段（${res.data.data.tabs} 个分类）`);
    await refreshDesigner();
  } catch {
    /* 错误已提示 */
  }
}

async function publishTemplate() {
  if (!currentTemplate.value) return;
  try {
    await ElMessageBox.confirm(
      `确认发布模板「${currentTemplate.value.template_name}」？\n发布后字段将被锁定，如需改动请新建版本。`,
      "发布确认",
      { type: "warning", confirmButtonText: "确认发布", cancelButtonText: "取消" }
    );
  } catch {
    return;
  }
  await TemplateAPI.publish(currentTemplate.value.id);
  ElMessage.success("发布成功");
  if (currentTemplate.value) currentTemplate.value.published = 1;
}

async function unpublishTemplate() {
  if (!currentTemplate.value) return;
  try {
    await ElMessageBox.confirm(
      `确认取消发布模板「${currentTemplate.value.template_name}」？\n仅当该模板未被任何病例使用时才能取消，取消后医生端将不再显示该模板。`,
      "取消发布确认",
      { type: "warning", confirmButtonText: "确认取消发布", cancelButtonText: "取消" }
    );
  } catch {
    return;
  }
  try {
    await TemplateAPI.unpublish(currentTemplate.value.id);
    ElMessage.success("已取消发布，模板回退为草稿");
    if (currentTemplate.value) currentTemplate.value.published = 0;
  } catch {
    /* 错误已由拦截器提示（如：已被病例使用） */
  }
}

onMounted(fetchData);
</script>

<template>
  <div class="cpx-page p-4">
    <!-- ═══════════ 视图① 模板列表 ═══════════ -->
    <template v-if="viewMode === 'list'">
      <ElCard shadow="never" class="mb-4">
        <div class="flex flex-wrap items-end gap-x-4 gap-y-3">
          <FaSearchItem label="模板名称">
            <FaSearchInput v-model="query.keyword" placeholder="模板名称" clearable class="w-56" @keyup.enter="handleSearch" />
          </FaSearchItem>
          <FaSearchItem label="使用状态">
            <ElSelect v-model="query.status" placeholder="使用状态" clearable class="w-32">
              <ElOption label="启用" :value="1" />
              <ElOption label="禁用" :value="0" />
            </ElSelect>
          </FaSearchItem>
          <ElButton type="primary" @click="handleSearch">查询</ElButton>
          <ElButton @click="handleReset">重置</ElButton>
          <div class="flex-1" />
          <ElButton type="primary" @click="openTemplateCreate">
            <span class="i-ri:file-add-line mr-1" />创建模板
          </ElButton>
        </div>
      </ElCard>

      <ElCard shadow="never">
        <ElTable v-loading="loading" :data="data" border stripe>
          <ElTableColumn type="index" label="#" width="55" />
          <ElTableColumn prop="template_name" label="模板名称" min-width="180" show-overflow-tooltip />
          <ElTableColumn prop="version" label="模板版本" width="110" align="center" />
          <ElTableColumn prop="status" label="使用状态" width="100" align="center">
            <template #default="{ row }">
              <ElTag :type="(row as TemplateTable).status === 1 ? 'success' : 'info'" size="small">
                {{ (row as TemplateTable).status === 1 ? "启用" : "禁用" }}
              </ElTag>
            </template>
          </ElTableColumn>
          <ElTableColumn prop="published" label="发布状态" width="110" align="center">
            <template #default="{ row }">
              <ElTag :type="(row as TemplateTable).published === 1 ? 'primary' : 'warning'" size="small" effect="light">
                {{ (row as TemplateTable).published === 1 ? "已发布" : "未发布" }}
              </ElTag>
            </template>
          </ElTableColumn>
          <ElTableColumn prop="create_time" label="创建时间" min-width="160" />
          <ElTableColumn label="操作" width="260" fixed="right">
            <template #default="{ row }">
              <ElButton link type="primary" size="small" @click="enterDesigner(row as TemplateTable)">表单设计器</ElButton>
              <ElButton link type="primary" size="small" @click="openTemplateEdit(row as TemplateTable)">编辑</ElButton>
              <ElButton
                v-if="(row as TemplateTable).published !== 1"
                link
                type="success"
                size="small"
                @click="handlePublish(row as TemplateTable)"
              >
                发布
              </ElButton>
              <template v-else>
                <ElTag size="small" type="success" effect="plain">已发布</ElTag>
                <ElButton link type="warning" size="small" @click="handleUnpublish(row as TemplateTable)">取消发布</ElButton>
              </template>
              <ElButton
                link
                :type="(row as TemplateTable).status === 1 ? 'danger' : 'success'"
                size="small"
                @click="toggleStatus(row as TemplateTable)"
              >
                {{ (row as TemplateTable).status === 1 ? "禁用" : "启用" }}
              </ElButton>
              <ElButton link type="danger" size="small" @click="handleDeleteTemplate(row as TemplateTable)">删除</ElButton>
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
    </template>

    <!-- ═══════════ 视图② 可视化表单设计器 ═══════════ -->
    <template v-else>
      <!-- 顶栏 -->
      <ElCard shadow="never" class="mb-4">
        <div class="flex flex-wrap items-center gap-3">
          <ElButton @click="backToList">
            <span class="i-ri:arrow-left-line mr-1" />返回模板列表
          </ElButton>
          <div class="flex min-w-0 items-center gap-2">
            <span class="i-ri:file-list-3-line text-2xl text-blue-500" />
            <span class="truncate text-base font-bold text-gray-700">{{ currentTemplate?.template_name }}</span>
            <ElTag size="small" type="info" effect="plain">v{{ currentTemplate?.version }}</ElTag>
            <ElTag v-if="isPublished" size="small" type="success">已发布</ElTag>
            <ElTag v-else size="small" type="warning">未发布</ElTag>
            <ElTag size="small" effect="plain">{{ fields.length }} 个字段</ElTag>
          </div>
          <div class="flex-1" />
          <ElButton :disabled="isPublished" @click="copyStandard">
            <span class="i-ri:download-line mr-1" />从标准模板复制
          </ElButton>
          <ElButton v-if="isPublished" type="warning" plain @click="unpublishTemplate">
            <span class="i-ri:rewind-line mr-1" />取消发布
          </ElButton>
          <ElButton v-else type="success" @click="publishTemplate">
            <span class="i-ri:rocket-line mr-1" />发布
          </ElButton>
        </div>
      </ElCard>

      <ElAlert
        v-if="isPublished"
        type="warning"
        :closable="false"
        show-icon
        class="mb-4"
        title="该模板已发布，分类与字段均已锁定（保护已填病例数据）。如需修改：未被病例使用时点右上角「取消发布」；已被使用时请新建模板版本。"
      />

      <div v-loading="designerLoading" class="designer-grid">
        <!-- 左：分类 -->
        <ElCard shadow="never" class="cat-card">
          <div class="cat-head">
            <span class="cat-title">分类（Tab）</span>
            <ElButton link type="primary" size="small" :disabled="isPublished" @click="openAddCategory">
              <span class="i-ri:add-line mr-1" />新建
            </ElButton>
          </div>
          <div v-if="!categories.length" class="cat-empty">暂无分类</div>
          <div
            v-for="c in categories"
            :key="c.name"
            class="cat-item"
            :class="{ active: activeTab === c.name }"
            @click="activeTab = c.name"
          >
            <div class="cat-item-main">
              <span class="cat-name">{{ c.name }}</span>
              <span class="cat-count">{{ c.count }} 字段</span>
            </div>
            <div v-if="!isPublished" class="cat-item-actions" @click.stop>
              <ElButton link type="primary" size="small" @click="openEditCategory(c)">编辑</ElButton>
              <ElButton link type="danger" size="small" @click="deleteCategory(c)">删除</ElButton>
            </div>
          </div>
        </ElCard>

        <!-- 右：字段 -->
        <ElCard shadow="never" class="field-card">
          <div class="field-head">
            <span class="field-title">分类「{{ activeTab || '（未选择）' }}」下的字段</span>
            <ElButton type="primary" :disabled="isPublished || !activeTab" @click="openAddField">
              <span class="i-ri:add-line mr-1" />新增字段
            </ElButton>
          </div>

          <ElTable v-if="activeTab" :data="fieldsInActiveTab" border stripe>
            <ElTableColumn type="index" label="#" width="55" />
            <ElTableColumn prop="field_name" label="字段名称" min-width="140" />
            <ElTableColumn prop="field_code" label="字段编码" min-width="140" />
            <ElTableColumn label="类型" width="100" align="center">
              <template #default="{ row }">{{ typeLabel((row as TemplateField).field_type) }}</template>
            </ElTableColumn>
            <ElTableColumn label="必填" width="70" align="center">
              <template #default="{ row }">
                <ElTag :type="(row as TemplateField).required_flag === 1 ? 'danger' : 'info'" size="small" effect="plain">
                  {{ (row as TemplateField).required_flag === 1 ? "必填" : "选填" }}
                </ElTag>
              </template>
            </ElTableColumn>
            <ElTableColumn label="下拉选项" min-width="180" show-overflow-tooltip>
              <template #default="{ row }">
                <span v-if="(row as TemplateField).field_type === 'select' && Array.isArray((row as TemplateField).field_options)" class="opts-text">
                  {{ ((row as TemplateField).field_options as string[]).join(' / ') }}
                </span>
                <span v-else class="text-gray-300">-</span>
              </template>
            </ElTableColumn>
            <ElTableColumn prop="sort_num" label="排序" width="70" align="center" />
            <ElTableColumn label="操作" width="150" fixed="right">
              <template #default="{ row }">
                <ElButton link type="primary" size="small" :disabled="isPublished" @click="openEditField(row as TemplateField)">修改</ElButton>
                <ElButton link type="danger" size="small" :disabled="isPublished" @click="deleteField(row as TemplateField)">删除</ElButton>
              </template>
            </ElTableColumn>
          </ElTable>
          <ElEmpty v-else description="请先在左侧选择或新建一个分类" :image-size="80" />

          <ElEmpty
            v-if="activeTab && !fieldsInActiveTab.length"
            description="该分类暂无字段，点击右上角「新增字段」开始配置"
            :image-size="80"
            class="mt-4"
          />
        </ElCard>
      </div>
    </template>

    <!-- ═══════════ 弹窗：创建/编辑模板基础信息 ═══════════ -->
    <ElDialog v-model="templateDialog.visible" :title="templateDialog.title" width="480px">
      <ElForm ref="templateFormRef" :model="templateForm" :rules="templateRules" label-width="90px">
        <ElFormItem label="模板名称" prop="template_name">
          <ElInput v-model="templateForm.template_name" placeholder="如：胸痛患者病例模板" />
        </ElFormItem>
        <ElFormItem label="模板版本" prop="version">
          <ElInput v-model="templateForm.version" placeholder="如：1.0" />
        </ElFormItem>
        <ElFormItem label="使用状态">
          <ElRadioGroup v-model="templateForm.status">
            <ElRadio :value="1">启用</ElRadio>
            <ElRadio :value="0">禁用</ElRadio>
          </ElRadioGroup>
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="templateDialog.visible = false">取消</ElButton>
        <ElButton type="primary" :loading="templateSaving" @click="saveTemplate">提交</ElButton>
      </template>
    </ElDialog>

    <!-- ═══════════ 弹窗：分类（新建/编辑） ═══════════ -->
    <ElDialog v-model="catDialog.visible" :title="catDialog.title" width="420px">
      <ElForm ref="catFormRef" :model="catForm" :rules="catRules" label-width="80px">
        <ElFormItem label="分类名" prop="name">
          <ElInput v-model="catForm.name" placeholder="如：基本信息 / 院前急救" maxlength="50" />
        </ElFormItem>
        <ElFormItem label="排序">
          <ElInputNumber v-model="catForm.order" :min="0" :max="999" />
          <span class="ml-2 text-xs text-gray-400">数字越小越靠前</span>
        </ElFormItem>
        <ElAlert
          v-if="catDialog.mode === 'create'"
          type="info"
          :closable="false"
          show-icon
          title="新建分类后，请在右侧为该分类添加至少一个字段，分类才会出现在左侧列表中。"
        />
      </ElForm>
      <template #footer>
        <ElButton @click="catDialog.visible = false">取消</ElButton>
        <ElButton type="primary" @click="saveCategory">确定</ElButton>
      </template>
    </ElDialog>

    <!-- ═══════════ 弹窗：字段（新增/修改） ═══════════ -->
    <ElDialog v-model="fieldDialog.visible" :title="fieldDialog.title" width="560px">
      <ElForm ref="fieldFormRef" :model="fieldForm" :rules="fieldRules" label-width="100px">
        <ElFormItem label="所属分类" prop="tab_name">
          <ElSelect
            v-model="fieldForm.tab_name"
            filterable
            allow-create
            default-first-option
            placeholder="选择已有分类或输入新分类"
            class="w-full"
          >
            <ElOption v-for="c in categories" :key="c.name" :label="c.name" :value="c.name" />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="字段名称" prop="field_name">
          <ElInput v-model="fieldForm.field_name" placeholder="如：患者姓名" maxlength="100" />
        </ElFormItem>
        <ElFormItem label="字段编码" prop="field_code">
          <ElInput v-model="fieldForm.field_code" placeholder="如：patient_name（表单数据存储键）" maxlength="50" />
        </ElFormItem>
        <ElFormItem label="字段类型" prop="field_type">
          <ElSelect v-model="fieldForm.field_type" class="w-full">
            <ElOption v-for="o in FIELD_TYPE_OPTIONS" :key="o.value" :label="`${o.label} (${o.value})`" :value="o.value" />
          </ElSelect>
        </ElFormItem>
        <ElFormItem v-if="fieldForm.field_type === 'select'" label="下拉选项">
          <ElInput
            v-model="fieldForm.optionsText"
            type="textarea"
            :rows="4"
            placeholder="每行一个选项，如：&#10;男&#10;女"
          />
        </ElFormItem>
        <ElFormItem label="是否必填">
          <ElRadioGroup v-model="fieldForm.required_flag">
            <ElRadio :value="1">必填</ElRadio>
            <ElRadio :value="0">选填</ElRadio>
          </ElRadioGroup>
        </ElFormItem>
        <ElFormItem label="排序">
          <ElInputNumber v-model="fieldForm.sort_num" :min="0" :max="999" />
          <span class="ml-2 text-xs text-gray-400">数字越小越靠前</span>
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="fieldDialog.visible = false">取消</ElButton>
        <ElButton type="primary" :loading="fieldSaving" @click="saveField">确定</ElButton>
      </template>
    </ElDialog>
  </div>
</template>

<style lang="scss" scoped>
.designer-grid {
  display: grid;
  grid-template-columns: 280px 1fr;
  gap: 16px;
  align-items: stretch;
}
.cat-card { min-height: 480px; }
.field-card { min-height: 480px; }
.cat-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.cat-title { font-size: 14px; font-weight: 600; color: #374151; }
.cat-empty {
  padding: 24px 8px;
  text-align: center;
  color: #9ca3af;
  font-size: 12px;
}
.cat-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  margin-bottom: 6px;
  border-radius: 8px;
  cursor: pointer;
  background: #f9fafb;
  border: 1px solid transparent;
  transition: all 0.15s;
}
.cat-item:hover { background: #eff6ff; }
.cat-item.active {
  background: #2563eb;
  color: #ffffff;
  border-color: #1d4ed8;
}
.cat-item.active .cat-count { color: rgba(255, 255, 255, 0.8); }
.cat-item-main { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.cat-name { font-size: 14px; font-weight: 500; }
.cat-count { font-size: 12px; color: #6b7280; }
.cat-item-actions { display: flex; gap: 4px; opacity: 0.85; }

.field-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.field-title { font-size: 14px; font-weight: 600; color: #374151; }
.opts-text { color: #4b5563; font-size: 12px; }
</style>
