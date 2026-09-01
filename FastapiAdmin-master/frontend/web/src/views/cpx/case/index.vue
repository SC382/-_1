<!-- 病例数据管理（仅系统管理员）：医院卡片总览 ⇄ 医院病例列表 双视图 + 大尺寸只读详情弹窗 -->
<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { saveAs } from "file-saver";
import HospitalAPI, { type HospitalTable } from "@/api/cpx/hospital";
import CaseAPI, { type CaseDetail, type CaseTable, type CaseTimeline, type CaseAnalysis } from "@/api/cpx/case";
import UserAPI, { type DoctorTable } from "@/api/cpx/user";
import FaSearchInput from "@/components/forms/fa-search-input/index.vue";
import FaSearchItem from "@/components/forms/fa-search-item/index.vue";

defineOptions({ name: "CpxCase" });

// ── 视图切换 ──────────────────────────────────────────
const viewMode = ref<"overview" | "cases">("overview");
const currentHospital = ref<HospitalTable | null>(null);

// ── 视图① 医院卡片总览 ────────────────────────────────
const hospitalLoading = ref(false);
const hospitalList = ref<HospitalTable[]>([]);
const hospitalTotal = ref(0);
const hospitalQuery = reactive({
  page_no: 1,
  page_size: 12,
  hospital_name: "",
  hospital_level: undefined as string | undefined,
  province: undefined as string | undefined,
  status: undefined as number | undefined,
});

const LEVEL_OPTIONS = ["三级甲等", "三级乙等", "二级甲等", "二级乙等"];

const provinceOptions = computed(() => {
  const set = new Set<string>();
  hospitalList.value.forEach((h) => {
    if (h.province) set.add(h.province);
  });
  return Array.from(set);
});

async function fetchHospitals() {
  hospitalLoading.value = true;
  try {
    const res = await HospitalAPI.list({ ...hospitalQuery });
    hospitalList.value = res.data.data.items;
    hospitalTotal.value = res.data.data.total;
  } finally {
    hospitalLoading.value = false;
  }
}
function handleHospitalSearch() {
  hospitalQuery.page_no = 1;
  fetchHospitals();
}
function handleHospitalReset() {
  hospitalQuery.hospital_name = "";
  hospitalQuery.hospital_level = undefined;
  hospitalQuery.province = undefined;
  hospitalQuery.status = undefined;
  hospitalQuery.page_no = 1;
  fetchHospitals();
}

/** 进入该医院病例列表 */
async function enterCases(hospital: HospitalTable) {
  currentHospital.value = hospital;
  viewMode.value = "cases";
  resetCaseQuery();
  await Promise.all([fetchCases(), fetchDoctors()]);
}
function backToOverview() {
  viewMode.value = "overview";
  currentHospital.value = null;
  fetchHospitals();
}

// ── 视图② 该医院病例列表 ──────────────────────────────
const caseLoading = ref(false);
const caseList = ref<CaseTable[]>([]);
const caseTotal = ref(0);
const caseQuery = reactive({
  page_no: 1,
  page_size: 10,
  case_no: "",
  doctor_name: "",
  patient_name: "",
  doctor_id: undefined as number | undefined,
  dateRange: [] as string[],
  status: "" as string,
});
function resetCaseQuery() {
  Object.assign(caseQuery, {
    page_no: 1,
    page_size: 10,
    case_no: "",
    doctor_name: "",
    patient_name: "",
    doctor_id: undefined,
    dateRange: [],
    status: "",
  });
}

const STATUS_OPTIONS = [
  { label: "待审核", value: "submitted" },
  { label: "审核通过", value: "approved" },
  { label: "审核驳回", value: "rejected" },
];
const statusLabel = (s?: string) => {
  if (s === "submitted") return "待审核";
  if (s === "approved") return "审核通过";
  if (s === "rejected") return "审核驳回";
  return s === "draft" ? "草稿" : s ?? "-";
};
const statusTagType = (s?: string) => {
  if (s === "submitted") return "warning";
  if (s === "approved") return "success";
  if (s === "rejected") return "danger";
  return "info";
};

async function fetchCases() {
  caseLoading.value = true;
  try {
    const res = await CaseAPI.list({
      page_no: caseQuery.page_no,
      page_size: caseQuery.page_size,
      hospital_id: currentHospital.value?.id,
      case_no: caseQuery.case_no || undefined,
      doctor_name: caseQuery.doctor_name || undefined,
      patient_name: caseQuery.patient_name || undefined,
      doctor_id: caseQuery.doctor_id,
      status: caseQuery.status || undefined,
      start_time: caseQuery.dateRange?.[0],
      end_time: caseQuery.dateRange?.[1],
    });
    caseList.value = res.data.data.items;
    caseTotal.value = res.data.data.total;
  } finally {
    caseLoading.value = false;
  }
}
function handleCaseSearch() {
  caseQuery.page_no = 1;
  fetchCases();
}

