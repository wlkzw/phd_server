<template>
  <div class="min-h-screen bg-slate-100 flex items-center justify-center px-4">
    <div
      v-if="!isLoggedIn"
      class="w-full max-w-md bg-white shadow-xl rounded-2xl p-8 space-y-6"
    >
      <header class="text-center space-y-2">
        <h1 class="text-3xl font-semibold text-slate-900">域账号登录</h1>
        <p class="text-sm text-slate-500">请输入域用户名和密码完成登录</p>
      </header>

      <form class="space-y-5" @submit.prevent="handleLogin">
        <div class="space-y-2">
          <label class="text-sm font-medium text-slate-700" for="username"
            >用户名</label
          >
          <input
            id="username"
            v-model.trim="username"
            type="text"
            required
            class="w-full rounded-lg border border-slate-200 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="domain\\username"
          />
        </div>

        <div class="space-y-2">
          <label class="text-sm font-medium text-slate-700" for="password"
            >密码</label
          >
          <input
            id="password"
            v-model="password"
            type="password"
            required
            class="w-full rounded-lg border border-slate-200 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="••••••••"
          />
        </div>

        <div
          v-if="errorMessage"
          class="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600"
        >
          {{ errorMessage }}
        </div>

        <button
          type="submit"
          :disabled="isLoading"
          class="w-full rounded-lg bg-blue-600 py-3 text-sm font-semibold text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
        >
          <span v-if="!isLoading">登录</span>
          <span v-else class="inline-flex items-center gap-2">
            <svg class="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
              <circle
                class="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                stroke-width="4"
              />
              <path
                class="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.37 0 0 5.37 0 12h4zm2 5.29A8 8 0 014 12H0c0 3.04 1.14 5.82 3 7.94l3-2.65z"
              />
            </svg>
            登录中…
          </span>
        </button>
      </form>
    </div>

    <div
      v-else
      class="w-full max-w-2xl bg-white shadow-xl rounded-2xl p-10 text-center space-y-6"
    >
      <div
        class="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-green-100 text-green-600"
      >
        <svg
          class="h-8 w-8"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="m5 13 4 4L19 7"
          />
        </svg>
      </div>

      <div class="space-y-2">
        <h2 class="text-2xl font-semibold text-slate-900">登录成功</h2>
        <p class="text-sm text-slate-500">
          欢迎回来，<span class="font-medium text-slate-700">{{
            userInfo.name || userInfo.username
          }}</span>
        </p>
      </div>

      <div class="grid gap-3 text-sm text-left text-slate-600">
        <div class="rounded-lg border border-slate-200 px-4 py-3">
          <span class="font-medium text-slate-700">用户名：</span
          >{{ userInfo.username }}
        </div>
        <div
          v-if="userInfo.email"
          class="rounded-lg border border-slate-200 px-4 py-3"
        >
          <span class="font-medium text-slate-700">邮箱：</span
          >{{ userInfo.email }}
        </div>
        <div
          v-if="userInfo.department"
          class="rounded-lg border border-slate-200 px-4 py-3"
        >
          <span class="font-medium text-slate-700">部门：</span
          >{{ userInfo.department }}
        </div>
      </div>

      <button
        class="inline-flex items-center justify-center rounded-lg border border-slate-200 px-6 py-3 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
        @click="handleLogout"
      >
        退出登录
      </button>
    </div>
  </div>
</template>

<script setup>
  import { ref } from 'vue';
  import axios from 'axios';
  import { useRouter } from 'vue-router';

  const router = useRouter();
  const username = ref('');
  const password = ref('');
  const isLoading = ref(false);
  const errorMessage = ref('');
  const isLoggedIn = ref(false);
  const userInfo = ref({});

  const API_BASE_URL = 'http://localhost:5000/api';

  const handleLogin = async () => {
    if (!username.value || !password.value) {
      errorMessage.value = '请输入用户名和密码';
      return;
    }

    isLoading.value = true;
    errorMessage.value = '';

    try {
      const response = await axios.post(`${API_BASE_URL}/login`, {
        username: username.value,
        password: password.value,
      });

      if (response.data?.success) {
        const info = response.data.user ?? { username: username.value };
        isLoggedIn.value = true;
        userInfo.value = info;
        localStorage.setItem('token', response.data.token);
        localStorage.setItem('user', JSON.stringify(info));
        router.push({ name: 'tables' });
      } else {
        errorMessage.value = response.data?.message ?? '认证失败';
      }
    } catch (error) {
      errorMessage.value = error.response?.data?.message ?? '无法连接服务器';
    } finally {
      isLoading.value = false;
    }
  };

  const handleLogout = () => {
    isLoggedIn.value = false;
    userInfo.value = {};
    username.value = '';
    password.value = '';
    localStorage.removeItem('token');
  };
</script>
