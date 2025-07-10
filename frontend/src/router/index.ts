import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from '../views/Dashboard.vue'
import Upload from '../views/Upload.vue'
import History from '../views/History.vue'
import Devices from '../views/Devices.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'dashboard',
      component: Dashboard,
    },
    {
      path: '/upload',
      name: 'upload',
      component: Upload,
    },
    {
      path: '/history',
      name: 'history',
      component: History,
    },
    {
      path: '/devices',
      name: 'devices',
      component: Devices,
    },
  ],
})

export default router