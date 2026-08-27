<!-- 胸痛中心业务登录页 -->
<script setup lang="ts">
import { reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessage, type FormInstance, type FormRules } from "element-plus";
import { useUserStore } from "@stores";

defineOptions({ name: "CpxLogin" });

const router = useRouter();
const userStore = useUserStore();

const formRef = ref<FormInstance>();
const loading = ref(false);

const form = reactive({
  username: "",
  password: "",
});

const rules: FormRules = {
  username: [{ required: true, message: "请输入登录账号", trigger: "blur" }],
  password: [{ required: true, message: "请输入密码", trigger: "blur" }],
};

/** 按角色跳转首页 */
function roleHome(roleCode: string): string {
  if (roleCode === "admin") return "/cpx/dashboard";
  return roleCode === "auditor" ? "/cpx/audit/workbench" : "/cpx/hospital";
}

async function handleSubmit() {
  if (!formRef.value) return;
  const valid = await formRef.value.validate().catch(() => false);
  if (!valid) return;

  loading.value = true;
  try {
    const biz = await userStore.businessLogin({ username: form.username, password: form.password });
    ElMessage.success("登录成功");
    await router.replace(roleHome(biz.role_code));
  } catch (error) {
    // 错误消息已由请求拦截器提示
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <div class="cpx-login-root relative flex h-screen w-full items-center justify-center overflow-hidden">
    <!-- 医院主题背景：医疗色渐变 + 心电图波形 + 十字装饰 -->
    <div class="absolute inset-0 bg-gradient-to-br from-sky-500 via-blue-600 to-emerald-600" />
    <!-- 心电图波形（横贯底部） -->
    <svg
      class="absolute bottom-0 left-0 h-56 w-full text-white/20"
      viewBox="0 0 1440 220"
      preserveAspectRatio="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <path
        d="M0,110 L120,110 L150,60 L180,160 L210,110 L260,110 L260,110 L320,110 L350,40 L380,180 L420,110 L520,110 L540,80 L560,140 L600,110 L720,110 L760,20 L800,200 L850,110 L960,110 L980,70 L1010,150 L1060,110 L1180,110 L1210,50 L1250,170 L1300,110 L1440,110"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
      />
    </svg>
    <!-- 装饰：医院十字 + 心形（散落） -->
    <svg class="absolute left-[8%] top-[15%] h-24 w-24 text-white/15" viewBox="0 0 64 64" fill="currentColor">
      <rect x="26" y="10" width="12" height="44" rx="2" />
      <rect x="10" y="26" width="44" height="12" rx="2" />
    </svg>
    <svg class="absolute right-[10%] top-[12%] h-16 w-16 text-white/15" viewBox="0 0 24 24" fill="currentColor">
      <path d="M12 21s-7-4.5-9.5-9.5C.5 7 4 3 7.5 3c2 0 3.5 1 4.5 2.5C13 4 14.5 3 16.5 3 20 3 23.5 7 21.5 11.5 19 16.5 12 21 12 21z" />
    </svg>
    <svg class="absolute right-[18%] bottom-[20%] h-20 w-20 text-white/15" viewBox="0 0 64 64" fill="currentColor">
      <rect x="26" y="10" width="12" height="44" rx="2" />
      <rect x="10" y="26" width="44" height="12" rx="2" />
    </svg>
    <svg class="absolute left-[15%] bottom-[28%] h-14 w-14 text-white/15" viewBox="0 0 24 24" fill="currentColor">
      <path d="M12 21s-7-4.5-9.5-9.5C.5 7 4 3 7.5 3c2 0 3.5 1 4.5 2.5C13 4 14.5 3 16.5 3 20 3 23.5 7  21.5 11.5 19 16.5 12 21 12 21z" />
    </svg>

    <!-- 登录卡片 -->
    <div class="cpx-login-card relative z-10 w-[min(420px,92vw)] rounded-2xl bg-white p-8 shadow-2xl">
      <div class="mb-8 text-center">
        <div class="mx-auto mb-3 flex h-16 w-16 items-center justify-center overflow-hidden rounded-2xl bg-gradient-to-br from-blue-500 to-sky-400 text-white shadow-lg">
          <svg viewBox="0 0 64 64" class="h-12 w-12">
            <rect x="26" y="14" width="12" height="36" rx="2" fill="#ffffff" />
            <rect x="14" y="26" width="36" height="12" rx="2" fill="#ffffff" />
          </svg>
        </div>
        <h1 class="text-xl font-bold text-gray-800">智慧胸痛管理</h1>
        <p class="mt-1 text-xs text-gray-400">胸痛中心数据填报 · Web 管理后台</p>
      </div>

      <ElForm ref="formRef" :model="form" :rules="rules" label-position="top" size="large" @keyup.enter="handleSubmit">
        <ElFormItem label="登录账号" prop="username">
          <ElInput v-model="form.username" placeholder="请输入登录账号" clearable autocomplete="username">
            <template #prefix><span class="i-ri:user-line text-gray-400" /></template>
          </ElInput>
        </ElFormItem>
        <ElFormItem label="登录密码" prop="password">
          <ElInput v-model="form.password" type="password" placeholder="请输入登录密码" show-password autocomplete="current-password">
            <template #prefix><span class="i-ri:lock-line text-gray-400" /></template>
          </ElInput>
        </ElFormItem>
        <ElButton
          class="mt-2 w-full"
          type="primary"
          size="large"
          :loading="loading"
          @click="handleSubmit"
        >
          登 录
        </ElButton>
      </ElForm>

      <p class="mt-6 text-center text-xs text-gray-300">管理员 / 审核员账号登录 · 医生请使用 APP 端</p>
    </div>
  </div>
</template>
