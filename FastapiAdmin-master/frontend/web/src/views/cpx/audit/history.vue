<!-- 审核记录：病例编号查询 + 查看详情弹窗 + 修改（审核结果/意见） -->
<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import AuditAPI, { type AuditHistoryItem } from "@/api/cpx/audit";
import CaseDetailDialog from "./components/CaseDetailDialog.vue";

defineOptions({ name: "CpxAuditHistory" });

const loading = ref(false);
const data = ref<AuditHistoryItem[]>([]);
const total = ref(0);
const query = reactive({ page_no: 1, page_size: 10, case_no: "" });

async function fetchData() {
  loading.value = true;
  try {
    const res = await AuditAPI.history({
      page_no: query.page_no,
      page_size: query.page_size,
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
  query.case_no = "";
  query.page_no = 1;
  fetchData();
}

// ── 查看详情弹窗 ──────────────────────────────────────
const detailVisible = ref(false);
const detailCaseId = ref<number | null>(null);
function openDetail(row: AuditHistoryItem) {
  detailCaseId.value = row.case_id;
  detailVisible.value = true;
}

// ── 修改审核记录 ──────────────────────────────────────
const editVisible = ref(false);
const editRow = ref<AuditHistoryItem | null>(null);
const editResult = ref<"pass" | "reject">("pass");
const editComment = ref("");
const submitting = ref(false);

function openEdit(row: AuditHistoryItem) {
  editRow.value = row;
  editResult.value = row.audit_result === "pass" ? "pass" : "reject";
  editComment.value = row.audit_comment || "";
  editVisible.value = true;
}

async function submitEdit() {
  if (!editRow.value) return;
  if (editResult.value === "reject" && !editComment.value.trim()) {
    ElMessage.warning("驳回时必须填写驳回原因");
    return;
  }
  submitting.value = true;
  try {
    await AuditAPI.updateRecord(editRow.value.id, {
      audit_result: editResult.value,
      audit_comment: editComment.value.trim() || undefined,
    });
    ElMessage.success("审核记录已更新");
    editVisible.value = false;
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
      <div class="mb-4 flex flex-wrap items-center gap-3">
        <ElInput v-model="query.case_no" placeholder="病例编号（支持完整/片段检索）" clearable class="w-60" @keyup.enter="handleSearch" />
        <ElButton type="primary" @click="handleSearch">查询</ElButton>
        <ElButton @click="handleReset">重置</ElButton>
        <div class="flex-1" />
        <ElTag type="info" effect="light">共 {{ total }} 条审核记录</ElTag>
      </div>

      <ElTable v-loading="loading" :data="data" border stripe>
        <ElTableColumn type="index" label="#" width="55" />
        <ElTableColumn prop="case_no" label="病例编号" width="170" />
        <ElTableColumn prop="patient_name" label="患者姓名" width="110" />
        <ElTableColumn prop="auditor_name" label="审核员" width="110" />
        <ElTableColumn prop="audit_result" label="审核结果" width="100" align="center">
          <template #default="{ row }">
            <ElTag :type="row.audit_result === 'pass' ? 'success' : 'danger'">
              {{ row.audit_result === "pass" ? "通过" : "驳回" }}
            </ElTag>
          </template>
        </ElTableColumn>
        <ElTableColumn prop="audit_comment" label="审核意见" min-width="180" show-overflow-tooltip />
        <ElTableColumn prop="audit_time" label="审核时间" width="170" />
        <ElTableColumn label="操作" width="130" fixed="right">
          <template #default="scope">
            <ElButton link type="primary" size="small" @click="openDetail(scope.row as AuditHistoryItem)">查看</ElButton>
            <ElButton link type="warning" size="small" @click="openEdit(scope.row as AuditHistoryItem)">修改</ElButton>
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

    <!-- 修改审核记录弹窗 -->
    <ElDialog v-model="editVisible" title="修改审核记录" width="520px" :close-on-click-modal="false">
      <div v-if="editRow" class="mb-4 rounded-lg bg-gray-50 p-3 text-sm">
        <div class="flex items-center gap-2">
          <span class="font-medium text-gray-700">{{ editRow.patient_name }}</span>
          <span class="text-gray-400">·</span>
          <span class="text-gray-500">{{ editRow.case_no }}</span>
          <span class="text-gray-400">·</span>
          <span class="text-gray-500">审核员：{{ editRow.auditor_name || "-" }}</span>
          <span class="text-gray-400">·</span>
          <span class="text-gray-500">{{ editRow.audit_time }}</span>
        </div>
      </div>

      <ElForm label-width="90px">
        <ElFormItem label="审核结果" required>
          <ElRadioGroup v-model="editResult">
            <ElRadio value="pass">审核通过</ElRadio>
            <ElRadio value="reject">审核驳回</ElRadio>
          </ElRadioGroup>
        </ElFormItem>
        <ElFormItem label="审核意见">
          <ElInput
            v-model="editComment"
            type="textarea"
            :rows="4"
            maxlength="500"
            show-word-limit
            :placeholder="editResult === 'reject' ? '请输入驳回原因（必填）' : '请输入审核意见（选填）'"
          />
        </ElFormItem>
      </ElForm>

      <template #footer>
        <ElButton @click="editVisible = false">取消</ElButton>
        <ElButton type="primary" :loading="submitting" @click="submitEdit">保存修改</ElButton>
      </template>
    </ElDialog>
  </div>
</template>
