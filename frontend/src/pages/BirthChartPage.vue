<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { api, type BirthChart as BC } from '@/api'

const birth = ref('1994-08-10T14:32:00')
const lat = ref(31.23)
const lon = ref(121.47)
const chart = ref<BC | null>(null)
const loading = ref(false)
const error = ref('')

const planetColor: Record<string, string> = {
  sun: '#fde68a', moon: '#c7d2fe', mercury: '#93c5fd', venus: '#fda4af',
  mars: '#fb923c', jupiter: '#a78bfa', saturn: '#94a3b8',
  uranus: '#67e8f9', neptune: '#60a5fa',
}
const planetSymbol: Record<string, string> = {
  sun: '☉', moon: '☽', mercury: '☿', venus: '♀', mars: '♂',
  jupiter: '♃', saturn: '♄', uranus: '♅', neptune: '♆',
}
const planetName: Record<string, string> = {
  sun: '太阳', moon: '月亮', mercury: '水星', venus: '金星', mars: '火星',
  jupiter: '木星', saturn: '土星', uranus: '天王', neptune: '海王',
}

// 本命盘 SVG — 行星按黄经映到圆周
const CX = 130, CY = 130, R = 115
const planetPoints = computed(() =>
  chart.value?.planets.map(p => {
    const angle = (p.longitude - 90) * (Math.PI / 180)
    return { ...p, x: CX + R * Math.cos(angle), y: CY + R * Math.sin(angle) }
  }) ?? []
)

async function load() {
  loading.value = true; error.value = ''
  try { chart.value = await api.birthChart(birth.value, lat.value, lon.value) }
  catch (e) { error.value = (e as Error).message }
  finally { loading.value = false }
}
onMounted(load)
</script>

<template>
  <section>
    <div class="topbar">
      <h1>🌟 我的星盘</h1>
      <div class="inputs">
        <input v-model="birth" placeholder="ISO 8601 出生时间" @change="load">
        <input v-model.number="lat" type="number" placeholder="lat" @change="load">
        <input v-model.number="lon" type="number" placeholder="lon" @change="load">
        <button @click="load">计算</button>
      </div>
    </div>
    <p v-if="loading" class="muted">计算中…</p>
    <p v-if="error" class="error">❌ {{ error }}</p>

    <div v-if="chart" class="grid-2">
      <div class="card center">
        <div class="card-title align-left">🌟 本命盘</div>
        <svg width="260" height="260" viewBox="0 0 260 260">
          <circle :cx="CX" :cy="CY" :r="R" fill="none" stroke="var(--border)" stroke-width="1.5" />
          <circle :cx="CX" :cy="CY" :r="R - 25" fill="none" stroke="var(--border)" stroke-width="0.8" stroke-dasharray="4 5" />
          <circle :cx="CX" :cy="CY" :r="R - 50" fill="none" stroke="var(--border)" stroke-width="0.5" stroke-dasharray="2 4" />
          <!-- 12 房位线 -->
          <line v-for="i in 12" :key="i"
            :x1="CX + (R - 50) * Math.cos((i * 30 - 90) * Math.PI / 180)"
            :y1="CY + (R - 50) * Math.sin((i * 30 - 90) * Math.PI / 180)"
            :x2="CX + R * Math.cos((i * 30 - 90) * Math.PI / 180)"
            :y2="CY + R * Math.sin((i * 30 - 90) * Math.PI / 180)"
            stroke="var(--border)" stroke-width="0.5" opacity="0.3" />
          <!-- 行星点 -->
          <g v-for="p in planetPoints" :key="p.planet">
            <circle :cx="p.x" :cy="p.y" r="8" :fill="planetColor[p.planet]" opacity="0.9" />
            <text :x="p.x" :y="p.y + 4" text-anchor="middle" fill="#000" font-size="9" font-weight="700">{{ planetSymbol[p.planet] }}</text>
          </g>
          <!-- ASC 标记 -->
          <text :x="CX" :y="14" text-anchor="middle" fill="var(--accent)" font-size="11" font-weight="600">ASC {{ chart.ascendant_sign[0] }}</text>
        </svg>
      </div>

      <div class="card">
        <div class="card-title">📌 行星落位</div>
        <table class="house-table">
          <thead><tr><th>行星</th><th>星座</th><th>宫位</th><th>度数</th></tr></thead>
          <tbody>
            <tr v-for="p in chart.planets" :key="p.planet">
              <td>{{ planetSymbol[p.planet] }} {{ planetName[p.planet] }}</td>
              <td>{{ p.sign_symbol }} {{ p.sign }}</td>
              <td>第{{ p.house }}宫</td>
              <td>{{ p.degree_fmt }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </section>
</template>

<style scoped>
.topbar { display: flex; justify-content: space-between; align-items: center; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; }
.inputs { display: flex; gap: 8px; flex-wrap: wrap; }
.inputs input { padding: 6px 10px; border: 1px solid var(--border); border-radius: 6px; background: var(--surface); color: var(--text); width: 180px; }
.inputs button { padding: 6px 16px; border: 1px solid var(--border); border-radius: 6px; background: var(--surface2); color: var(--text); cursor: pointer; }
.muted { color: var(--text2); }
.error { color: var(--danger); }
.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.card { padding: 20px; border: 1px solid var(--border); border-radius: 12px; background: var(--surface); }
.card.center { display: flex; flex-direction: column; align-items: center; }
.align-left { align-self: flex-start; }
.card-title { font-weight: 600; margin-bottom: 16px; }
.house-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.house-table th { text-align: left; padding: 8px 6px; color: var(--text2); font-weight: 500; border-bottom: 1px solid var(--border); }
.house-table td { padding: 8px 6px; border-bottom: 1px solid var(--border); }
@media (max-width: 768px) { .grid-2 { grid-template-columns: 1fr; } }
</style>