// ── 导出 Excel（按当前筛选条件）───────────────────────
const exporting = ref(false);
async function handleExport() {
  exporting.value = true;
  try {
    const res = await CaseAPI.exportExcel({
      hospital_id: currentHospital.value?.id,
      case_no: caseQuery.case_no || undefined,
      doctor_name: caseQuery.doctor_name || undefined,
      patient_name: caseQuery.patient_name || undefined,
      doctor_id: caseQuery.doctor_id,
      status: caseQuery.status || undefined,
      start_time: caseQuery.dateRange?.[0],
      end_time: caseQuery.dateRange?.[1],
    });
    const blob = res.data as unknown as Blob;
    const t = new Date();
    const pad = (x: number) => String(x).padStart(2, "0");
    const name = `病例导出_${currentHospital.value?.hospital_name || "全部"}_${t.getFullYear()}${pad(t.getMonth() + 1)}${pad(t.getDate())}_${pad(t.getHours())}${pad(t.getMinutes())}.xlsx`;
    saveAs(blob, name);
    ElMessage.success("导出成功，请查看下载文件");
  } catch {
    /* 错误已由拦截器提示 */
  } finally {
    exporting.value = false;
  }
}

// ── 导出 PDF（按当前筛选条件）───────────────────────
const exportingPdf = ref(false);
async function handleExportPdf() {
  exportingPdf.value = true;
  try {
    const res = await CaseAPI.exportPdf({
      hospital_id: currentHospital.value?.id,
      case_no: caseQuery.case_no || undefined,
      doctor_name: caseQuery.doctor_name || undefined,
      patient_name: caseQuery.patient_name || undefined,
      doctor_id: caseQuery.doctor_id,
      status: caseQuery.status || undefined,
      start_time: caseQuery.dateRange?.[0],
      end_time: caseQuery.dateRange?.[1],
    });
    const blob = res.data as unknown as Blob;
    const t = new Date();
    const pad = (x: number) => String(x).padStart(2, "0");
    const name = `病例导出_${currentHospital.value?.hospital_name || "全部"}_${t.getFullYear()}${pad(t.getMonth() + 1)}${pad(t.getDate())}_${pad(t.getHours())}${pad(t.getMinutes())}.pdf`;
    saveAs(blob, name);
    ElMessage.success("导出成功，请查看下载文件");
  } catch {
    /* 错误已由拦截器提示 */
  } finally {
    exportingPdf.value = false;
  }
}

// ── 所属医生下拉（当前医院医生）───────────────────────
const doctorOptions = ref<DoctorTable[]>([]);
async function fetchDoctors() {
  if (!currentHospital.value) return;
  const res = await UserAPI.listDoctors({ page_no: 1, page_size: 100, hospital_id: currentHospital.value.id });
  doctorOptions.value = res.data.data.items;
}

// ── 病例详情弹窗（大尺寸只读）─────────────────────────
const detailVisible = ref(false);
const detailLoading = ref(false);
const detail = ref<CaseDetail | null>(null);
const timelineData = ref<CaseTimeline | null>(null);
const analysisData = ref<CaseAnalysis | null>(null);

async function openDetail(row: CaseTable) {
  detailVisible.value = true;
  detailLoading.value = true;
  try {
    const res = await CaseAPI.detail(row.id);
    detail.value = res.data.data;
    // 并行拉取时间轴与单病例分析（详情页只读展示，非时间采集）
    const [tl, an] = await Promise.all([
      CaseAPI.timeline(row.id).then((r) => r.data.data).catch(() => null),
      CaseAPI.analysis(row.id).then((r) => r.data.data).catch(() => null),
    ]);
    timelineData.value = tl;
    analysisData.value = an;
  } finally {
    detailLoading.value = false;
  }
}

// ── 单病例 PDF 导出（打印）─────────────────────────
const exportingDetailPdf = ref(false);
async function handleExportPdfDetail() {
  if (!detail.value?.id) return;
  exportingDetailPdf.value = true;
  try {
    const res = await CaseAPI.exportPdfById(detail.value.id);
    const blob = res.data as unknown as Blob;
    const t = new Date();
    const pad = (x: number) => String(x).padStart(2, "0");
    const name = `病例报告_${detail.value.case_no || detail.value.id}_${t.getFullYear()}${pad(t.getMonth() + 1)}${pad(t.getDate())}_${pad(t.getHours())}${pad(t.getMinutes())}.pdf`;
    saveAs(blob, name);
    ElMessage.success("已生成 PDF，请查看下载文件");
  } catch {
    /* 错误已由拦截器提示 */
  } finally {
    exportingDetailPdf.value = false;
  }
}

/** 删除病例（级联删除详情/审核/随访/心电） */
async function handleDeleteCase(row: CaseTable) {
  try {
    await ElMessageBox.confirm(
      `确认删除病例「${row.patient_name}（${row.case_no}）」？\n将连带删除该病例的详情、审核记录、随访与心电记录，此操作不可恢复。`,
      "删除病例",
      { type: "error", confirmButtonText: "删除", cancelButtonText: "取消" }
    );
  } catch {
    return;
  }
  try {
    await CaseAPI.remove(row.id);
    ElMessage.success("病例已删除");
    fetchCases();
  } catch {
    /* 错误已由拦截器提示 */
  }
}

