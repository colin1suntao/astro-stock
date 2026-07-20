import { createRouter, createWebHistory } from 'vue-router'
import { isLoggedIn } from '@/api'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'auth',
      component: () => import('@/pages/AuthPage.vue'),
    },
    {
      path: '/dashboard',
      name: 'dashboard',
      component: () => import('@/pages/DashboardPage.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/stock/:ticker',
      name: 'stock-detail',
      component: () => import('@/pages/StockDetailPage.vue'),
      props: true,
      meta: { requiresAuth: true },
    },
    {
      path: '/birth-chart',
      name: 'birth-chart',
      component: () => import('@/pages/BirthChartPage.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/market-calendar',
      name: 'market-calendar',
      component: () => import('@/pages/MarketCalendarPage.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/heatmap',
      name: 'heatmap',
      component: () => import('@/pages/HeatmapPage.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/sky-history',
      name: 'sky-history',
      component: () => import('@/pages/SkyHistoryPage.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/leaderboard',
      name: 'leaderboard',
      component: () => import('@/pages/LeaderboardPage.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/share/:token',
      name: 'share',
      component: () => import('@/pages/LeaderboardPage.vue'),
      props: true,
    },
    {
      path: '/portfolio',
      name: 'portfolio',
      component: () => import('@/pages/PortfolioPage.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/auth',
      redirect: '/',  // 旧链兼容 → 跳首页
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
