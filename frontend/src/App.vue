<script setup lang="ts">
import { onMounted } from 'vue'
import { useThemeStore } from '@/stores/theme'
import TheSidebar from '@/components/TheSidebar.vue'

const theme = useThemeStore()
onMounted(() => theme.init())
</script>

<template>
  <div class="app-shell">
    <TheSidebar />
    <main class="app-main">
      <RouterView />
    </main>
  </div>
</template>

<style scoped>
.app-shell {
  display: flex;
  min-height: 100vh;
  background: var(--bg);
  color: var(--text);
}
.app-main {
  flex: 1;
  padding: 24px;
}
</style>
