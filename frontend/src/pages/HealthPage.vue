<script setup lang="ts">
import { ref, onMounted } from 'vue'

const status = ref<'loading' | 'ok' | 'fail'>('loading')
const backend = ref<string>('')

async function check() {
  try {
    const res = await fetch('/api/health')
    const data = await res.json()
    status.value = 'ok'
    backend.value = data.version || 'unknown'
  } catch {
    status.value = 'fail'
  }
}

onMounted(check)
</script>

<template>
  <section>
    <h1>🩺 系统健康</h1>
    <div class="card">
      <div class="row">
        <span>前端</span>
        <span class="ok">✅ 运行中</span>
      </div>
      <div class="row">
        <span>后端 /api/health</span>
        <span v-if="status === 'loading'">⏳ 检测中…</span>
        <span v-else-if="status === 'ok'" class="ok">✅ {{ backend }}</span>
        <span v-else class="fail">❌ 无法连接</span>
      </div>
      <button class="retry" @click="check">重新检测</button>
    </div>
  </section>
</template>

<style scoped>
.card {
  padding: 20px;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: var(--surface);
  max-width: 400px;
}
.row {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
}
.ok {
  color: var(--success);
}
.fail {
  color: var(--danger);
}
.retry {
  margin-top: 12px;
  padding: 8px 16px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--surface2);
  color: var(--text);
  cursor: pointer;
}
</style>