/** 编辑电话（与 APP 端互通，更新 case_record.phone） */
const editingPhone = ref(false);
const savingPhone = ref(false);
const newPhone = ref("");
async function editPhone() {
  if (!detail.value) return;
  newPhone.value = detail.value.phone || "";
  editingPhone.value = true;
}
async function savePhone() {
  if (!detail.value || !detail.value.id) return;
  const val = newPhone.value.trim();
  if (!val) {
    ElMessage.warning("电话不能为空");
    return;
  }
  savingPhone.value = true;
  try {
    await CaseAPI.update(detail.value.id, { phone: val });
    ElMessage.success("电话已更新");
    editingPhone.value = false;
    detail.value.phone = val;
  } catch (e) {
    ElMessage.error((e as { message?: string })?.message || "更新失败");
  } finally {
    savingPhone.value = false;
  }
}

/** 模板字段值展示（select 选项转文本） */
function fieldValue(f: { field_code: string; field_type: string; field_options?: unknown }): string {
  const raw = detail.value?.form_data?.[f.field_code];
  if (raw === undefined || raw === null || raw === "") return "-";
  const v = String(raw);
  if (f.field_type === "select" && Array.isArray(f.field_options)) {
    const opt = (f.field_options as Array<{ label?: string; value?: string } | string>).find((o) => {
      if (typeof o === "string") return o === v;
      return o.value === v;
    });
    if (opt && typeof opt === "object" && opt.label) return opt.label;
  }
  return v;
}

/** 字典外的患者基本信息字段：显示时回退为中文名（避免英文字段编码裸露） */
const EXTRA_FIELD_CN: Record<string, string> = {
  detail_address: "详细住址",
  first_contact_time: "首次接触时间",
  id_type: "证件类型",
  insurance_no: "医保卡号",
  insurance_type: "医保类型",
};

/** 以下 code 不进入"全部填报数据"模块展示：
 *  - inpatient_no / discharge_date：已在"完整患者信息"模块展示，避免重复；
 *  - remote_ecg_receive（接收远程心电图）：属远程心电协同，已在"心电图 AI 诊断"模块统一展示，模块五不重复。
 */
const SKIP_FILLED_FIELDS = new Set<string>(["inpatient_no", "discharge_date", "remote_ecg_receive"]);

/** 去掉名称中纯英文的括号注释（如 "首次医疗接触时间(FMC)" -> "首次医疗接触时间"、"院前血压(mmHg)" -> "院前血压"），只保留中文 */
function cleanFieldName(n: string): string {
  return n.replace(/\s*\([A-Za-z0-9\s./+-]+\)\s*$/g, "").trim();
}

/** 图片字段路径标准化：兼容 /api/v1/static/...、/uploads/...、uploads/... 三种写法，统一成可访问的绝对路径 */
function imageSrc(p: string): string {
  if (!p) return "";
  if (p.startsWith("http://") || p.startsWith("https://")) return p;
  if (p.startsWith("/api/v1/static")) return p;
  if (p.startsWith("/")) return `/api/v1/static${p}`;
  return `/api/v1/static/${p}`;
}

/** 按字段字典渲染 form_data 的全部字段（三端统一展示；字典 + form_data 取并集，空字段也展示，避免漏 key）
 *  去重/清洗策略：
 *  ① 字典字段已在 step1 用中文名渲染，step2 跳过这些 code，避免用英文字段编码重复出现（如 "年龄" 与 "age" 并存）；
 *  ② 按中文名合并，同名只留一条（优先保留有值项）—— 解决 证件类型：字典 card_type(空) 与 表单 id_type(有值) 同名；
 *  ③ 字段名中的英文括号注释剥离，只留中文。
 */
const filledFields = computed(() => {
  const fd = detail.value?.form_data || {};
  const dict = detail.value?.field_dict?.length ? detail.value.field_dict : detail.value?.template_fields;
  const dictCodes = new Set<string>((dict || []).map((f: Record<string, any>) => f.code ?? f.field_code));
  const rows: Array<{ name: string; value: string; long: boolean; isImage: boolean }> = [];
  const seenName = new Map<string, number>(); // 中文名 -> rows 下标，用于同名合并
  const push = (code: string, rawName: string, type?: string, options?: unknown) => {
    if (SKIP_FILLED_FIELDS.has(code)) return; // 住院号/出院日期（模块二已展示）+ 接收远程心电图（心电图模块已展示），避免重复
    const raw = fd[code];
    const v = raw === undefined || raw === null ? "" : String(raw);
    let val = v;
    if (type === "select" && Array.isArray(options)) {
      const opt = (options as Array<{ label?: string; value?: string } | string>).find((o) => {
        if (typeof o === "string") return o === v;
        return o.value === v;
      });
      if (opt && typeof opt === "object" && opt.label) val = opt.label;
    }
    const name = cleanFieldName(rawName);
    const isImage = type === "image";
    const display = val || "-";
    // 同名合并：已存在同名项时，优先保留有值那条（如 证件类型：card_type 空 / id_type 有值）
    if (seenName.has(name)) {
      const idx = seenName.get(name)!;
      if (rows[idx].value === "-" && display !== "-") rows[idx].value = display;
      return;
    }
    seenName.set(name, rows.length);
    rows.push({ name, value: display, long: v.length > 40, isImage });
  };
  // 1) 先按字段字典渲染（带中文名 / 类型 / 选项）
  // 注意：后端 field_dict 用 code/name/type/options，template_fields 用 field_code/field_name/field_type/field_options，两套键都兼容
  (dict || []).forEach((f: Record<string, any>) =>
    push(f.code ?? f.field_code, f.name ?? f.field_name, f.type ?? f.field_type, f.options ?? f.field_options),
  );
  // 2) 仅补 form_data 中"不在字典里"的 key（英文字段编码已在 step1 用中文名渲染过，跳过避免重复；其余回退中文名）
  Object.keys(fd).forEach((k) => {
    if (dictCodes.has(k)) return;
    push(k, EXTRA_FIELD_CN[k] ?? k);
  });
  return rows;
});

