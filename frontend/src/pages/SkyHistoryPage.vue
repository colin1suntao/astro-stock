<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { api, type PlanetPosition, type Aspect } from '@/api'
import { useThemeStore } from '@/stores/theme'

const theme = useThemeStore()
onMounted(() => theme.init())

const selectedDate = ref(new Date().toISOString().slice(0, 10))
const snap = ref<{
  ts: string
  positions: PlanetPosition[]
  aspects: Aspect[]
  moon: { name: string; illumination_pct: number }
  highlighted_aspects: Aspect[]
  note: string
} | null>(null)
const loading = ref(false)
const error = ref('')

const planetSymbol: Record<string, string> = {
  sun: '☉', moon: '☽', mercury: '☿', venus: '♀', mars: '♂',
  jupiter: '♃', saturn: '♄', uranus: '♅', neptune: '♆',
}
const planetName: Record<string, string> = {
  sun: '太阳', moon: '月亮', mercury: '水星', venus: '金星', mars: '火星',
  jupiter: '木星', saturn: '土星', uranus: '天王', neptune: '海王',
}

// 相位轮 SVG — 7 颗古典行星
const WHEEL_CX = 170, WHEEL_CY = 170, WHEEL_R = 150
const classicalPlanets = ['sun', 'moon', 'mercury', 'venus', 'mars', 'jupiter', 'saturn']

const wheelPositions = computed(() => {
  const out: Array<{ planet: string; x: number; y: number }> = []
  for (const p of snap.value?.positions || []) {
    if (!classicalPlanets.includes(p.planet)) continue
    const angle = (p.longitude - 90) * (Math.PI / 180)
    out.push({
      planet: p.planet,
      x: WHEEL_CX + WHEEL_R * Math.cos(angle),
      y: WHEEL_CY + WHEEL_R * Math.sin(angle),
    })
  }
  return out
})

const aspectLines = computed(() => {
  const posMap = new Map(wheelPositions.value.map(p => [p.planet, p]))
  return (snap.value?.aspects || [])
    .filter(a => classicalPlanets.includes(a.planet1) && classicalPlanets.includes(a.planet2))
    .map(a => {
      const p1 = posMap.get(a.planet1)!
      const p2 = posMap.get(a.planet2)!
      const color = a.influence === 'positive' ? 'var(--success)' :
        a.influence === 'negative' ? 'var(--danger)' : 'var(--text3)'
      const dash = a.type === 'trine' || a.type === 'sextile' ? '6 3' : 'none'
      const highlighted = snap.value?.highlighted_aspects.some(
        h => h.planet1 === a.planet1 && h.planet2 === a.planet2 && h.type === a.type
      )
      return { x1: p1.x, y1: p1.y, x2: p2.x, y2: p2.y, color, dash, type: a.type, highlighted }
    })
})

const zodiacSymbols = ['♈', '♉', '♊', '♋', '♌', '♍', '♎', '♏', '♐', '♑', '♒', '♓']

async function load() {
  loading.value = true; error.value = ''
  try {
    snap.value = await api.skyHistory(selectedDate.value + 'T12:00:00')
  } catch (e) { error.value = (e as Error).message }
  finally { loading.value = false }
}
onMounted(() => load())

function pickToday() { selectedDate.value = new Date().toISOString().slice(0, 10); load() }
function pickNYE() { selectedDate.value = `${new Date().getFullYear()}-01-01`; load() }
</script>

