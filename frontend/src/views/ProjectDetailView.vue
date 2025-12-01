<template>
  <div class="min-h-screen bg-slate-100 py-10">
    <div class="mx-auto w-full max-w-5xl space-y-8 px-4">
      <header class="flex items-center justify-between">
        <div>
          <h1 class="text-2xl font-semibold text-slate-900">Project Detail</h1>
          <p class="text-sm text-slate-500">{{ projectNumber }}</p>
        </div>
        <div class="flex gap-3">
          <button
            @click="showUploadModal = true"
            class="inline-flex items-center rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            Import Data
          </button>
          <RouterLink
            to="/tables"
            class="inline-flex items-center rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100"
          >
            ← Back
          </RouterLink>
        </div>
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

      <div v-else class="space-y-6">
        <!-- 统计卡片 -->
        <div class="grid gap-4 sm:grid-cols-3">
          <div class="rounded-2xl bg-white p-6 shadow">
            <h3 class="mb-2 text-sm font-medium text-slate-500">Total Rows</h3>
            <p class="text-2xl font-semibold text-slate-900">
              {{ detail.total_rows?.toLocaleString() ?? 0 }}
            </p>
          </div>
          <div class="rounded-2xl bg-white p-6 shadow">
            <h3 class="mb-2 text-sm font-medium text-slate-500">
              Oldest Record
            </h3>
            <p class="text-lg font-semibold text-slate-900">
              {{ formatTimestamp(detail.oldest) }}
            </p>
          </div>
          <div class="rounded-2xl bg-white p-6 shadow">
            <h3 class="mb-2 text-sm font-medium text-slate-500">
              Newest Record
            </h3>
            <p class="text-lg font-semibold text-slate-900">
              {{ formatTimestamp(detail.newest) }}
            </p>
          </div>
        </div>

        <!-- Name 标签列表 -->
        <div class="rounded-2xl bg-white shadow">
          <div class="border-b border-slate-200 px-6 py-4">
            <h3 class="text-lg font-semibold text-slate-900">
              Tag List ({{ detail.names_count ?? 0 }})
            </h3>
          </div>
          <div class="max-h-96 overflow-y-auto">
            <table class="w-full table-auto">
              <thead
                class="sticky top-0 bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-500"
              >
                <tr>
                  <th class="px-6 py-3">Name</th>
                  <th class="px-6 py-3">Count</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="item in detail.names"
                  :key="item.name"
                  class="border-t border-slate-100 text-sm text-slate-700"
                >
                  <td class="px-6 py-4 font-medium">{{ item.name }}</td>
                  <td class="px-6 py-4">{{ item.count.toLocaleString() }}</td>
                </tr>
                <tr
                  v-if="!detail.names || detail.names.length === 0"
                  class="border-t border-slate-100 text-sm text-slate-500"
                >
                  <td class="px-6 py-4" colspan="2">No data</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- 标签选择与图表展示 -->
        <div class="rounded-2xl bg-white p-6 shadow">
          <h3 class="mb-4 text-lg font-semibold text-slate-900">
            Data Trend Display
          </h3>

          <!-- 标签选择器 -->
          <div class="mb-4 space-y-3">
            <label class="text-sm font-medium text-slate-700"
              >Select Tags</label
            >
            <div
              class="max-h-48 overflow-y-auto rounded border border-slate-200 p-2"
            >
              <label
                v-for="tag in detail.names"
                :key="tag.name"
                class="flex items-center gap-2 rounded px-2 py-1 hover:bg-slate-50"
              >
                <input
                  type="checkbox"
                  :value="tag.name"
                  v-model="selectedTags"
                  class="rounded border-slate-300"
                />
                <span class="text-sm text-slate-700">{{ tag.name }}</span>
              </label>
            </div>

            <!-- 时间段筛选 -->
            <div class="grid gap-3 sm:grid-cols-2">
              <div class="space-y-2">
                <label class="text-sm font-medium text-slate-700"
                  >Start Time</label
                >
                <input
                  type="datetime-local"
                  v-model="startTime"
                  class="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div class="space-y-2">
                <label class="text-sm font-medium text-slate-700"
                  >End Time</label
                >
                <input
                  type="datetime-local"
                  v-model="endTime"
                  class="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>

            <button
              @click="loadChartData"
              :disabled="selectedTags.length === 0 || isLoadingChart"
              class="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <span v-if="!isLoadingChart">Show Chart</span>
              <span v-else>Loading…</span>
            </button>

            <button
              @click="exportCLC"
              :disabled="selectedTags.length === 0 || isExporting"
              class="rounded-lg border border-blue-600 px-4 py-2 text-sm font-semibold text-blue-600 hover:bg-blue-50 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <span v-if="!isExporting">Export CLC File</span>
              <span v-else>Exporting…</span>
            </button>
          </div>

          <!-- 图表容器 -->
          <div
            v-if="chartError"
            class="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600"
          >
            {{ chartError }}
          </div>
          <div v-else-if="showChart" class="relative h-96">
            <canvas ref="chartCanvas"></canvas>
          </div>
        </div>
      </div>
    </div>

    <!-- 导入数据弹窗 -->
    <div
      v-if="showUploadModal"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 px-4"
      @click.self="showUploadModal = false"
    >
      <div class="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl">
        <h2 class="mb-4 text-xl font-semibold text-slate-900">
          Import from CSV
        </h2>

        <form @submit.prevent="handleUpload" class="space-y-4">
          <div class="space-y-2">
            <label class="text-sm font-medium text-slate-700" for="csvFile">
              Select CSV file
            </label>
            <input
              id="csvFile"
              type="file"
              accept=".csv,.xlsx"
              @change="handleFileChange"
              class="block w-full text-sm text-slate-600 file:mr-4 file:rounded-lg file:border-0 file:bg-blue-600 file:px-4 file:py-2 file:text-sm file:font-semibold file:text-white hover:file:bg-blue-700"
            />
          </div>

          <div
            v-if="uploadError"
            class="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600"
          >
            {{ uploadError }}
          </div>

          <div class="flex gap-3">
            <button
              type="button"
              @click="showUploadModal = false"
              class="flex-1 rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              :disabled="!selectedFile || isUploading"
              class="flex-1 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <span v-if="!isUploading">Upload</span>
              <span v-else>Uploading…</span>
            </button>
          </div>

          <!-- <div class="flex gap-3">
            <button
              @click="loadChartData"
              :disabled="selectedTags.length === 0 || isLoadingChart"
              class="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <span v-if="!isLoadingChart">Show Chart</span>
              <span v-else>Loading…</span>
            </button>

            <button
              @click="exportCLC"
              :disabled="selectedTags.length === 0 || isExporting"
              class="rounded-lg border border-blue-600 px-4 py-2 text-sm font-semibold text-blue-600 hover:bg-blue-50 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <span v-if="!isExporting">Export CLC File</span>
              <span v-else>Exporting…</span>
            </button>
          </div> -->
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
  import { onMounted, ref, nextTick } from 'vue';
  import { useRoute, useRouter } from 'vue-router';
  import axios from 'axios';
  import { Chart, registerables } from 'chart.js';
  import 'chartjs-adapter-date-fns';
  import { API_BASE_URL } from '@/config/api';

  Chart.register(...registerables);

  const route = useRoute();
  const router = useRouter();
  const projectNumber = ref(route.params.projectNumber || '');
  const detail = ref({});
  const isLoading = ref(true);
  const errorMessage = ref('');

  const showUploadModal = ref(false);
  const selectedFile = ref(null);
  const isUploading = ref(false);
  const uploadError = ref('');

  const selectedTags = ref([]);
  const startTime = ref('');
  const endTime = ref('');
  const isLoadingChart = ref(false);
  const chartError = ref('');
  const showChart = ref(false);
  const chartCanvas = ref(null);
  const isExporting = ref(false);
  let chartInstance = null;

  const formatTimestamp = (ts) => {
    if (!ts) return 'N/A';
    try {
      return new Date(ts).toLocaleString();
    } catch {
      return 'Invalid';
    }
  };

  const loadChartData = async () => {
    if (selectedTags.value.length === 0) return;

    isLoadingChart.value = true;
    chartError.value = '';
    showChart.value = false; // 重置图表显示状态

    const token = localStorage.getItem('token');

    try {
      const payload = {
        tags: selectedTags.value,
      };

      // 添加时间筛选条件
      if (startTime.value) {
        payload.start_time = new Date(startTime.value).toISOString();
      }
      if (endTime.value) {
        payload.end_time = new Date(endTime.value).toISOString();
      }

      const response = await axios.post(
        `${API_BASE_URL}/api/questdb/chart-data/${projectNumber.value}`,
        payload,
        { headers: { Authorization: `Bearer ${token}` } }
      );

      console.log('Chart data response:', response.data);

      if (response.data?.success) {
        renderChart(response.data.data);
      } else {
        chartError.value =
          response.data?.message ?? 'Failed to load chart data';
      }
    } catch (error) {
      console.error('Chart data error:', error);
      chartError.value =
        error.response?.data?.message ?? 'Server connection failed';
    } finally {
      isLoadingChart.value = false;
    }
  };

  const renderChart = (data) => {
    // 先销毁旧图表
    if (chartInstance) {
      chartInstance.destroy();
      chartInstance = null;
    }

    // 先显示图表容器
    showChart.value = true;

    // 等待 DOM 更新
    nextTick(() => {
      if (!chartCanvas.value) {
        console.error('Canvas element not found after nextTick');
        chartError.value = 'Failed to initialize chart';
        return;
      }

      console.log('Rendering chart with data:', data);

      const ctx = chartCanvas.value.getContext('2d');
      const colors = [
        '#3b82f6',
        '#ef4444',
        '#10b981',
        '#f59e0b',
        '#8b5cf6',
        '#ec4899',
        '#14b8a6',
        '#f97316',
        '#6366f1',
        '#84cc16',
      ];

      const datasets = Object.keys(data).map((tag, idx) => {
        const points = data[tag].map((item) => ({
          x: new Date(item.time).getTime(),
          y: item.value,
        }));

        console.log(`Tag ${tag}: ${points.length} points`);

        return {
          label: tag,
          data: points,
          borderColor: colors[idx % colors.length],
          backgroundColor: colors[idx % colors.length] + '20',
          tension: 0.1,
          pointRadius: 0,
        };
      });

      chartInstance = new Chart(ctx, {
        type: 'line',
        data: { datasets },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            x: {
              type: 'time',
              time: {
                unit: 'hour',
                displayFormats: {
                  minute: 'MM-dd HH:mm',
                  hour: 'MM-dd HH:mm',
                  day: 'yyyy-MM-dd',
                },
                tooltipFormat: 'yyyy-MM-dd HH:mm:ss',
              },
              title: { display: true, text: 'Time' },
            },
            y: {
              title: { display: true, text: 'Value' },
            },
          },
          plugins: {
            legend: { position: 'top' },
            tooltip: {
              mode: 'index',
              intersect: false,
            },
          },
        },
      });

      console.log('Chart rendered successfully');
    });
  };

  const handleFileChange = (event) => {
    selectedFile.value = event.target.files?.[0] ?? null;
    uploadError.value = '';
  };

  const handleUpload = async () => {
    if (!selectedFile.value) {
      uploadError.value = '请选择文件';
      return;
    }

    isUploading.value = true;
    uploadError.value = '';

    const token = localStorage.getItem('token');
    const formData = new FormData();
    formData.append('file', selectedFile.value);

    try {
      const response = await axios.post(
        `/api/questdb/import-csv/${projectNumber.value}`,
        formData,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (response.data?.success) {
        showUploadModal.value = false;
        selectedFile.value = null;
        // 上传成功后刷新详情
        await loadDetail();
      } else {
        uploadError.value = response.data?.message ?? '导入失败';
      }
    } catch (error) {
      uploadError.value = error.response?.data?.message ?? '服务器连接失败';
    } finally {
      isUploading.value = false;
    }
  };

  const loadDetail = async () => {
    const token = localStorage.getItem('token');
    if (!token) {
      router.replace('/');
      return;
    }

    try {
      const response = await axios.get(
        `${API_BASE_URL}/api/questdb/table-detail/${projectNumber.value}`,
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );
      if (response.data?.success) {
        detail.value = response.data.detail ?? {};

        // 设置默认时间范围
        if (detail.value.oldest) {
          startTime.value = formatDateTimeLocal(detail.value.oldest);
        }
        if (detail.value.newest) {
          endTime.value = formatDateTimeLocal(detail.value.newest);
        }
      } else {
        errorMessage.value = response.data?.message ?? 'Failed to load detail';
      }
    } catch (error) {
      errorMessage.value =
        error.response?.data?.message ?? 'Server connection failed';
    } finally {
      isLoading.value = false;
    }
  };

  const formatDateTimeLocal = (timestamp) => {
    if (!timestamp) return '';
    try {
      const date = new Date(timestamp);
      // 格式化为 datetime-local 输入框需要的格式: YYYY-MM-DDTHH:mm
      const year = date.getFullYear();
      const month = String(date.getMonth() + 1).padStart(2, '0');
      const day = String(date.getDate()).padStart(2, '0');
      const hours = String(date.getHours()).padStart(2, '0');
      const minutes = String(date.getMinutes()).padStart(2, '0');
      return `${year}-${month}-${day}T${hours}:${minutes}`;
    } catch {
      return '';
    }
  };

  const exportCLC = async () => {
    if (selectedTags.value.length === 0) {
      alert('请至少选择一个标签');
      return;
    }

    isExporting.value = true;
    const token = localStorage.getItem('token');

    try {
      const payload = {
        tags: selectedTags.value,
      };

      if (startTime.value) {
        payload.start_time = new Date(startTime.value).toISOString();
      }
      if (endTime.value) {
        payload.end_time = new Date(endTime.value).toISOString();
      }

      const response = await axios.post(
        `${API_BASE_URL}/api/questdb/export-clc/${projectNumber.value}`,
        payload,
        {
          headers: { Authorization: `Bearer ${token}` },
          responseType: 'blob',
        }
      );

      // 创建下载链接
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${projectNumber.value}.clc`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      alert(error.response?.data?.message ?? '导出失败');
    } finally {
      isExporting.value = false;
    }
  };

  onMounted(loadDetail);
</script>