/** 文本字段（走 ElDescriptions 两列网格） */
const textFields = computed(() => filledFields.value.filter((f) => !f.isImage));
/** 图片字段（每个独立全宽卡片，真正"占一行"） */
const imageFields = computed(() => filledFields.value.filter((f) => f.isImage));

const isLongText = (f: { field_code: string }) => {
  const v = detail.value?.form_data?.[f.field_code];
  return typeof v === "string" && v.length > 40;
};

/** 点击图片放大查看（新标签页打开原图） */
function openImage(src: string) {
  if (src) window.open(src, "_blank");
}

// ── 时间轴 / 病例分析 状态配色（与 APP 端保持一致）────────
const metricColor = (s: string) => (s === "pass" ? "#10b981" : s === "fail" ? "#ef4444" : "#9ca3af");
const metricText = (s: string) => (s === "pass" ? "达标" : s === "fail" ? "不达标" : "未采集");
const analysisColor = (s: string) =>
  s === "pass" ? "#2563eb" : s === "fail" ? "#ef4444" : s === "info" ? "#10b981" : "#9ca3af";
const analysisLabel = (s: string) =>
  s === "pass" ? "达标" : s === "fail" ? "不达标" : s === "info" ? "已记录" : "未采集/不适用";

onMounted(fetchHospitals);
</script>

