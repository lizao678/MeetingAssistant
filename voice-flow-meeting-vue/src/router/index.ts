import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView,
      meta: {
        title: '首页',
        icon: 'House'
      }
    },
    {
      path: '/recordings',
      name: 'recordings',
      component: () => import('../views/RecordingsView.vue'),
      meta: {
        title: '我的记录',
        icon: 'Folder'
      }
    },
    {
      path: '/realtime',
      name: 'realtime',
      component: () => import('../views/RealtimeView.vue'),
      meta: {
        title: '实时转写',
        icon: 'Microphone'
      }
    },
    {
      path: '/upload',
      name: 'upload',
      component: () => import('../views/UploadView.vue'),
      meta: {
        title: '上传音视频',
        icon: 'Upload'
      }
    },
    {
      path: '/settings',
      name: 'settings',
      component: () => import('../views/SettingsView.vue'),
      meta: {
        title: '设置',
        icon: 'Setting'
      }
    }
  ],
})

export default router
