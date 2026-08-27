<!-- 医院组织及人员管理（仅系统管理员）：医院卡片总览 + 医院人员管理 双视图 -->
<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from "element-plus";
import HospitalAPI, { type HospitalForm, type HospitalTable } from "@/api/cpx/hospital";
import UserAPI, {
  type AuditorForm,
  type AuditorTable,
  type DoctorForm,
  type DoctorTable,
} from "@/api/cpx/user";

defineOptions({ name: "CpxHospital" });

// ── 视图切换 ──────────────────────────────────────────
const viewMode = ref<"overview" | "members">("overview");
const currentHospital = ref<HospitalTable | null>(null);

// ── 医院卡片总览 ──────────────────────────────────────
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

/** 地区下拉：从已加载医院数据中提取去重省份 */
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

/** 进入该医院人员管理视图 */
function enterMembers(hospital: HospitalTable) {
  currentHospital.value = hospital;
  viewMode.value = "members";
  resetAuditorQuery();
  resetDoctorQuery();
  fetchAuditors();
  fetchDoctors();
}
function backToOverview() {
  viewMode.value = "overview";
  currentHospital.value = null;
  fetchHospitals();
}

// ── 医院弹窗（新增/修改/详情）────────────────────────
const hospitalDialog = reactive({ visible: false, title: "新增医院", mode: "create" as "create" | "edit" });
const hospitalDetailVisible = ref(false);
const detailData = ref<HospitalTable | null>(null);
const savingHospital = ref(false);
const hospitalFormRef = ref<FormInstance>();
const hospitalForm = reactive<HospitalForm>({
  hospital_name: "",
  hospital_level: "",
  province: "",
  city: "",
  address: "",
  contact_name: "",
  contact_phone: "",
  status: 1,
});
const hospitalRules: FormRules = {
  hospital_name: [{ required: true, message: "请输入医院名称", trigger: "blur" }],
  hospital_level: [{ required: true, message: "请选择医院等级", trigger: "change" }],
  province: [{ required: true, message: "请输入省", trigger: "blur" }],
  city: [{ required: true, message: "请输入市", trigger: "blur" }],
};

function openHospitalCreate() {
  hospitalDialog.mode = "create";
  hospitalDialog.title = "新增医院";
  Object.assign(hospitalForm, {
    id: undefined,
    hospital_name: "",
    hospital_level: "",
    province: "",
    city: "",
    address: "",
    contact_name: "",
    contact_phone: "",
    status: 1,
  });
  hospitalDialog.visible = true;
}
function openHospitalEdit(row: HospitalTable) {
  hospitalDialog.mode = "edit";
  hospitalDialog.title = "修改医院";
  Object.assign(hospitalForm, {
    id: row.id,
    hospital_name: row.hospital_name,
    hospital_level: row.hospital_level ?? "",
    province: row.province ?? "",
    city: row.city ?? "",
    address: row.address ?? "",
    contact_name: row.contact_name ?? "",
    contact_phone: row.contact_phone ?? "",
    status: row.status ?? 1,
  });
  hospitalDialog.visible = true;
}
async function openHospitalDetail(row: HospitalTable) {
  const res = await HospitalAPI.detail(row.id);
  detailData.value = res.data.data;
  hospitalDetailVisible.value = true;
}
async function saveHospital() {
  const valid = await hospitalFormRef.value?.validate().catch(() => false);
  if (!valid) return;
  savingHospital.value = true;
  try {
    if (hospitalDialog.mode === "edit" && hospitalForm.id) {
      await HospitalAPI.update(hospitalForm.id, { ...hospitalForm });
      ElMessage.success("修改成功");
    } else {
      await HospitalAPI.create({ ...hospitalForm });
      ElMessage.success("新增成功");
    }
    hospitalDialog.visible = false;
    fetchHospitals();
  } catch {
    // 错误已由拦截器提示
  } finally {
    savingHospital.value = false;
  }
}

