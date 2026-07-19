import { createRouter, createWebHistory } from 'vue-router'
import { isLoggedIn } from '@/api'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'dashboard',
      component: () => import('@/pages/DashboardPage.vue'),
    },
    {
      path: '/stock/:ticker',
      name: 'stock-detail',
      component: () => import('@/pages/StockDetailPage.vue'),
      props: true,
    },
    {
      path: '/birth-chart',
      name: 'birth-chart',
      component: () => import('@/pages/BirthChartPage.vue'),
    },
    {
      path: '/market-calendar',
      name: 'market-calendar',
      component: () => import('@/pages/MarketCalendarPage.vue'),
    },
    {
      path: '/heatmap',
      name: 'heatmap',
      component: () => import('@/pages/HeatmapPage.vue'),
    },
    {
      path: '/sky-history',
      name: 'sky-history',
      component: () => import('@/pages/SkyHistoryPage.vue'),
    },
    {
      path: '/portfolio',
      name: 'portfolio',
      component: () => import('@/pages/PortfolioPage.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/auth',
      name: 'auth',
      component: () => import('@/pages/AuthPage.vue'),
    },
    {
      path: '/health',
      name: 'health',
      component: () => import('@/pages/HealthPage.vue'),
    },
  ],
})

router.beforeEach((to) => {
  if (to.meta.requiresAuth && !isLoggedIn()) {
    return { name: 'auth', query: { redirect: to.fullPath } }
  }
})
