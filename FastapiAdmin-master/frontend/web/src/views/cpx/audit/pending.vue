<!-- 待审核病例列表：编号/姓名查询 + 查看详情弹窗 + 修改（审核通过/驳回） -->
<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import AuditAPI, { type PendingCaseItem } from "@/api/cpx/audit";
import CaseDetailDialog from "./components/CaseDetailDialog.vue";
import FaSearchInput from "@/components/forms/fa-search-input/index.vue";
import FaSearchItem from "@/components/forms/fa-search-item/index.vue";

defineOptions({ name: "CpxAuditPending" });

const loading = ref(false);
const data = ref<PendingCaseItem[]>([]);
const total = ref(0);
const query = reactive({ page_no: 1, page_size: 10, keyword: "", case_no: "" });

async function fetchData() {
  loading.value = true;
  try {
    const res = await AuditAPI.pending({
      page_no: query.page_no,
      page_size: query.page_size,
      keyword: query.keyword || undefined,
      case_no: query.case_no || undefined,
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
  query.keyword = "";
  query.case_no = "";
  query.page_no = 1;
  fetchData();
}

// ── 查看详情弹窗 ──────────────────────────────────────
const detailVisible = ref(false);
const detailCaseId = ref<number | null>(null);
function openDetail(row: PendingCaseItem) {
  detailCaseId.value = row.id;
  detailVisible.value = true;
}

// ── 修改（审核处理：通过/驳回）────────────────────────
const auditVisible = ref(false);
const auditCase = ref<PendingCaseItem | null>(null);
const auditResult = ref<"pass" | "reject">("pass");
const auditComment = ref("");
const submitting = ref(false);

function openAudit(row: PendingCaseItem) {
  auditCase.value = row;
  auditResult.value = "pass";
  auditComment.value = "";
  auditVisible.value = true;
}

async function submitAudit() {
  if (!auditCase.value) return;
  if (auditResult.value === "reject" && !auditComment.value.trim()) {
    ElMessage.warning("驳回时必须填写驳回原因");
    return;
  }
  submitting.value = true;
  try {
    if (auditResult.value === "pass") {
      await AuditAPI.approve({ case_id: auditCase.value.id, audit_comment: auditComment.value || undefined });
      ElMessage.success("审核通过");
    } else {
      await AuditAPI.reject({ case_id: auditCase.value.id, audit_comment: auditComment.value.trim() });
      ElMessage.success("已驳回");
    }
    auditVisible.value = false;
    fetchData();
  } finally {
    submitting.value = false;
  }
}

onMounted(fetchData);
</script>

<template>
  <div class="cpx-page p-4">
    <ElCard shadow="never">
      <!-- 搜索筛选区 -->
      <div class="mb-4 flex flex-wrap items-center gap-x-4 gap-y-3">
        <FaSearchItem label="患者姓名">
          <FaSearchInput v-model="query.keyword" placeholder="患者姓名" clearable class="w-44" @keyup.enter="handleSearch" />
        </FaSearchItem>
        <FaSearchItem label="病例编号">
          <FaSearchInput v-model="query.case_no" placeholder="病例编号" clearable class="w-56" @keyup.enter="handleSearch" />
        </FaSearchItem>
        <ElButton type="primary" @click="handleSearch">查询</ElButton>
        <ElButton @click="handleReset">重置</ElButton>
        <div class="flex-1" />
        <ElTag type="warning" effect="light">待审核 {{ total }} 例</ElTag>
      </div>

      <ElTable v-loading="loading" :data="data" border stripe>
        <ElTableColumn type="index" label="#" width="55" />
        <ElTableColumn prop="case_no" label="病例编号" width="170" />
        <ElTableColumn prop="patient_name" label="患者姓名" width="110" />
        <ElTableColumn prop="gender" label="性别" width="70" align="center" />
        <ElTableColumn prop="age" label="年龄" width="70" align="center" />
        <ElTableColumn prop="doctor_name" label="提交医生" width="110" />
        <ElTableColumn prop="create_time" label="提交时间" width="170" />
        <ElTableColumn label="操作" width="150" fixed="right">
          <template #default="scope">
            <ElButton link type="primary" size="small" @click="openDetail(scope.row as PendingCaseItem)">查看</ElButton>
            <ElButton link type="warning" size="small" @click="openAudit(scope.row as PendingCaseItem)">修改</ElButton>
          </template>
        </ElTableColumn>
      </ElTable>

      <div class="mt-4 flex justify-end">
        <ElPagination
          v-model:current-page="query.page_no"
          v-model:page-size="query.page_size"
          :total="total"
          layout="total, prev, pager, next"
          @current-change="fetchData"
        />
      </div>
    </ElCard>

    <!-- 查看详情弹窗 -->
    <CaseDetailDialog v-model="detailVisible" :case-id="detailCaseId" />

    <!-- 修改（审核处理）弹窗 -->
    <ElDialog v-model="auditVisible" title="病例审核" width="520px" :close-on-click-modal="false">
      <div v-if="auditCase" class="mb-4 rounded-lg bg-gray-50 p-3 text-sm">
        <div class="flex items-center gap-2">
          <span class="font-medium text-gray-700">{{ auditCase.patient_name }}</span>
          <span class="text-gray-400">·</span>
          <span class="text-gray-500">{{ auditCase.case_no }}</span>
          <span class="text-gray-400">·</span>
          <span class="text-gray-500">提交医生：{{ auditCase.doctor_name || "-" }}</span>
        </div>
      </div>

      <ElForm label-width="90px">
        <ElFormItem label="审核结果" required>
          <ElRadioGroup v-model="auditResult">
            <ElRadio value="pass">审核通过</ElRadio>
            <ElRadio value="reject">审核驳回</ElRadio>
          </ElRadioGroup>
        </ElFormItem>
        <ElFormItem label="审核意见">
          <ElInput
            v-model="auditComment"
            type="textarea"
            :rows="4"
            maxlength="500"
            show-word-limit
            :placeholder="auditResult === 'reject' ? '请输入驳回原因（必填）' : '请输入审核意见（选填）'"
          />
        </ElFormItem>
      </ElForm>

      <template #footer>
        <ElButton @click="auditVisible = false">取消</ElButton>
        <ElButton type="primary" :loading="submitting" @click="submitAudit">确认提交</ElButton>
      </template>
    </ElDialog>
  </div>
</template>
