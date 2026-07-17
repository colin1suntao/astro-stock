<script setup lang="ts">
import { RouterLink, RouterView } from 'vue-router'
</script>

<template>
  <aside class="sidebar">
    <div class="logo">🌌 AstroStock</div>
    <nav>
      <RouterLink to="/">📊 仪表盘</RouterLink>
      <RouterLink to="/birth-chart">🌟 我的星盘</RouterLink>
      <RouterLink to="/market-calendar">📅 市场日历</RouterLink>
      <RouterLink to="/heatmap">🔥 板块热力图</RouterLink>
      <RouterLink to="/portfolio">💼 投资组合</RouterLink>
      <RouterLink to="/auth">🔐 登录</RouterLink>
      <RouterLink to="/health">🩺 Health</RouterLink>
    </nav>
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
</style>
