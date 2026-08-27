<!-- 病例数据管理（仅系统管理员）：医院卡片总览 ⇄ 医院病例列表 双视图 + 大尺寸只读详情弹窗 -->
<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import HospitalAPI, { type HospitalTable } from "@/api/cpx/hospital";
import CaseAPI, { type CaseDetail, type CaseTable } from "@/api/cpx/case";
import UserAPI, { type DoctorTable } from "@/api/cpx/user";

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

async function openDetail(row: CaseTable) {
  detailVisible.value = true;
  detailLoading.value = true;
  try {
    const res = await CaseAPI.detail(row.id);
    detail.value = res.data.data;
  } finally {
    detailLoading.value = false;
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

/** 按字段字典渲染 form_data 的非空字段（三端统一展示；无 field_dict 时回退模板字段） */
const filledFields = computed(() => {
  const fd = detail.value?.form_data || {};
  const dict = detail.value?.field_dict?.length ? detail.value.field_dict : detail.value?.template_fields;
  const rows: Array<{ name: string; value: string; long: boolean }> = [];
  const seen = new Set<string>();
  (dict || []).forEach((f) => {
    if (seen.has(f.field_code)) return;
    seen.add(f.field_code);
    // 住院号/出院日期已在"完整患者信息"模块展示，避免重复
    if (f.field_code === "inpatient_no" || f.field_code === "discharge_date") return;
    const raw = fd[f.field_code];
    if (raw === undefined || raw === null || raw === "") return;
    const v = String(raw);
    let val = v;
    if (f.field_type === "select" && Array.isArray(f.field_options)) {
      const opt = (f.field_options as Array<{ label?: string; value?: string } | string>).find((o) => {
        if (typeof o === "string") return o === v;
        return o.value === v;
      });
      if (opt && typeof opt === "object" && opt.label) val = opt.label;
    }
    rows.push({ name: f.field_name, value: val, long: v.length > 40 });
  });
  return rows;
});

const isLongText = (f: { field_code: string }) => {
  const v = detail.value?.form_data?.[f.field_code];
  return typeof v === "string" && v.length > 40;
};

onMounted(fetchHospitals);
</script>

<template>
  <div class="cpx-page p-4">
    <!-- ═══════════ 视图① 医院卡片总览 ═══════════ -->
    <template v-if="viewMode === 'overview'">
      <ElCard shadow="never" class="mb-4">
        <div class="flex flex-wrap items-center gap-3">
          <ElInput v-model="hospitalQuery.hospital_name" placeholder="医院名称" clearable class="w-48" @keyup.enter="handleHospitalSearch" />
          <ElSelect v-model="hospitalQuery.hospital_level" placeholder="医院等级" clearable class="w-32">
            <ElOption v-for="lv in LEVEL_OPTIONS" :key="lv" :label="lv" :value="lv" />
          </ElSelect>
          <ElSelect v-model="hospitalQuery.province" placeholder="所在地区" clearable class="w-32">
            <ElOption v-for="p in provinceOptions" :key="p" :label="p" :value="p" />
          </ElSelect>
          <ElSelect v-model="hospitalQuery.status" placeholder="医院状态" clearable class="w-28">
            <ElOption label="正常" :value="1" />
            <ElOption label="禁用" :value="0" />
          </ElSelect>
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
        <div class="mb-4 flex flex-wrap items-center gap-3">
          <ElInput
            v-model="caseQuery.case_no"
            placeholder="病例编号（完整精确/片段模糊）"
            clearable
            class="w-56"
            @keyup.enter="handleCaseSearch"
          />
          <ElInput v-model="caseQuery.doctor_name" placeholder="医生姓名" clearable class="w-32" @keyup.enter="handleCaseSearch" />
          <ElInput v-model="caseQuery.patient_name" placeholder="患者姓名" clearable class="w-32" @keyup.enter="handleCaseSearch" />
          <ElSelect v-model="caseQuery.doctor_id" placeholder="所属医生" clearable filterable class="w-36">
            <ElOption v-for="d in doctorOptions" :key="d.id" :label="d.real_name" :value="d.id" />
          </ElSelect>
          <ElDatePicker
            v-model="caseQuery.dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="提交开始时间"
            end-placeholder="提交结束时间"
            value-format="YYYY-MM-DD"
            class="!w-60"
          />
          <ElSelect v-model="caseQuery.status" placeholder="审核状态" clearable class="w-32">
            <ElOption v-for="s in STATUS_OPTIONS" :key="s.value" :label="s.label" :value="s.value" />
          </ElSelect>
          <ElButton type="primary" @click="handleCaseSearch">查询</ElButton>
          <ElButton @click="resetCaseQuery; fetchCases()">重置</ElButton>
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
      title="病例详情"
      width="920px"
      top="4vh"
      :close-on-click-modal="false"
      class="case-detail-dialog"
    >
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

          <!-- 模块三：救治过程（字段字典自动渲染，三端统一） -->
          <div class="mb-5">
            <div class="mb-2 flex items-center gap-2">
              <span class="i-ri:heart-pulse-line text-emerald-500" />
              <span class="text-sm font-semibold text-gray-700">救治过程时间轴（填报数据）</span>
              <ElTag v-if="detail.template_name" size="small" type="info" effect="plain">{{ detail.template_name }}</ElTag>
            </div>
            <ElDescriptions v-if="filledFields.length" :column="2" border size="small">
              <ElDescriptionsItem
                v-for="(f, idx) in filledFields"
                :key="idx"
                :label="f.name"
                :span="f.long ? 2 : 1"
              >
                <span :class="{ 'whitespace-pre-wrap': f.long }">{{ f.value }}</span>
              </ElDescriptionsItem>
            </ElDescriptions>
            <ElEmpty v-else description="该病例暂无填报数据" :image-size="60" />
          </div>

          <!-- 模块四：完整审核信息 -->
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
