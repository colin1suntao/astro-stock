<script setup lang="ts">
import { RouterLink, RouterView, useRouter } from 'vue-router'
import { isLoggedIn } from '@/api'

const router = useRouter()
function logout() {
  localStorage.removeItem('astro-token')
  localStorage.removeItem('astro-user')
  router.push('/')
}
</script>

<template>
  <aside class="sidebar">
    <div class="logo">🌌 AstroStock</div>
    <nav>
      <RouterLink to="/dashboard">📊 仪表盘</RouterLink>
      <RouterLink v-if="isLoggedIn()" to="/birth-chart">🌟 我的星盘</RouterLink>
      <RouterLink v-if="isLoggedIn()" to="/market-calendar">📅 市场日历</RouterLink>
      <RouterLink v-if="isLoggedIn()" to="/heatmap">🔥 板块热力图</RouterLink>
      <RouterLink v-if="isLoggedIn()" to="/sky-history">📅 天象日历</RouterLink>
      <RouterLink v-if="isLoggedIn()" to="/leaderboard">🏆 占星排行</RouterLink>
      <RouterLink v-if="isLoggedIn()" to="/portfolio">💼 投资组合</RouterLink>
    </nav>
    <div v-if="isLoggedIn()" class="logout-area">
      <button class="logout-btn" @click="logout">🚪 退出</button>
    </div>
  </aside>
</template>

<style scoped>
.sidebar {
  width: 220px;
  padding: 20px 16px;
  border-right: 1px solid var(--border);
  background: var(--surface);
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.logo {
  font-size: 18px;
  font-weight: 700;
  color: var(--accent);
}
nav {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
nav a {
  padding: 8px 12px;
  border-radius: 8px;
  color: var(--text2);
  text-decoration: none;
  transition: background 0.2s;
}
nav a:hover,
nav a.router-link-active {
  background: var(--surface2);
  color: var(--text);
}
.logout-area { margin-top: auto; padding-top: 12px; border-top: 1px solid var(--border); }
.logout-btn { width: 100%; padding: 8px; border: 1px solid var(--border); border-radius: 8px; background: var(--surface2); color: var(--text2); cursor: pointer; font-size: 13px; }
.logout-btn:hover { background: var(--danger); color: #fff; }
</style>
