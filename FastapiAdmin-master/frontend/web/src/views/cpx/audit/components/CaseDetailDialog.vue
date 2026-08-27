<!-- 审核端 · 病例详情弹窗（大尺寸只读，样式与管理员端病例详情一致）
  四模块：基础信息 / 完整患者信息 / 救治过程时间轴（动态模板字段）/ 审核完整信息 -->
<script setup lang="ts">
import { ref, watch } from "vue";
import AuditAPI, { type AuditDetail } from "@/api/cpx/audit";

defineOptions({ name: "AuditCaseDetailDialog" });

const props = defineProps<{
  modelValue: boolean;
  caseId: number | null;
}>();

const emit = defineEmits<{
  (e: "update:modelValue", v: boolean): void;
}>();

const loading = ref(false);
const detail = ref<AuditDetail | null>(null);

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

const isLongText = (f: { field_code: string }) => {
  const v = detail.value?.form_data?.[f.field_code];
  return typeof v === "string" && v.length > 40;
};

async function load() {
  if (!props.modelValue || props.caseId == null) return;
  loading.value = true;
  detail.value = null;
  try {
    const res = await AuditAPI.detail(props.caseId);
    detail.value = res.data.data;
  } finally {
    loading.value = false;
  }
}

watch(
  () => props.modelValue,
  (v) => {
    if (v) load();
  }
);
</script>

<template>
  <ElDialog
    :model-value="modelValue"
    title="病例详情"
    width="920px"
    top="4vh"
    :close-on-click-modal="false"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <div v-loading="loading" class="max-h-[75vh] overflow-y-auto pr-1">
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
            <ElDescriptionsItem label="联系电话">{{ detail.phone || "-" }}</ElDescriptionsItem>
          </ElDescriptions>
        </div>

        <!-- 模块三：救治过程（动态模板字段自动渲染） -->
        <div class="mb-5">
          <div class="mb-2 flex items-center gap-2">
            <span class="i-ri:heart-pulse-line text-emerald-500" />
            <span class="text-sm font-semibold text-gray-700">救治过程时间轴（模板字段）</span>
            <ElTag v-if="detail.template_name" size="small" type="info" effect="plain">{{ detail.template_name }}</ElTag>
          </div>
          <ElDescriptions v-if="detail.fields.length" :column="2" border size="small">
            <ElDescriptionsItem
              v-for="f in detail.fields"
              :key="f.id"
              :label="f.field_name"
              :span="isLongText(f) ? 2 : 1"
            >
              <span :class="{ 'whitespace-pre-wrap': isLongText(f) }">{{ fieldValue(f) }}</span>
            </ElDescriptionsItem>
          </ElDescriptions>
          <ElEmpty v-else description="该病例暂无模板填报数据" :image-size="60" />
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
      <ElEmpty v-else-if="!loading" description="未找到病例数据" :image-size="60" />
    </div>

    <template #footer>
      <ElButton type="primary" @click="emit('update:modelValue', false)">关闭</ElButton>
    </template>
  </ElDialog>
</template>
