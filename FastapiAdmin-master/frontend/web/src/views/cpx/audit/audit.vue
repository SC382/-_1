<!-- 病例审核详情与操作 -->
<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import AuditAPI, { type AuditDetail } from "@/api/cpx/audit";

defineOptions({ name: "CpxAuditDetail" });

const route = useRoute();
const router = useRouter();

const loading = ref(false);
const detail = ref<AuditDetail | null>(null);
const approving = ref(false);

const FIELD_TYPE_LABEL: Record<string, string> = {
  text: "文本",
  number: "数字",
  date: "日期",
  time: "时间",
  datetime: "日期时间",
  select: "选择",
};

async function fetchDetail() {
  const caseId = Number(route.query.case_id);
  if (!caseId) return;
  loading.value = true;
  try {
    const res = await AuditAPI.detail(caseId);
    detail.value = res.data.data;
  } finally {
    loading.value = false;
  }
}

async function approve() {
  const { value } = await ElMessageBox.prompt("可填写审核意见（选填）", "审核通过", {
    inputPlaceholder: "审核意见",
    confirmButtonText: "确认通过",
    cancelButtonText: "取消",
  }).catch(() => ({ value: undefined }));
  approving.value = true;
  try {
    await AuditAPI.approve({ case_id: detail.value!.id, audit_comment: value || undefined });
    ElMessage.success("审核通过");
    router.push("/cpx/audit/pending");
  } finally {
    approving.value = false;
  }
}

async function reject() {
  const { value } = await ElMessageBox.prompt("请输入驳回原因（必填）", "审核驳回", {
    inputPlaceholder: "驳回原因",
    inputValidator: (v: string) => (v && v.trim() ? true : "驳回原因必填"),
    confirmButtonText: "确认驳回",
    cancelButtonText: "取消",
  });
  approving.value = true;
  try {
    await AuditAPI.reject({ case_id: detail.value!.id, audit_comment: value });
    ElMessage.success("已驳回");
    router.push("/cpx/audit/pending");
  } finally {
    approving.value = false;
  }
}

onMounted(fetchDetail);
</script>

<template>
  <div class="cpx-page p-4">
    <div v-loading="loading">
      <template v-if="detail">
        <div class="mb-4 flex items-center justify-between">
          <div class="flex items-center gap-3">
            <ElButton @click="router.back()">返回</ElButton>
            <h2 class="text-lg font-bold text-gray-700">病例审核：{{ detail.patient_name ?? "-" }}</h2>
            <ElTag :type="detail.status === 'submitted' ? 'warning' : 'info'">{{ detail.status }}</ElTag>
          </div>
          <div v-if="detail.status === 'submitted'" class="flex gap-2">
            <ElButton type="success" :loading="approving" @click="approve">审核通过</ElButton>
            <ElButton type="danger" :loading="approving" @click="reject">审核驳回</ElButton>
          </div>
        </div>

        <!-- 校验提示 -->
        <ElAlert v-if="!detail.checks.complete || !detail.checks.time_ok" type="warning" show-icon :closable="false" class="mb-4">
          <template #title>数据校验存在以下问题：</template>
          <ul class="list-inside list-disc text-sm">
            <li v-for="m in detail.checks.missing_required" :key="m.field_code">必填字段「{{ m.field_name }}」未填写</li>
            <li v-for="(t, i) in detail.checks.time_issues" :key="i">{{ t }}</li>
          </ul>
        </ElAlert>
        <ElAlert v-else type="success" show-icon :closable="false" class="mb-4" title="数据校验通过（必填完整、时间逻辑正常）" />

        <!-- 病例基本信息 -->
        <ElCard shadow="never" class="mb-4">
          <template #header><b>病例信息</b></template>
          <ElDescriptions :column="3" border>
            <ElDescriptionsItem label="病例编号">{{ detail.case_no ?? "-" }}</ElDescriptionsItem>
            <ElDescriptionsItem label="患者姓名">{{ detail.patient_name ?? "-" }}</ElDescriptionsItem>
            <ElDescriptionsItem label="性别">{{ detail.gender ?? "-" }}</ElDescriptionsItem>
            <ElDescriptionsItem label="年龄">{{ detail.age ?? "-" }}</ElDescriptionsItem>
            <ElDescriptionsItem label="联系电话">{{ detail.phone ?? "-" }}</ElDescriptionsItem>
            <ElDescriptionsItem label="所属医院">{{ detail.hospital_name ?? "-" }}</ElDescriptionsItem>
            <ElDescriptionsItem label="提交医生">{{ detail.doctor_name ?? "-" }}</ElDescriptionsItem>
            <ElDescriptionsItem label="填报模板">{{ detail.template_name ?? "-" }}</ElDescriptionsItem>
            <ElDescriptionsItem label="提交时间">{{ detail.create_time ?? "-" }}</ElDescriptionsItem>
          </ElDescriptions>
        </ElCard>

        <!-- 填报数据 -->
        <ElCard shadow="never" class="mb-4">
          <template #header><b>填报数据</b></template>
          <ElDescriptions v-if="detail.fields.length" :column="2" border>
            <ElDescriptionsItem v-for="f in detail.fields" :key="f.id" :label="`${f.field_name}${f.required_flag === 1 ? ' *' : ''}`">
              {{ detail.form_data[f.field_code] ?? "-" }}
              <template #label>
                <span>
                  {{ f.field_name }}
                  <ElTag v-if="f.required_flag === 1" size="small" type="danger" effect="plain">必填</ElTag>
                  <span class="ml-1 text-xs text-gray-400">{{ FIELD_TYPE_LABEL[f.field_type] ?? f.field_type }}</span>
                </span>
              </template>
            </ElDescriptionsItem>
          </ElDescriptions>
          <ElEmpty v-else description="无填报数据" :image-size="60" />
        </ElCard>

        <!-- 历史审核记录 -->
        <ElCard v-if="detail.audit_records.length" shadow="never">
          <template #header><b>历史审核记录</b></template>
          <ElTimeline>
            <ElTimelineItem
              v-for="a in detail.audit_records"
              :key="a.id"
              :timestamp="a.audit_time ?? ''"
              :type="a.audit_result === 'pass' ? 'success' : 'danger'"
            >
              <p>
                <ElTag :type="a.audit_result === 'pass' ? 'success' : 'danger'" size="small">
                  {{ a.audit_result === "pass" ? "通过" : "驳回" }}
                </ElTag>
                <span class="ml-2">{{ a.auditor_name }}</span>
              </p>
              <p v-if="a.audit_comment" class="text-sm text-gray-500">意见：{{ a.audit_comment }}</p>
            </ElTimelineItem>
          </ElTimeline>
        </ElCard>
      </template>
      <ElEmpty v-else-if="!loading" description="未找到病例" />
    </div>
  </div>
</template>
