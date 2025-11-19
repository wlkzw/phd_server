<template>
  <div class="min-h-screen bg-slate-100 py-10">
    <div class="mx-auto w-full max-w-3xl space-y-8 px-4">
      <header
        class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between"
      >
        <div>
          <h1 class="text-2xl font-semibold text-slate-900">
            SQL 导入 QuestDB
          </h1>
          <p class="text-sm text-slate-500">
            上传 SQL 文件并自动转换为 CSV 后写入 QuestDB
          </p>
        </div>
        <RouterLink
          to="/success"
          class="inline-flex items-center rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100"
        >
          返回
        </RouterLink>
      </header>

      <div class="rounded-2xl bg-white p-8 shadow">
        <form class="space-y-6" @submit.prevent="handleSubmit">
          <div class="space-y-2">
            <label class="text-sm font-medium text-slate-700"
              >选择 SQL 文件</label
            >
            <input
              type="file"
              accept=".sql"
              @change="handleFileChange"
              class="block w-full text-sm text-slate-600 file:mr-4 file:rounded-lg file:border-0 file:bg-blue-600 file:px-4 file:py-2 file:text-sm file:font-semibold file:text-white hover:file:bg-blue-700"
            />
          </div>

          <button
            type="submit"
            :disabled="!selectedFile || isLoading"
            class="rounded-lg bg-blue-600 px-6 py-3 text-sm font-semibold text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
          >
            <span v-if="!isLoading">开始导入</span>
            <span v-else>正在导入…</span>
          </button>
        </form>
      </div>

      <div v-if="message" class="rounded-xl bg-white p-6 shadow">
        <p :class="messageClass">{{ message }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
  import { computed, ref } from 'vue';
  import axios from 'axios';
  import { useRouter } from 'vue-router';
  import { API_BASE_URL } from '@/config/api';

  const router = useRouter();
  const selectedFile = ref(null);
  const isLoading = ref(false);
  const message = ref('');

  const token = localStorage.getItem('token');
  if (!token) {
    router.replace('/');
  }

  const messageClass = computed(() =>
    message.value.startsWith('成功')
      ? 'text-sm text-green-600'
      : 'text-sm text-red-600'
  );

  const handleFileChange = (event) => {
    selectedFile.value = event.target.files?.[0] ?? null;
    message.value = '';
  };

  const handleSubmit = async () => {
    if (!selectedFile.value) return;

    const formData = new FormData();
    formData.append('file', selectedFile.value);

    isLoading.value = true;
    message.value = '';

    try {
      const response = await axios.post(
        `${API_BASE_URL}/api/questdb/import`,
        formData,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (response.data?.success) {
        message.value = `成功导入 ${response.data.imported ?? 0} 条记录`;
      } else {
        message.value = response.data?.message ?? '导入失败';
      }
    } catch (error) {
      message.value = error.response?.data?.message ?? '服务器连接失败';
    } finally {
      isLoading.value = false;
    }
  };
</script>
