<script setup>
  import { RouterView } from 'vue-router';
  import NavBar from '@/components/NavBar.vue';
</script>

<template>
  <div class="min-h-screen bg-slate-100">
    <NavBar />
    <RouterView />
  </div>
</template>

<style scoped></style>
