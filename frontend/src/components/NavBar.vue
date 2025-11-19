<template>
  <nav class="bg-white shadow-sm">
    <div class="mx-auto flex h-14 max-w-5xl items-center justify-between px-4">
      <RouterLink to="/tables" class="text-base font-semibold text-slate-900">
        PHD Importer
      </RouterLink>
      <div class="flex items-center gap-4 text-sm font-medium text-slate-600">
        <RouterLink class="hover:text-blue-600" to="/tables"
          >Project List</RouterLink
        >
        <button
          @click="handleLogout"
          class="hover:text-blue-600 hover:cursor-pointer"
        >
          Exit
        </button>
      </div>
    </div>
  </nav>
</template>

<script setup>
  import { useRouter } from 'vue-router';

  const router = useRouter();

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    router.push('/');
  };
</script>
