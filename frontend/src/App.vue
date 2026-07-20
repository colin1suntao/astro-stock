<script setup lang="ts">
import { onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useThemeStore } from '@/stores/theme'
import TheSidebar from '@/components/TheSidebar.vue'

const theme = useThemeStore()
const route = useRoute()
onMounted(() => theme.init())
</script>

<template>
  <div class="app-shell">
    <TheSidebar v-if="route.name !== 'auth'" />
    <main class="app-main" :class="{ 'app-main--full': route.name === 'auth' }">
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
.app-main--full { max-width: 100%; padding: 0; }
</style>
