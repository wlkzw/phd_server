<template>
  <div class="min-h-screen bg-slate-100 flex items-center justify-center px-4">
    <div
      class="w-full max-w-xl bg-white shadow-xl rounded-2xl p-8 text-center space-y-6"
    >
      <h2 class="text-2xl font-semibold text-slate-900">登录成功</h2>
      <p class="text-sm text-slate-600">
        欢迎回来，<span class="font-medium">{{
          user.name || user.username
        }}</span>
      </p>
      <div class="grid gap-3 text-left text-sm text-slate-600">
        <div>
          <span class="font-medium text-slate-700">用户名：</span
          >{{ user.username }}
        </div>
        <div v-if="user.email">
          <span class="font-medium text-slate-700">邮箱：</span>{{ user.email }}
        </div>
        <div v-if="user.department">
          <span class="font-medium text-slate-700">部门：</span
          >{{ user.department }}
        </div>
      </div>
      <RouterLink
        class="inline-flex rounded-lg border border-slate-200 px-6 py-3 text-sm font-medium"
        to="/"
      >
        返回登录
      </RouterLink>
    </div>
  </div>
</template>

<script setup>
  import { computed } from 'vue';
  import { useRouter } from 'vue-router';

  const router = useRouter();
  const user = computed(() => {
    const raw = localStorage.getItem('user');
    if (!raw) {
      router.replace('/');
      return {};
    }
    try {
      return JSON.parse(raw);
    } catch {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
    }
  });
</script>