<template>
  <div class="theme-init" :data-theme="theme.current">
    <section>
      <h1>📅 天象日历 — 回看任意日</h1>
      <p class="muted">选日期或快速跳今日/年初，查当时真行星位置+相位轮+月相（skyfield de421.bsp 真算）</p>

      <div class="date-bar">
        <input type="date" v-model="selectedDate" @change="load" class="date-input" />
        <button class="quick" @click="pickToday">今日</button>
        <button class="quick" @click="pickNYE">年初</button>
        <button class="quick" @click="load">重新加载</button>
      </div>

      <p v-if="loading" class="muted">推演中…</p>
      <p v-if="error" class="error">❌ {{ error }} <button @click="load">重试</button></p>

      <div v-if="snap && !loading" class="grid-2">
        <!-- 当时行星位置 -->
        <div class="card">
          <div class="card-title">🌌 {{ snap.ts.slice(0, 10) }} 行星位置</div>
          <div class="planet-grid">
            <div v-for="p in snap.positions" :key="p.planet" class="planet-row">
              <div class="planet">
                <span>{{ planetSymbol[p.planet] }} {{ planetName[p.planet] }}</span>
                <span v-if="p.is_retrograde" class="retro">逆</span>
              </div>
              <span class="sign-pos">{{ p.sign_symbol }} {{ p.sign }} {{ p.degree_fmt }}</span>
            </div>
          </div>
          <div class="moon-row">
            🌙 月相: {{ snap.moon.name }} · {{ snap.moon.illumination_pct }}%照明
          </div>
        </div>

        <!-- 当时相位轮 -->
        <div class="card">
          <div class="card-title">🔯 当时相位轮（标星=精确相位≤2°）</div>
          <div class="wheel-container">
            <svg width="340" height="340" viewBox="0 0 340 340">
              <circle :cx="WHEEL_CX" :cy="WHEEL_CY" :r="WHEEL_R" fill="none" stroke="var(--border)" stroke-width="1" />
              <circle :cx="WHEEL_CX" :cy="WHEEL_CY" :r="WHEEL_R - 30" fill="none" stroke="var(--border)" stroke-width="0.5" stroke-dasharray="4 6" />
              <g fill="var(--text3)" font-size="11" text-anchor="middle">
                <text v-for="(sym, i) in zodiacSymbols" :key="i"
                  :x="WHEEL_CX + (WHEEL_R - 15) * Math.cos((i * 30 - 90) * Math.PI / 180)"
                  :y="WHEEL_CY + (WHEEL_R - 15) * Math.sin((i * 30 - 90) * Math.PI / 180) + 4">{{ sym }}</text>
              </g>
              <g stroke-width="1.5" opacity="0.7">
                <line v-for="(l, i) in aspectLines" :key="i"
                  :x1="l.x1" :y1="l.y1" :x2="l.x2" :y2="l.y2"
                  :stroke="l.color" :stroke-dasharray="l.dash" :stroke-width="l.highlighted ? 3 : 1.5" />
              </g>
              <g>
                <circle v-for="wp in wheelPositions" :key="wp.planet"
                  :cx="wp.x" :cy="wp.y" r="10" fill="var(--accent)" opacity="0.9" />
                <text v-for="wp in wheelPositions" :key="wp.planet + '-t'"
                  :x="wp.x" :y="wp.y + 4" text-anchor="middle" fill="#000" font-size="10" font-weight="700">{{ planetSymbol[wp.planet] }}</text>
              </g>
            </svg>
          </div>
        </div>
      </div>
      <p v-if="snap" class="note muted">{{ snap.note }}</p>
    </section>
  </div>
</template>

<style scoped>
.muted { color: var(--text2); }
.error { color: var(--danger); }
.error button { margin-left: 8px; padding: 4px 12px; cursor: pointer; }
.date-bar { display: flex; gap: 12px; align-items: center; margin: 16px 0; flex-wrap: wrap; }
.date-input { padding: 8px 12px; border: 1px solid var(--border); border-radius: 6px; background: var(--surface); color: var(--text); font-size: 14px; }
.quick { padding: 8px 16px; border: 1px solid var(--border); border-radius: 6px; background: var(--surface2); color: var(--text); cursor: pointer; font-size: 13px; }
.quick:hover { background: var(--accent); color: #fff; }
.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.card { padding: 20px; border: 1px solid var(--border); border-radius: 12px; background: var(--surface); }
.card-title { font-weight: 600; margin-bottom: 16px; }
.planet-grid { display: flex; flex-direction: column; gap: 6px; }
.planet-row { display: flex; justify-content: space-between; align-items: center; padding: 6px 0; border-bottom: 1px solid var(--border); }
.planet { display: flex; align-items: center; gap: 8px; }
.retro { font-size: 10px; padding: 1px 4px; border-radius: 4px; background: var(--danger); color: #fff; }
.sign-pos { color: var(--text2); font-size: 13px; }
.moon-row { margin-top: 16px; padding-top: 16px; border-top: 1px solid var(--border); color: var(--text2); font-size: 13px; }
.wheel-container { display: flex; flex-direction: column; align-items: center; gap: 12px; }
.note { margin-top: 16px; font-size: 11px; }
@media (max-width: 768px) { .grid-2 { grid-template-columns: 1fr; } }
</style>