async function toggleHospitalStatus(row: HospitalTable) {
  const action = row.status === 1 ? "禁用" : "启用";
  const tip =
    action === "禁用"
      ? "禁用后该院医生无法登录 APP、审核员无法进入审核系统，历史数据将保留。确定继续吗？"
      : "启用后该院恢复正常使用权限。确定继续吗？";
  try {
    await ElMessageBox.confirm(`确定要${action}医院「${row.hospital_name}」吗？\n${tip}`, "提示", {
      type: "warning",
      confirmButtonText: "确定",
      cancelButtonText: "取消",
    });
  } catch {
    return;
  }
  await HospitalAPI.batchStatus({ ids: [row.id], status: row.status === 1 ? 0 : 1 });
  ElMessage.success(`${action}成功`);
  fetchHospitals();
  if (currentHospital.value?.id === row.id) {
    currentHospital.value = { ...currentHospital.value, status: row.status === 1 ? 0 : 1 };
  }
}

// ── 人员视图：审核员 ──────────────────────────────────
const auditorLoading = ref(false);
const auditorList = ref<AuditorTable[]>([]);
const auditorTotal = ref(0);
const auditorQuery = reactive({
  page_no: 1,
  page_size: 10,
  real_name: "",
  phone: "",
  username: "",
  status: undefined as number | undefined,
});
function resetAuditorQuery() {
  Object.assign(auditorQuery, { page_no: 1, page_size: 10, real_name: "", phone: "", username: "", status: undefined });
}
async function fetchAuditors() {
  auditorLoading.value = true;
  try {
    const res = await UserAPI.listAuditors({
      page_no: auditorQuery.page_no,
      page_size: auditorQuery.page_size,
      hospital_id: currentHospital.value?.id,
      keyword: auditorQuery.real_name || auditorQuery.username || undefined,
      phone: auditorQuery.phone || undefined,
      status: auditorQuery.status,
    });
    auditorList.value = res.data.data.items;
    auditorTotal.value = res.data.data.total;
  } finally {
    auditorLoading.value = false;
  }
}
function handleAuditorSearch() {
  auditorQuery.page_no = 1;
  fetchAuditors();
}

// ── 人员视图：医生 ────────────────────────────────────
const doctorLoading = ref(false);
const doctorList = ref<DoctorTable[]>([]);
const doctorTotal = ref(0);
const doctorQuery = reactive({
  page_no: 1,
  page_size: 10,
  real_name: "",
  doctor_no: "",
  phone: "",
  department: "",
  title: "",
  status: undefined as number | undefined,
});
function resetDoctorQuery() {
  Object.assign(doctorQuery, {
    page_no: 1,
    page_size: 10,
    real_name: "",
    doctor_no: "",
    phone: "",
    department: "",
    title: "",
    status: undefined,
  });
}
async function fetchDoctors() {
  doctorLoading.value = true;
  try {
    const res = await UserAPI.listDoctors({
      page_no: doctorQuery.page_no,
      page_size: doctorQuery.page_size,
      hospital_id: currentHospital.value?.id,
      keyword: doctorQuery.real_name || doctorQuery.doctor_no || undefined,
      phone: doctorQuery.phone || undefined,
      department: doctorQuery.department || undefined,
      title: doctorQuery.title || undefined,
      status: doctorQuery.status,
    });
    doctorList.value = res.data.data.items;
    doctorTotal.value = res.data.data.total;
  } finally {
    doctorLoading.value = false;
  }
}
function handleDoctorSearch() {
  doctorQuery.page_no = 1;
  fetchDoctors();
}

// ── 人员表单弹窗（新增/修改，审核员与医生共用状态机）──
const personDialog = reactive({
  visible: false,
  kind: "auditor" as "auditor" | "doctor",
  mode: "create" as "create" | "edit",
  title: "",
});
const personSaving = ref(false);
const personFormRef = ref<FormInstance>();
const personForm = reactive<AuditorForm & DoctorForm>({
  id: undefined,
  username: "",
  password: "",
  real_name: "",
  phone: "",
  hospital_id: 0,
  doctor_no: "",
  department: "",
  title: "",
  audit_level: "",
  status: 1,
});
const personRules = computed<FormRules>(() => {
  const base: FormRules = {
    real_name: [{ required: true, message: "请输入姓名", trigger: "blur" }],
    username: [{ required: true, message: "请输入登录账号", trigger: "blur" }],
  };
  if (personDialog.mode === "create") {
    base.password = [{ required: true, message: "请输入初始密码", trigger: "blur" }];
  }
  if (personDialog.kind === "doctor") {
    base.doctor_no = [{ required: true, message: "请输入工号", trigger: "blur" }];
  }
  return base;
});

