<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api, type PlanetPosition, type Aspect, type MoonPhase } from '@/api'

const moon = ref<MoonPhase | null>(null)
const positions = ref<PlanetPosition[]>([])
const upcomingAspects = ref<Aspect[]>([])
const loading = ref(true)
const error = ref('')

// 本周重要天象 — MVP 用当前相位聚合（真实天象历待 P2）
async function load() {
  loading.value = true; error.value = ''
  try {
    const [m, p, a] = await Promise.all([api.moonPhase(), api.planetPositions(), api.aspects()])
    moon.value = m
    positions.value = p
    upcomingAspects.value = a.slice(0, 5)
  } catch (e) { error.value = (e as Error).message }
  finally { loading.value = false }
}
onMounted(load)

const typeLabel: Record<string, string> = {
  conjunction: '合相', opposition: '对冲', trine: '三分', square: '四分', sextile: '六分',
}
</script>

<template>
  <section>
    <div class="topbar">
      <h1>📅 占星市场日历</h1>
      <span v-if="moon" class="muted">{{ moon.name }} · {{ moon.illumination_pct }}%</span>
    </div>
    <p v-if="loading" class="muted">加载中…</p>
    <p v-if="error" class="error">❌ {{ error }} <button @click="load">重试</button></p>

    <div v-if="!loading && !error" class="grid-2">
      <div class="card">
        <div class="card-title">本周重要天象（当前相位）</div>
        <div class="event-list">
          <div v-for="(a, i) in upcomingAspects" :key="i" class="event-row">
            <div class="event-info">
              <div class="title">{{ a.planet1 }} {{ typeLabel[a.type] }} {{ a.planet2 }}</div>
              <div class="desc muted">{{ a.influence === 'positive' ? '🟢 和谐助力' : a.influence === 'negative' ? '🔴 张力挑战' : '⚪ 中性' }}</div>
            </div>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="card-title">🌌 当前行星位置</div>
        <div class="planet-list">
          <div v-for="p in positions" :key="p.planet" class="planet-row">
            <span>{{ p.sign_symbol }} {{ p.sign }}</span>
            <span class="muted">{{ p.degree_fmt }}</span>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.topbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.muted { color: var(--text2); }
.error { color: var(--danger); }
.error button { margin-left: 8px; padding: 4px 12px; cursor: pointer; }
.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.card { padding: 20px; border: 1px solid var(--border); border-radius: 12px; background: var(--surface); }
.card-title { font-weight: 600; margin-bottom: 16px; }
.event-list { display: flex; flex-direction: column; gap: 12px; }
.event-row { padding: 12px; border-radius: 8px; background: var(--surface2); }
.event-info .title { font-weight: 600; }
.event-info .desc { font-size: 13px; margin-top: 4px; }
.planet-list { display: flex; flex-direction: column; gap: 6px; }
.planet-row { display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid var(--border); }
@media (max-width: 768px) { .grid-2 { grid-template-columns: 1fr; } }
</style>
