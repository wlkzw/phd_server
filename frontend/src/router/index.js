import { createRouter, createWebHistory } from 'vue-router';
import LoginView from '@/views/LoginView.vue';
import UploadView from '@/views/UploadView.vue';
import TablesView from '@/views/TablesView.vue';
import ProjectDetailView from '@/views/ProjectDetailView.vue';

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', name: 'login', component: LoginView },
    { path: '/upload', name: 'upload', component: UploadView },
    { path: '/tables', name: 'tables', component: TablesView },
    {
      path: '/project/:projectNumber',
      name: 'project-detail',
      component: ProjectDetailView,
    },
  ],
});

export default router;