function openPersonCreate(kind: "auditor" | "doctor") {
  personDialog.kind = kind;
  personDialog.mode = "create";
  personDialog.title = kind === "auditor" ? "新增审核员" : "新增医生";
  Object.assign(personForm, {
    id: undefined,
    username: "",
    password: "",
    real_name: "",
    phone: "",
    hospital_id: currentHospital.value?.id,
    doctor_no: "",
    department: "",
    title: "",
    audit_level: "",
    status: 1,
  });
  personDialog.visible = true;
}
function openPersonEdit(row: AuditorTable | DoctorTable) {
  const isDoctor = personDialog.kind === "doctor" || "doctor_no" in row;
  personDialog.kind = isDoctor ? "doctor" : "auditor";
  personDialog.mode = "edit";
  personDialog.title = isDoctor ? "修改医生" : "修改审核员";
  Object.assign(personForm, {
    id: row.id,
    username: row.username,
    password: "",
    real_name: row.real_name,
    phone: row.phone ?? "",
    hospital_id: row.hospital_id,
    doctor_no: (row as DoctorTable).doctor_no ?? "",
    department: (row as DoctorTable).department ?? "",
    title: (row as DoctorTable).title ?? "",
    audit_level: (row as AuditorTable).audit_level ?? "",
    status: row.status ?? 1,
  });
  personDialog.visible = true;
}
async function savePerson() {
  const valid = await personFormRef.value?.validate().catch(() => false);
  if (!valid) return;
  personSaving.value = true;
  try {
    if (personDialog.kind === "auditor") {
      const body: AuditorForm = {
        username: personForm.username,
        real_name: personForm.real_name,
        phone: personForm.phone,
        hospital_id: personForm.hospital_id,
        audit_level: personForm.audit_level,
        status: personForm.status,
      };
      if (personDialog.mode === "edit" && personForm.id) {
        await UserAPI.updateAuditor(personForm.id, body);
      } else {
        body.password = personForm.password;
        await UserAPI.createAuditor(body);
      }
    } else {
      const body: DoctorForm = {
        username: personForm.username,
        real_name: personForm.real_name,
        phone: personForm.phone,
        hospital_id: personForm.hospital_id,
        doctor_no: personForm.doctor_no,
        department: personForm.department,
        title: personForm.title,
        status: personForm.status,
      };
      if (personDialog.mode === "edit" && personForm.id) {
        await UserAPI.updateDoctor(personForm.id, body);
      } else {
        body.password = personForm.password;
        await UserAPI.createDoctor(body);
      }
    }
    ElMessage.success(personDialog.mode === "edit" ? "修改成功" : "新增成功");
    personDialog.visible = false;
    personDialog.kind === "auditor" ? fetchAuditors() : fetchDoctors();
  } catch {
    // 错误已由拦截器提示
  } finally {
    personSaving.value = false;
  }
}

// ── 人员查看详情 ──────────────────────────────────────
const personDetailVisible = ref(false);
const personDetail = ref<AuditorTable | DoctorTable | null>(null);
function openPersonDetail(row: AuditorTable | DoctorTable) {
  personDetail.value = row;
  personDetailVisible.value = true;
}

// ── 重置密码 ──────────────────────────────────────────
const resetPwdVisible = ref(false);
const resetPwdSaving = ref(false);
const resetPwdTarget = ref<{ id: number; real_name: string; kind: string } | null>(null);
const resetPwdForm = reactive({ password: "", confirm: "" });
const resetPwdRef = ref<FormInstance>();
const resetPwdRules: FormRules = {
  password: [{ required: true, min: 6, message: "密码至少 6 位", trigger: "blur" }],
  confirm: [
    {
      validator: (_r, v, cb) => {
        if (v !== resetPwdForm.password) cb(new Error("两次输入的密码不一致"));
        else cb();
      },
      trigger: "blur",
    },
  ],
};
function openResetPwd(row: AuditorTable | DoctorTable) {
  resetPwdTarget.value = { id: row.id, real_name: row.real_name, kind: "doctor_no" in row ? "医生" : "审核员" };
  resetPwdForm.password = "";
  resetPwdForm.confirm = "";
  resetPwdVisible.value = true;
}
async function saveResetPwd() {
  const valid = await resetPwdRef.value?.validate().catch(() => false);
  if (!valid || !resetPwdTarget.value) return;
  resetPwdSaving.value = true;
  try {
    await UserAPI.resetPassword(resetPwdTarget.value.id, { password: resetPwdForm.password });
    ElMessage.success("重置密码成功");
    resetPwdVisible.value = false;
  } catch {
    // 错误已由拦截器提示
  } finally {
    resetPwdSaving.value = false;
  }
}

