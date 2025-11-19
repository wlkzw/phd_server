<template>
  <div class="min-h-screen bg-slate-100 py-10">
    <div class="mx-auto w-full max-w-4xl space-y-8 px-4">
      <header
        class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between"
      >
        <div>
          <h1 class="text-2xl font-semibold text-slate-900">Project List</h1>
          <p class="text-sm text-slate-500">当前实例中的所有表</p>
        </div>
        <!-- 只有管理员才能看到添加按钮 -->
        <button
          v-if="isAdmin"
          @click="showModal = true"
          class="inline-flex items-center rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
        >
          Add Project
        </button>
        <div v-else class="text-sm text-slate-500">仅管理员可添加项目</div>
      </header>

      <section
        v-if="isLoading"
        class="rounded-2xl bg-white p-8 text-center shadow"
      >
        <p class="text-sm text-slate-500">Loading…</p>
      </section>

      <section v-else-if="errorMessage" class="rounded-2xl bg-white p-8 shadow">
        <p class="text-sm text-red-600">{{ errorMessage }}</p>
      </section>

      <section v-else class="rounded-2xl bg-white shadow">
        <table class="w-full table-auto">
          <thead
            class="bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-500"
          >
            <tr>
              <th class="px-6 py-3">Project Number</th>
              <th class="px-6 py-3">Oldest Record</th>
              <th class="px-6 py-3">Newest Record</th>
              <th class="px-6 py-3">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="table in tables"
              :key="table.table_name"
              class="border-t border-slate-100 text-sm text-slate-700"
            >
              <td class="px-6 py-4 font-medium">{{ table.table_name }}</td>
              <td class="px-6 py-4">
                {{ formatTimestamp(table.oldest) || 'No data' }}
              </td>
              <td class="px-6 py-4">
                {{ formatTimestamp(table.newest) || 'No data' }}
              </td>
              <td class="px-6 py-4">
                <RouterLink
                  :to="`/project/${table.table_name}`"
                  class="text-sm font-medium text-blue-600 hover:text-blue-700"
                >
                  View Detail
                </RouterLink>
              </td>
            </tr>
            <tr
              v-if="tables.length === 0"
              class="border-t border-slate-100 text-sm text-slate-500"
            >
              <td class="px-6 py-4" colspan="3">No Data</td>
            </tr>
          </tbody>
        </table>
      </section>
    </div>

    <!-- 添加项目弹窗 -->
    <div
      v-if="showModal"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 px-4"
      @click.self="showModal = false"
    >
      <div class="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl">
        <h2 class="mb-4 text-xl font-semibold text-slate-900">Add Project</h2>

        <form @submit.prevent="handleCreateProject" class="space-y-4">
          <div class="space-y-2">
            <label
              class="text-sm font-medium text-slate-700"
              for="projectNumber"
            >
              Project Number
            </label>
            <input
              id="projectNumber"
              v-model.trim="projectNumber"
              type="text"
              required
              class="w-full rounded-lg border border-slate-200 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Enter project number..."
            />
          </div>

          <div
            v-if="modalError"
            class="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600"
          >
            {{ modalError }}
          </div>

          <div class="flex gap-3">
            <button
              type="button"
              @click="showModal = false"
              class="flex-1 rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              :disabled="isCreating"
              class="flex-1 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <span v-if="!isCreating">Confirm</span>
              <span v-else>Creating…</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
  import { onMounted, ref } from 'vue';
  import axios from 'axios';
  import { useRouter } from 'vue-router';
  import { API_BASE_URL } from '@/config/api';

  const router = useRouter();
  const tables = ref([]);
  const isLoading = ref(true);
  const errorMessage = ref('');
  const showModal = ref(false);
  const projectNumber = ref('');
  const isCreating = ref(false);
  const modalError = ref('');
  const isAdmin = ref(false); // 新增：管理员标识

  const formatTimestamp = (ts) => {
    if (!ts) return 'N/A';
    try {
      return new Date(ts).toLocaleString();
    } catch {
      return 'Invalid';
    }
  };

  const loadTables = async () => {
    const token = localStorage.getItem('token');
    if (!token) {
      router.replace('/');
      return;
    }

    try {
      const response = await axios.get(`${API_BASE_URL}/api/questdb/tables`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.data?.success) {
        tables.value = response.data.tables ?? [];
      } else {
        errorMessage.value = response.data?.message ?? '无法获取表列表';
      }
    } catch (error) {
      errorMessage.value = error.response?.data?.message ?? '服务器连接失败';
    } finally {
      isLoading.value = false;
    }
  };

  // 新增：检查用户权限
  const checkPermissions = async () => {
    const token = localStorage.getItem('token');
    if (!token) {
      return;
    }

    try {
      const response = await axios.get(`${API_BASE_URL}/api/user/permissions`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.data?.success) {
        isAdmin.value = response.data.is_admin ?? false;
      }
    } catch (error) {
      console.error('Failed to check permissions:', error);
    }
  };

  const handleCreateProject = async () => {
    if (!projectNumber.value) {
      modalError.value = '请输入项目编号';
      return;
    }

    isCreating.value = true;
    modalError.value = '';
    const token = localStorage.getItem('token');

    try {
      const response = await axios.post(
        `${API_BASE_URL}/api/questdb/create-table`,
        { table_name: projectNumber.value },
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      if (response.data?.success) {
        showModal.value = false;
        projectNumber.value = '';
        isLoading.value = true;
        await loadTables();
      } else {
        modalError.value = response.data?.message ?? '创建项目失败';
      }
    } catch (error) {
      modalError.value = error.response?.data?.message ?? '服务器连接失败';
    } finally {
      isCreating.value = false;
    }
  };

  onMounted(async () => {
    await checkPermissions();
    await loadTables();
  });
</script>