<template>
  <div class="cpx-page p-4">
    <!-- ═══════════ 视图① 医院卡片总览 ═══════════ -->
    <template v-if="viewMode === 'overview'">
      <ElCard shadow="never" class="mb-4">
        <div class="flex flex-wrap items-center gap-x-4 gap-y-3">
          <FaSearchItem label="医院名称">
            <FaSearchInput v-model="hospitalQuery.hospital_name" placeholder="医院名称" clearable class="w-48" @keyup.enter="handleHospitalSearch" />
          </FaSearchItem>
          <FaSearchItem label="医院等级">
            <ElSelect v-model="hospitalQuery.hospital_level" placeholder="医院等级" clearable class="w-32">
              <ElOption v-for="lv in LEVEL_OPTIONS" :key="lv" :label="lv" :value="lv" />
            </ElSelect>
          </FaSearchItem>
          <FaSearchItem label="所在地区">
            <ElSelect v-model="hospitalQuery.province" placeholder="所在地区" clearable filterable class="w-32">
              <ElOption v-for="p in provinceOptions" :key="p" :label="p" :value="p" />
            </ElSelect>
          </FaSearchItem>
          <FaSearchItem label="医院状态">
            <ElSelect v-model="hospitalQuery.status" placeholder="医院状态" clearable class="w-28">
              <ElOption label="正常" :value="1" />
              <ElOption label="禁用" :value="0" />
            </ElSelect>
          </FaSearchItem>
          <ElButton type="primary" @click="handleHospitalSearch">查询</ElButton>
          <ElButton @click="handleHospitalReset">重置</ElButton>
        </div>
      </ElCard>

      <div v-loading="hospitalLoading" class="min-h-40">
        <ElEmpty v-if="!hospitalLoading && hospitalList.length === 0" description="暂无医院数据" />
        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-4">
          <div
            v-for="h in hospitalList"
            :key="h.id"
            class="group cursor-pointer rounded-xl bg-white p-4 shadow-sm ring-1 ring-black/5 transition-all hover:-translate-y-0.5 hover:shadow-md"
            :class="{ 'opacity-60 saturate-50': h.status !== 1 }"
            @click="enterCases(h)"
          >
            <div class="flex items-start justify-between gap-2">
              <div class="min-w-0">
                <div class="truncate text-base font-bold text-gray-700">{{ h.hospital_name }}</div>
                <div class="mt-1.5 flex flex-wrap gap-1.5">
                  <ElTag size="small" type="primary" effect="light">{{ h.hospital_level || "未设置" }}</ElTag>
                  <ElTag size="small" type="info" effect="plain">{{ h.province }}{{ h.city }}</ElTag>
                </div>
              </div>
              <ElTag :type="h.status === 1 ? 'success' : 'info'" size="small">
                {{ h.status === 1 ? "正常" : "禁用" }}
              </ElTag>
            </div>
            <div class="mt-4 flex items-center justify-between rounded-lg bg-emerald-50 px-3 py-2.5">
              <span class="text-xs text-gray-500">病例总数</span>
              <span class="text-xl font-bold text-emerald-600">{{ h.case_count ?? 0 }}</span>
            </div>
            <div class="mt-2 text-center text-xs text-gray-400">点击卡片查看该院病例</div>
          </div>
        </div>

        <div class="mt-4 flex justify-end">
          <ElPagination
            v-model:current-page="hospitalQuery.page_no"
            v-model:page-size="hospitalQuery.page_size"
            :total="hospitalTotal"
            :page-sizes="[12, 24, 48]"
            layout="total, sizes, prev, pager, next"
            @current-change="fetchHospitals"
            @size-change="handleHospitalSearch"
          />
        </div>
      </div>
    </template>

    <!-- ═══════════ 视图② 医院病例列表 ═══════════ -->
    <template v-else>
      <ElCard shadow="never" class="mb-4">
        <div class="flex flex-wrap items-center gap-4">
          <ElButton @click="backToOverview">
            <span class="i-ri:arrow-left-line mr-1" />返回医院总览
          </ElButton>
          <div class="flex min-w-0 items-center gap-3">
            <span class="i-ri:clipboard-line text-2xl text-blue-500" />
            <div class="min-w-0">
              <div class="flex items-center gap-2">
                <span class="truncate text-base font-bold text-gray-700">{{ currentHospital?.hospital_name }}</span>
                <ElTag v-if="currentHospital" :type="currentHospital.status === 1 ? 'success' : 'info'" size="small">
                  {{ currentHospital.status === 1 ? "正常" : "禁用" }}
                </ElTag>
              </div>
              <div class="mt-0.5 text-xs text-gray-400">共 {{ caseTotal }} 份病例</div>
            </div>
          </div>
        </div>
      </ElCard>

      <ElCard shadow="never">
        <!-- 病例搜索筛选 -->
        <div class="mb-4 flex flex-wrap items-center gap-x-4 gap-y-3">
          <FaSearchItem label="病例编号">
            <FaSearchInput
              v-model="caseQuery.case_no"
              placeholder="病例编号"
              clearable
              class="w-56"
              @keyup.enter="handleCaseSearch"
            />
          </FaSearchItem>
          <FaSearchItem label="医生姓名">
            <FaSearchInput v-model="caseQuery.doctor_name" placeholder="医生姓名" clearable class="w-32" @keyup.enter="handleCaseSearch" />
          </FaSearchItem>
          <FaSearchItem label="患者姓名">
            <FaSearchInput v-model="caseQuery.patient_name" placeholder="患者姓名" clearable class="w-32" @keyup.enter="handleCaseSearch" />
          </FaSearchItem>
          <FaSearchItem label="所属医生">
            <ElSelect v-model="caseQuery.doctor_id" placeholder="所属医生" clearable filterable class="w-36">
              <ElOption v-for="d in doctorOptions" :key="d.id" :label="d.real_name" :value="d.id" />
            </ElSelect>
          </FaSearchItem>
          <FaSearchItem label="提交时间">
            <ElDatePicker
              v-model="caseQuery.dateRange"
              type="daterange"
              range-separator="至"
              start-placeholder="开始"
              end-placeholder="结束"
              value-format="YYYY-MM-DD"
              class="!w-60"
            />
          </FaSearchItem>
          <FaSearchItem label="审核状态">
            <ElSelect v-model="caseQuery.status" placeholder="审核状态" clearable class="w-32">
              <ElOption v-for="s in STATUS_OPTIONS" :key="s.value" :label="s.label" :value="s.value" />
            </ElSelect>
          </FaSearchItem>
          <ElButton type="primary" @click="handleCaseSearch">查询</ElButton>
          <ElButton @click="resetCaseQuery; fetchCases()">重置</ElButton>
          <ElButton type="success" :loading="exporting" @click="handleExport">
            <span class="i-ri:file-excel-line mr-1" />导出 Excel
          </ElButton>
          <ElButton type="primary" plain :loading="exportingPdf" @click="handleExportPdf">
            <span class="i-ri:file-pdf-line mr-1" />导出 PDF
          </ElButton>
        </div>

        <!-- 病例列表 -->
        <ElTable v-loading="caseLoading" :data="caseList" border stripe>
          <ElTableColumn type="index" label="#" width="55" />
          <ElTableColumn prop="case_no" label="病例编号" min-width="170" show-overflow-tooltip />
          <ElTableColumn prop="patient_name" label="患者姓名" min-width="100" />
          <ElTableColumn prop="hospital_name" label="所属医院" min-width="140" show-overflow-tooltip />
          <ElTableColumn prop="doctor_name" label="提交医生" min-width="100" />
          <ElTableColumn prop="status" label="状态" width="100" align="center">
            <template #default="{ row }">
              <ElTag :type="statusTagType((row as CaseTable).status)" size="small">
                {{ statusLabel((row as CaseTable).status) }}
              </ElTag>
            </template>
          </ElTableColumn>
          <ElTableColumn prop="create_time" label="创建时间" min-width="160" />
          <ElTableColumn label="操作" width="180" fixed="right">
            <template #default="{ row }">
              <ElButton link type="primary" size="small" @click="openDetail(row as CaseTable)">
                <span class="i-ri:eye-line mr-1" />病例详情
              </ElButton>
              <ElButton link type="danger" size="small" @click="handleDeleteCase(row as CaseTable)">删除</ElButton>
            </template>
          </ElTableColumn>
        </ElTable>

        <div class="mt-4 flex justify-end">
          <ElPagination
            v-model:current-page="caseQuery.page_no"
            v-model:page-size="caseQuery.page_size"
            :total="caseTotal"
            :page-sizes="[10, 20, 50]"
            layout="total, sizes, prev, pager, next"
            @current-change="fetchCases"
            @size-change="handleCaseSearch"
          />
        </div>
      </ElCard>
    </template>

    <!-- ═══════════ 病例详情弹窗（大尺寸只读）═══════════ -->
    <ElDialog
      v-model="detailVisible"
      width="920px"
      top="4vh"
      :close-on-click-modal="false"
      class="case-detail-dialog"
    >
      <template #header>
        <div class="flex w-full items-center justify-between pr-6">
          <span class="text-base font-semibold text-gray-800">病例详情</span>
          <ElButton type="primary" plain size="small" :loading="exportingDetailPdf" @click="handleExportPdfDetail">
            <span class="i-ri:printer-line mr-1" />打印 / 导出 PDF
          </ElButton>
        </div>
      </template>
      <div v-loading="detailLoading" class="max-h-[75vh] overflow-y-auto pr-1">
        <template v-if="detail">
          <!-- 模块一：病例基础信息 -->
          <div class="mb-5">
            <div class="mb-2 flex items-center gap-2">
              <span class="i-ri:information-line text-blue-500" />
              <span class="text-sm font-semibold text-gray-700">病例基础信息</span>
            </div>
            <ElDescriptions :column="2" border size="small">
              <ElDescriptionsItem label="病例编号">{{ detail.case_no || "-" }}</ElDescriptionsItem>
              <ElDescriptionsItem label="所属医院">{{ detail.hospital_name || "-" }}</ElDescriptionsItem>
              <ElDescriptionsItem label="提交医生">{{ detail.doctor_name || "-" }}</ElDescriptionsItem>
              <ElDescriptionsItem label="来院方式">{{ detail.come_type || "-" }}</ElDescriptionsItem>
              <ElDescriptionsItem label="诊断类型">
                <ElTag v-if="detail.diagnose_type" type="danger" effect="light" size="small">{{ detail.diagnose_type }}</ElTag>
                <span v-else>-</span>
              </ElDescriptionsItem>
              <ElDescriptionsItem label="病例状态">
                <ElTag :type="statusTagType(detail.status)" size="small">{{ statusLabel(detail.status) }}</ElTag>
              </ElDescriptionsItem>
              <ElDescriptionsItem label="病例提交时间" :span="2">{{ detail.create_time || "-" }}</ElDescriptionsItem>
            </ElDescriptions>
          </div>

          <!-- 模块二：完整患者信息 -->
          <div class="mb-5">
            <div class="mb-2 flex items-center gap-2">
              <span class="i-ri:user-heart-line text-rose-500" />
              <span class="text-sm font-semibold text-gray-700">完整患者信息</span>
            </div>
            <ElDescriptions :column="2" border size="small">
              <ElDescriptionsItem label="患者姓名">{{ detail.patient_name || "-" }}</ElDescriptionsItem>
              <ElDescriptionsItem label="性别">{{ detail.gender || "-" }}</ElDescriptionsItem>
              <ElDescriptionsItem label="年龄">{{ detail.age != null ? `${detail.age} 岁` : "-" }}</ElDescriptionsItem>
              <ElDescriptionsItem label="联系电话">
                <div class="flex items-center gap-2">
                  <span>{{ detail.phone || "-" }}</span>
                  <ElButton link type="primary" size="small" @click="editPhone">编辑电话</ElButton>
                </div>
              </ElDescriptionsItem>
              <ElDescriptionsItem label="住院号">{{ detail.form_data?.inpatient_no || "-" }}</ElDescriptionsItem>
              <ElDescriptionsItem label="出院日期">{{ detail.form_data?.discharge_date || "-" }}</ElDescriptionsItem>
            </ElDescriptions>
          </div>

          <!-- 模块三：救治时间轴（节点时间线 + 关键质控指标，只读展示） -->
          <div class="mb-5">
            <div class="mb-2 flex items-center gap-2">
              <span class="i-ri:heart-pulse-line text-emerald-500" />
              <span class="text-sm font-semibold text-gray-700">救治时间轴</span>
              <ElTag v-if="detail.template_name" size="small" type="info" effect="plain">{{ detail.template_name }}</ElTag>
            </div>

            <!-- 关键质控指标卡片 -->
            <div v-if="timelineData?.metrics?.length" class="mb-3 grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-5">
              <div v-for="m in timelineData.metrics" :key="m.key" class="rounded-lg border border-gray-100 bg-gray-50 p-2.5">
                <div class="text-xs text-gray-400">{{ m.key }}</div>
                <div class="mt-0.5 text-base font-bold" :style="{ color: metricColor(m.status) }">
                  {{ m.minutes != null ? `${m.minutes} min` : "—" }}
                </div>
                <div class="mt-0.5 text-xs font-medium" :style="{ color: metricColor(m.status) }">{{ metricText(m.status) }}</div>
              </div>
            </div>

            <!-- 节点时间线 -->
            <ElTimeline v-if="timelineData?.nodes?.length" class="!pt-1">
              <ElTimelineItem
                v-for="n in timelineData.nodes"
                :key="n.code"
                :hollow="!n.value"
                :type="n.value ? 'primary' : 'info'"
                size="normal"
              >
                <div class="flex items-center justify-between">
                  <span class="text-sm text-gray-700">{{ n.name }}</span>
                  <span class="text-sm font-semibold" :class="n.value ? 'text-gray-900' : 'text-gray-400'">
                    {{ n.time || n.value || "未采集" }}
                  </span>
                </div>
              </ElTimelineItem>
            </ElTimeline>
            <ElEmpty v-else description="暂无时间轴数据" :image-size="50" />
          </div>

          <!-- 模块四：病例分析（质控指标校验 + 必填缺失清单） -->
          <div class="mb-5">
            <div class="mb-2 flex items-center gap-2">
              <span class="i-ri:file-chart-line text-indigo-500" />
              <span class="text-sm font-semibold text-gray-700">病例分析（质控指标校验）</span>
            </div>

            <div v-if="analysisData?.items?.length" class="space-y-2">
              <div
                v-for="m in analysisData.items"
                :key="m.key"
                class="rounded-lg border-l-4 bg-gray-50 p-2.5"
                :style="{ borderLeftColor: analysisColor(m.status) }"
              >
                <div class="flex items-center justify-between">
                  <span class="text-sm font-semibold text-gray-800">{{ m.name }}</span>
                  <span class="text-xs font-semibold" :style="{ color: analysisColor(m.status) }">{{ analysisLabel(m.status) }}</span>
                </div>
                <div class="mt-0.5 text-xs text-gray-400">{{ m.desc }}</div>
                <div class="mt-1 flex items-center justify-between text-xs">
                  <span class="text-gray-500">实际值：{{ m.minutes != null ? `${m.minutes} min` : "未采集" }}</span>
                  <span v-if="m.limit != null" class="text-gray-400">标准：≤{{ m.limit }} min</span>
                </div>
              </div>
            </div>

            <div v-if="analysisData?.missing_required?.length" class="mt-3 rounded-lg bg-rose-50 p-3">
              <div class="mb-1 text-xs font-semibold text-rose-600">缺失必填字段（请补录）</div>
              <div class="flex flex-wrap gap-1.5">
                <ElTag v-for="ms in analysisData.missing_required" :key="ms.field_code" type="danger" size="small" effect="light">
                  {{ ms.field_name }}
                </ElTag>
              </div>
            </div>
            <ElEmpty v-if="!analysisData?.items?.length" description="暂无分析数据" :image-size="50" />
          </div>

          <!-- 模块五：全部填报数据（字段字典自动渲染，三端统一） -->
          <div class="mb-5">
            <div class="mb-2 flex items-center gap-2">
              <span class="i-ri:list-check text-sky-500" />
              <span class="text-sm font-semibold text-gray-700">全部填报数据</span>
            </div>
            <!-- 文本字段：两列网格 -->
            <ElDescriptions v-if="textFields.length" :column="2" border size="small">
              <ElDescriptionsItem
                v-for="(f, idx) in textFields"
                :key="idx"
                :label="f.name"
                :span="f.long ? 2 : 1"
              >
                <span :class="{ 'whitespace-pre-wrap': f.long }">{{ f.value }}</span>
              </ElDescriptionsItem>
            </ElDescriptions>

            <!-- 图片字段：每个独立全宽卡片，真正"占一行" -->
            <div v-if="imageFields.length" :class="textFields.length ? 'mt-4' : ''" class="space-y-4">
              <div
                v-for="(f, idx) in imageFields"
                :key="`img-${idx}`"
                class="overflow-hidden rounded-lg border border-gray-100 bg-white"
              >
                <div class="border-b border-gray-100 bg-gray-50 px-4 py-2 text-sm font-semibold text-gray-700">
                  {{ f.name }}
                </div>
                <div class="p-4">
                  <img
                    v-if="f.value && f.value !== '-'"
                    :src="imageSrc(f.value)"
                    class="w-full cursor-zoom-in rounded-lg object-contain"
                    style="max-height: 320px"
                    :alt="f.name"
                    @click="openImage(imageSrc(f.value))"
                  />
                  <span v-else class="text-gray-400">无图片</span>
                </div>
              </div>
            </div>

            <ElEmpty v-if="!filledFields.length" description="该病例暂无填报数据" :image-size="60" />
          </div>

          <!-- 心电图 AI 诊断（图片 + AI 诊断 + 协同总结） -->
          <div class="mb-5">
            <div class="mb-2 flex items-center gap-2">
              <span class="i-ri:heart-pulse-line text-rose-500" />
              <span class="text-sm font-semibold text-gray-700">心电图 AI 诊断</span>
            </div>
            <div v-if="(detail?.ecg_records || []).length" class="space-y-4">
              <ElCard v-for="ecg in detail.ecg_records" :key="ecg.id" shadow="never" class="!border !border-gray-100">
                <div class="grid grid-cols-1 gap-3 md:grid-cols-2">
                  <div>
                    <div class="mb-1 text-xs text-gray-400">心电图图片</div>
                    <img v-if="ecg.image_path" :src="ecg.image_path" class="w-full rounded-lg border border-gray-100 object-contain" style="max-height: 320px" alt="心电图" />
                    <ElEmpty v-else description="无图片" :image-size="50" />
                  </div>
                  <div class="space-y-2">
                    <div>
                      <div class="text-xs text-gray-400">AI 诊断意见</div>
                      <div class="mt-1 whitespace-pre-wrap rounded-lg bg-gray-50 p-3 text-sm leading-relaxed text-gray-700">{{ ecg.ai_diagnosis || "-" }}</div>
                    </div>
                    <div>
                      <div class="text-xs text-gray-400">协同总结（发给接收方）</div>
                      <div class="mt-1 whitespace-pre-wrap rounded-lg bg-gray-50 p-3 text-sm leading-relaxed text-gray-700">{{ ecg.ai_summary || "-" }}</div>
                    </div>
                    <div v-if="ecg.feedback">
                      <div class="text-xs text-gray-400">接收方反馈</div>
                      <div class="mt-1 whitespace-pre-wrap rounded-lg bg-gray-50 p-3 text-sm leading-relaxed text-gray-700">{{ ecg.feedback }}</div>
                    </div>
                  </div>
                </div>
              </ElCard>
            </div>
            <ElEmpty v-else description="该病例暂无心电图记录" :image-size="60" />
          </div>

          <!-- 模块六：完整审核信息 -->
          <div>
            <div class="mb-2 flex items-center gap-2">
              <span class="i-ri:file-shield-line text-amber-500" />
              <span class="text-sm font-semibold text-gray-700">审核完整信息</span>
            </div>
            <div v-if="detail.audit_records.length" class="space-y-3">
              <ElCard v-for="a in detail.audit_records" :key="a.id" shadow="never" class="!border !border-gray-100">
                <div class="grid grid-cols-2 gap-x-4 gap-y-2 text-sm sm:grid-cols-4">
                  <div>
                    <div class="text-xs text-gray-400">审核人员</div>
                    <div class="mt-0.5 text-gray-700">{{ a.auditor_name || "-" }}</div>
                  </div>
                  <div>
                    <div class="text-xs text-gray-400">所属医院</div>
                    <div class="mt-0.5 text-gray-700">{{ a.auditor_hospital_name || "-" }}</div>
                  </div>
                  <div>
                    <div class="text-xs text-gray-400">审核时间</div>
                    <div class="mt-0.5 text-gray-700">{{ a.audit_time || "-" }}</div>
                  </div>
                  <div>
                    <div class="text-xs text-gray-400">审核结果</div>
                    <div class="mt-0.5">
                      <ElTag :type="a.audit_result === 'pass' ? 'success' : 'danger'" size="small">
                        {{ a.audit_result === "pass" ? "通过" : a.audit_result === "reject" ? "驳回" : a.audit_result || "-" }}
                      </ElTag>
                    </div>
                  </div>
                </div>
                <div class="mt-3">
                  <div class="text-xs text-gray-400">详细审核意见 / 驳回原因</div>
                  <div class="mt-1 whitespace-pre-wrap rounded-lg bg-gray-50 p-3 text-sm leading-relaxed text-gray-700">
                    {{ a.audit_comment || "（无审核意见）" }}
                  </div>
                </div>
              </ElCard>
            </div>
            <ElEmpty v-else description="该病例暂无审核记录" :image-size="60" />
          </div>
        </template>
      </div>

      <template #footer>
        <ElButton type="primary" @click="detailVisible = false">关闭</ElButton>
      </template>
    </ElDialog>

    <!-- 编辑电话弹窗（与 APP 端互通） -->
    <ElDialog
      v-model="editingPhone"
      title="编辑电话"
      width="420px"
      :close-on-click-modal="false"
      @closed="editingPhone = false"
    >
      <div class="text-sm text-gray-500">病例：{{ detail?.patient_name || "-" }}（{{ detail?.case_no || "-" }}）</div>
      <ElInput
        v-model="newPhone"
        class="mt-3"
        placeholder="请输入新电话号码"
        maxlength="20"
        @keyup.enter="savePhone"
      />
      <template #footer>
        <ElButton @click="editingPhone = false">取消</ElButton>
        <ElButton type="primary" :loading="savingPhone" @click="savePhone">保存</ElButton>
      </template>
    </ElDialog>
  </div>
</template>