// ── 人员禁用/启用 ─────────────────────────────────────
async function togglePersonStatus(row: AuditorTable | DoctorTable) {
  const action = row.status === 1 ? "禁用" : "启用";
  try {
    await ElMessageBox.confirm(`确定要${action}「${row.real_name}」的账号吗？`, "提示", {
      type: "warning",
      confirmButtonText: "确定",
      cancelButtonText: "取消",
    });
  } catch {
    return;
  }
  await UserAPI.batchStatus({ ids: [row.id], status: row.status === 1 ? 0 : 1 });
  ElMessage.success(`${action}成功`);
  personDialog.kind === "auditor" ? fetchAuditors() : fetchDoctors();
}

// ── 人员表格列定义（复用）────────────────────────────
const statusTagType = (s?: number) => (s === 1 ? "success" : "info");

onMounted(fetchHospitals);
</script>

<template>
  <div class="cpx-page p-4">
    <!-- ═══════════ 视图① 医院卡片总览 ═══════════ -->
    <template v-if="viewMode === 'overview'">
      <ElCard shadow="never" class="mb-4">
        <div class="flex flex-wrap items-center gap-3">
          <ElInput
            v-model="hospitalQuery.hospital_name"
            placeholder="医院名称"
            clearable
            class="w-48"
            @keyup.enter="handleHospitalSearch"
          />
          <ElSelect v-model="hospitalQuery.hospital_level" placeholder="医院等级" clearable class="w-32">
            <ElOption v-for="lv in LEVEL_OPTIONS" :key="lv" :label="lv" :value="lv" />
          </ElSelect>
          <ElSelect v-model="hospitalQuery.province" placeholder="地区" clearable class="w-32">
            <ElOption v-for="p in provinceOptions" :key="p" :label="p" :value="p" />
          </ElSelect>
          <ElSelect v-model="hospitalQuery.status" placeholder="状态" clearable class="w-28">
            <ElOption label="正常" :value="1" />
            <ElOption label="禁用" :value="0" />
          </ElSelect>
          <ElButton type="primary" @click="handleHospitalSearch">查询</ElButton>
          <ElButton @click="handleHospitalReset">重置</ElButton>
          <div class="flex-1" />
          <ElButton type="primary" @click="openHospitalCreate">
            <span class="i-ri:add-line mr-1" />新增医院
          </ElButton>
        </div>
      </ElCard>

      <!-- 医院卡片流 -->
      <div v-loading="hospitalLoading" class="min-h-40">
        <ElEmpty v-if="!hospitalLoading && hospitalList.length === 0" description="暂无医院数据" />
        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-4">
          <div
            v-for="h in hospitalList"
            :key="h.id"
            class="group cursor-pointer rounded-xl bg-white shadow-sm ring-1 ring-black/5 transition-all hover:-translate-y-0.5 hover:shadow-md"
            :class="{ 'opacity-60 saturate-50': h.status !== 1 }"
            @click="enterMembers(h)"
          >
            <!-- 卡片头部：名称 + 状态 -->
            <div class="flex items-start justify-between gap-2 border-b border-gray-100 px-4 py-3">
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

            <!-- 统计数据 -->
            <div class="grid grid-cols-3 gap-2 px-4 py-4">
              <div class="rounded-lg bg-sky-50 py-2.5 text-center">
                <div class="text-xl font-bold text-sky-600">{{ h.doctor_count ?? 0 }}</div>
                <div class="mt-0.5 text-xs text-gray-400">医生</div>
              </div>
              <div class="rounded-lg bg-violet-50 py-2.5 text-center">
                <div class="text-xl font-bold text-violet-600">{{ h.auditor_count ?? 0 }}</div>
                <div class="mt-0.5 text-xs text-gray-400">审核员</div>
              </div>
              <div class="rounded-lg bg-emerald-50 py-2.5 text-center">
                <div class="text-xl font-bold text-emerald-600">{{ h.case_count ?? 0 }}</div>
                <div class="mt-0.5 text-xs text-gray-400">病例</div>
              </div>
            </div>

            <!-- 操作按钮 -->
            <div class="flex items-center justify-around border-t border-gray-100 py-2">
              <ElButton link type="primary" size="small" @click.stop="openHospitalDetail(h)">
                <span class="i-ri:eye-line mr-1" />查看详情
              </ElButton>
              <ElButton link type="primary" size="small" @click.stop="openHospitalEdit(h)">
                <span class="i-ri:edit-line mr-1" />修改
              </ElButton>
              <ElButton link :type="h.status === 1 ? 'danger' : 'success'" size="small" @click.stop="toggleHospitalStatus(h)">
                {{ h.status === 1 ? "禁用" : "启用" }}
              </ElButton>
            </div>
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

    <!-- ═══════════ 视图② 医院人员管理 ═══════════ -->
    <template v-else>
      <ElCard shadow="never" class="mb-4">
        <div class="flex flex-wrap items-center gap-4">
          <ElButton @click="backToOverview">
            <span class="i-ri:arrow-left-line mr-1" />返回医院总览
          </ElButton>
          <div class="flex min-w-0 items-center gap-3">
            <span class="i-ri:hospital-line text-2xl text-blue-500" />
            <div class="min-w-0">
              <div class="flex items-center gap-2">
                <span class="truncate text-base font-bold text-gray-700">{{ currentHospital?.hospital_name }}</span>
                <ElTag v-if="currentHospital" :type="currentHospital.status === 1 ? 'success' : 'info'" size="small">
                  {{ currentHospital.status === 1 ? "正常" : "禁用" }}
                </ElTag>
              </div>
              <div class="mt-0.5 text-xs text-gray-400">
                {{ currentHospital?.hospital_level }} · {{ currentHospital?.province }}{{ currentHospital?.city }}
                <span v-if="currentHospital?.status !== 1" class="text-red-400">（医院已禁用，人员无法登录）</span>
              </div>
            </div>
          </div>
        </div>
      </ElCard>

      <ElCard shadow="never">
        <ElTabs v-model="personDialog.kind" type="border-card" class="!shadow-none">
          <!-- ── 审核员 Tab ── -->
          <ElTabPane label="审核员" name="auditor">
            <div class="mb-4 flex flex-wrap items-center gap-3">
              <ElInput v-model="auditorQuery.real_name" placeholder="姓名" clearable class="w-36" @keyup.enter="handleAuditorSearch" />
              <ElInput v-model="auditorQuery.phone" placeholder="手机号" clearable class="w-40" @keyup.enter="handleAuditorSearch" />
              <ElInput v-model="auditorQuery.username" placeholder="登录账号" clearable class="w-40" @keyup.enter="handleAuditorSearch" />
              <ElSelect v-model="auditorQuery.status" placeholder="账号状态" clearable class="w-28">
                <ElOption label="正常" :value="1" />
                <ElOption label="禁用" :value="0" />
              </ElSelect>
              <ElButton type="primary" @click="handleAuditorSearch">查询</ElButton>
              <ElButton @click="resetAuditorQuery; fetchAuditors()">重置</ElButton>
              <div class="flex-1" />
              <ElButton type="primary" @click="openPersonCreate('auditor')">
                <span class="i-ri:user-add-line mr-1" />新增审核员
              </ElButton>
            </div>

            <ElTable v-loading="auditorLoading" :data="auditorList" border stripe>
              <ElTableColumn type="index" label="#" width="55" />
              <ElTableColumn prop="real_name" label="姓名" min-width="110" />
              <ElTableColumn prop="phone" label="手机号" min-width="130" />
              <ElTableColumn prop="username" label="登录账号" min-width="130" />
              <ElTableColumn prop="status" label="账号状态" width="100" align="center">
                <template #default="{ row }">
                  <ElTag :type="statusTagType((row as AuditorTable).status)" size="small">
                    {{ (row as AuditorTable).status === 1 ? "正常" : "禁用" }}
                  </ElTag>
                </template>
              </ElTableColumn>
              <ElTableColumn label="操作" width="240" fixed="right">
                <template #default="{ row }">
                  <ElButton link type="primary" size="small" @click="openPersonDetail(row as AuditorTable)">查看</ElButton>
                  <ElButton link type="primary" size="small" @click="openPersonEdit(row as AuditorTable)">修改</ElButton>
                  <ElButton link type="warning" size="small" @click="openResetPwd(row as AuditorTable)">重置密码</ElButton>
                  <ElButton
                    link
                    :type="(row as AuditorTable).status === 1 ? 'danger' : 'success'"
                    size="small"
                    @click="togglePersonStatus(row as AuditorTable)"
                  >
                    {{ (row as AuditorTable).status === 1 ? "禁用" : "启用" }}
                  </ElButton>
                </template>
              </ElTableColumn>
            </ElTable>
            <div class="mt-3 flex justify-end">
              <ElPagination
                v-model:current-page="auditorQuery.page_no"
                v-model:page-size="auditorQuery.page_size"
                :total="auditorTotal"
                :page-sizes="[10, 20, 50]"
                layout="total, sizes, prev, pager, next"
                @current-change="fetchAuditors"
                @size-change="handleAuditorSearch"
              />
            </div>
          </ElTabPane>

          <!-- ── 医生 Tab ── -->
          <ElTabPane label="医生" name="doctor">
            <div class="mb-4 flex flex-wrap items-center gap-3">
              <ElInput v-model="doctorQuery.real_name" placeholder="姓名" clearable class="w-32" @keyup.enter="handleDoctorSearch" />
              <ElInput v-model="doctorQuery.doctor_no" placeholder="工号" clearable class="w-32" @keyup.enter="handleDoctorSearch" />
              <ElInput v-model="doctorQuery.phone" placeholder="手机号" clearable class="w-36" @keyup.enter="handleDoctorSearch" />
              <ElInput v-model="doctorQuery.department" placeholder="科室" clearable class="w-32" @keyup.enter="handleDoctorSearch" />
              <ElInput v-model="doctorQuery.title" placeholder="职称" clearable class="w-32" @keyup.enter="handleDoctorSearch" />
              <ElSelect v-model="doctorQuery.status" placeholder="账号状态" clearable class="w-28">
                <ElOption label="正常" :value="1" />
                <ElOption label="禁用" :value="0" />
              </ElSelect>
              <ElButton type="primary" @click="handleDoctorSearch">查询</ElButton>
              <ElButton @click="resetDoctorQuery; fetchDoctors()">重置</ElButton>
              <div class="flex-1" />
              <ElButton type="primary" @click="openPersonCreate('doctor')">
                <span class="i-ri:user-add-line mr-1" />新增医生
              </ElButton>
            </div>

            <ElTable v-loading="doctorLoading" :data="doctorList" border stripe>
              <ElTableColumn type="index" label="#" width="55" />
              <ElTableColumn prop="real_name" label="姓名" min-width="100" />
              <ElTableColumn prop="doctor_no" label="工号" min-width="100" />
              <ElTableColumn prop="phone" label="手机号" min-width="120" />
              <ElTableColumn prop="department" label="科室" min-width="110" />
              <ElTableColumn prop="title" label="职称" min-width="100" />
              <ElTableColumn prop="username" label="登录账号" min-width="120" />
              <ElTableColumn prop="status" label="账号状态" width="100" align="center">
                <template #default="{ row }">
                  <ElTag :type="statusTagType((row as DoctorTable).status)" size="small">
                    {{ (row as DoctorTable).status === 1 ? "正常" : "禁用" }}
                  </ElTag>
                </template>
              </ElTableColumn>
              <ElTableColumn label="操作" width="240" fixed="right">
                <template #default="{ row }">
                  <ElButton link type="primary" size="small" @click="openPersonDetail(row as DoctorTable)">查看</ElButton>
                  <ElButton link type="primary" size="small" @click="openPersonEdit(row as DoctorTable)">修改</ElButton>
                  <ElButton link type="warning" size="small" @click="openResetPwd(row as DoctorTable)">重置密码</ElButton>
                  <ElButton
                    link
                    :type="(row as DoctorTable).status === 1 ? 'danger' : 'success'"
                    size="small"
                    @click="togglePersonStatus(row as DoctorTable)"
                  >
                    {{ (row as DoctorTable).status === 1 ? "禁用" : "启用" }}
                  </ElButton>
                </template>
              </ElTableColumn>
            </ElTable>
            <div class="mt-3 flex justify-end">
              <ElPagination
                v-model:current-page="doctorQuery.page_no"
                v-model:page-size="doctorQuery.page_size"
                :total="doctorTotal"
                :page-sizes="[10, 20, 50]"
                layout="total, sizes, prev, pager, next"
                @current-change="fetchDoctors"
                @size-change="handleDoctorSearch"
              />
            </div>
          </ElTabPane>
        </ElTabs>
      </ElCard>
    </template>

    <!-- ═══════════ 弹窗 ═══════════ -->

    <!-- 新增/修改医院 -->
    <ElDialog v-model="hospitalDialog.visible" :title="hospitalDialog.title" width="560px">
      <ElForm ref="hospitalFormRef" :model="hospitalForm" :rules="hospitalRules" label-width="90px">
        <ElFormItem label="医院名称" prop="hospital_name">
          <ElInput v-model="hospitalForm.hospital_name" placeholder="请输入医院名称" />
        </ElFormItem>
        <ElFormItem label="医院等级" prop="hospital_level">
          <ElSelect v-model="hospitalForm.hospital_level" placeholder="请选择" class="w-full">
            <ElOption v-for="lv in LEVEL_OPTIONS" :key="lv" :label="lv" :value="lv" />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="所在地区" prop="province">
          <div class="flex w-full gap-2">
            <ElInput v-model="hospitalForm.province" placeholder="省" />
            <ElInput v-model="hospitalForm.city" placeholder="市" />
          </div>
        </ElFormItem>
        <ElFormItem label="详细地址">
          <ElInput v-model="hospitalForm.address" placeholder="请输入详细地址" />
        </ElFormItem>
        <ElFormItem label="联系人">
          <ElInput v-model="hospitalForm.contact_name" placeholder="请输入联系人" />
        </ElFormItem>
        <ElFormItem label="联系电话">
          <ElInput v-model="hospitalForm.contact_phone" placeholder="请输入联系电话" />
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="hospitalDialog.visible = false">取消</ElButton>
        <ElButton type="primary" :loading="savingHospital" @click="saveHospital">确定</ElButton>
      </template>
    </ElDialog>

    <!-- 查看医院详情（只读） -->
    <ElDialog v-model="hospitalDetailVisible" title="医院详情" width="520px">
      <ElDescriptions v-if="detailData" :column="1" border>
        <ElDescriptionsItem label="医院名称">{{ detailData.hospital_name }}</ElDescriptionsItem>
        <ElDescriptionsItem label="医院等级">{{ detailData.hospital_level || "-" }}</ElDescriptionsItem>
        <ElDescriptionsItem label="所在地区">{{ detailData.province }} {{ detailData.city }}</ElDescriptionsItem>
        <ElDescriptionsItem label="详细地址">{{ detailData.address || "-" }}</ElDescriptionsItem>
        <ElDescriptionsItem label="联系人">{{ detailData.contact_name || "-" }}</ElDescriptionsItem>
        <ElDescriptionsItem label="联系电话">{{ detailData.contact_phone || "-" }}</ElDescriptionsItem>
        <ElDescriptionsItem label="状态">
          <ElTag :type="detailData.status === 1 ? 'success' : 'info'" size="small">
            {{ detailData.status === 1 ? "正常" : "禁用" }}
          </ElTag>
        </ElDescriptionsItem>
        <ElDescriptionsItem label="统计数据">
          <span class="text-sky-600">医生 {{ detailData.doctor_count ?? 0 }}</span>
          <span class="mx-2 text-violet-600">审核员 {{ detailData.auditor_count ?? 0 }}</span>
          <span class="text-emerald-600">病例 {{ detailData.case_count ?? 0 }}</span>
        </ElDescriptionsItem>
      </ElDescriptions>
    </ElDialog>

    <!-- 新增/修改人员（审核员/医生） -->
    <ElDialog v-model="personDialog.visible" :title="personDialog.title" width="520px">
      <ElForm ref="personFormRef" :model="personForm" :rules="personRules" label-width="90px">
        <ElFormItem label="姓名" prop="real_name">
          <ElInput v-model="personForm.real_name" placeholder="请输入姓名" />
        </ElFormItem>
        <ElFormItem v-if="personDialog.kind === 'doctor'" label="工号" prop="doctor_no">
          <ElInput v-model="personForm.doctor_no" placeholder="请输入工号" />
        </ElFormItem>
        <ElFormItem label="手机号">
          <ElInput v-model="personForm.phone" placeholder="请输入手机号" />
        </ElFormItem>
        <ElFormItem v-if="personDialog.kind === 'doctor'" label="科室">
          <ElInput v-model="personForm.department" placeholder="请输入科室" />
        </ElFormItem>
        <ElFormItem v-if="personDialog.kind === 'doctor'" label="职称">
          <ElInput v-model="personForm.title" placeholder="请输入职称" />
        </ElFormItem>
        <ElFormItem label="登录账号" prop="username">
          <ElInput v-model="personForm.username" placeholder="请输入登录账号" :disabled="personDialog.mode === 'edit'" />
        </ElFormItem>
        <ElFormItem v-if="personDialog.mode === 'create'" label="初始密码" prop="password">
          <ElInput v-model="personForm.password" type="password" show-password placeholder="请输入初始密码" />
        </ElFormItem>
        <ElFormItem v-if="personDialog.mode === 'edit'" label="账号状态">
          <ElRadioGroup v-model="personForm.status">
            <ElRadio :value="1">正常</ElRadio>
            <ElRadio :value="0">禁用</ElRadio>
          </ElRadioGroup>
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="personDialog.visible = false">取消</ElButton>
        <ElButton type="primary" :loading="personSaving" @click="savePerson">确定</ElButton>
      </template>
    </ElDialog>

    <!-- 人员查看详情（只读） -->
    <ElDialog v-model="personDetailVisible" title="人员详情" width="480px">
      <ElDescriptions v-if="personDetail" :column="1" border>
        <ElDescriptionsItem label="姓名">{{ personDetail.real_name }}</ElDescriptionsItem>
        <ElDescriptionsItem label="登录账号">{{ personDetail.username }}</ElDescriptionsItem>
        <ElDescriptionsItem label="手机号">{{ personDetail.phone || "-" }}</ElDescriptionsItem>
        <ElDescriptionsItem v-if="'doctor_no' in personDetail" label="工号">{{ (personDetail as DoctorTable).doctor_no || "-" }}</ElDescriptionsItem>
        <ElDescriptionsItem v-if="'doctor_no' in personDetail" label="科室">{{ (personDetail as DoctorTable).department || "-" }}</ElDescriptionsItem>
        <ElDescriptionsItem v-if="'doctor_no' in personDetail" label="职称">{{ (personDetail as DoctorTable).title || "-" }}</ElDescriptionsItem>
        <ElDescriptionsItem v-if="'audit_level' in personDetail" label="审核权限">{{ (personDetail as AuditorTable).audit_level || "-" }}</ElDescriptionsItem>
        <ElDescriptionsItem label="所属医院">{{ personDetail.hospital_name || "-" }}</ElDescriptionsItem>
        <ElDescriptionsItem label="账号状态">
          <ElTag :type="personDetail.status === 1 ? 'success' : 'info'" size="small">
            {{ personDetail.status === 1 ? "正常" : "禁用" }}
          </ElTag>
        </ElDescriptionsItem>
      </ElDescriptions>
    </ElDialog>

    <!-- 重置密码 -->
    <ElDialog v-model="resetPwdVisible" title="重置密码" width="440px">
      <p class="mb-3 text-sm text-gray-500">
        为{{ resetPwdTarget?.kind }}「{{ resetPwdTarget?.real_name }}」设置新密码（至少 6 位）
      </p>
      <ElForm ref="resetPwdRef" :model="resetPwdForm" :rules="resetPwdRules" label-width="80px">
        <ElFormItem label="新密码" prop="password">
          <ElInput v-model="resetPwdForm.password" type="password" show-password placeholder="请输入新密码" />
        </ElFormItem>
        <ElFormItem label="确认密码" prop="confirm">
          <ElInput v-model="resetPwdForm.confirm" type="password" show-password placeholder="请再次输入新密码" />
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="resetPwdVisible = false">取消</ElButton>
        <ElButton type="primary" :loading="resetPwdSaving" @click="saveResetPwd">确定</ElButton>
      </template>
    </ElDialog>
  </div>
</template>
