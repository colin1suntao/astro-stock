<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { api, type PlanetPosition, type Aspect, type MoonPhase } from '@/api'
import { useThemeStore } from '@/stores/theme'

const theme = useThemeStore()
onMounted(() => theme.init())

const positions = ref<PlanetPosition[]>([])
const aspects = ref<Aspect[]>([])
const moon = ref<MoonPhase | null>(null)
const interpretation = ref<{ text: string; tokens: number | null } | null>(null)
const interpLoading = ref(false)
const interpError = ref('')
const alerts = ref<Array<{ id: string; text: string; orb: number; aspect_type: string; read: boolean }>>([])
const loading = ref(true)
const error = ref('')

// 行星颜色映射（对齐后端 --planet-* tokens）
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

// 相位轮 SVG — 7 颗古典行星（Sun..Saturn）的位置坐标
const WHEEL_CX = 170, WHEEL_CY = 170, WHEEL_R = 150
const classicalPlanets = ['sun', 'moon', 'mercury', 'venus', 'mars', 'jupiter', 'saturn']

const wheelPositions = computed(() => {
  // 用行星黄经 longitude 映射到轮上角度（0°白羊在顶部，顺时针）
  const out: Array<{ planet: string; x: number; y: number }> = []
  for (const p of positions.value) {
    if (!classicalPlanets.includes(p.planet)) continue
    const angle = (p.longitude - 90) * (Math.PI / 180) // 顶部为 0°
    out.push({
      planet: p.planet,
      x: WHEEL_CX + WHEEL_R * Math.cos(angle),
      y: WHEEL_CY + WHEEL_R * Math.sin(angle),
    })
  }
  return out
})

const aspectLines = computed(() => {
  // 相位轮只画古典 7 星之间的连线
  const posMap = new Map(wheelPositions.value.map(p => [p.planet, p]))
  return aspects.value
    .filter(a => classicalPlanets.includes(a.planet1) && classicalPlanets.includes(a.planet2))
    .map(a => {
      const p1 = posMap.get(a.planet1)!
      const p2 = posMap.get(a.planet2)!
      const color = a.influence === 'positive' ? 'var(--success)' :
        a.influence === 'negative' ? 'var(--danger)' : 'var(--text3)'
      const dash = a.type === 'trine' || a.type === 'sextile' ? '6 3' : 'none'
      return { x1: p1.x, y1: p1.y, x2: p2.x, y2: p2.y, color, dash, type: a.type }
    })
})

// 元素平衡 — MVP：按行星所在星座的元素分类计数
const elementStats = computed(() => {
  const fireSigns = ['白羊座', '狮子座', '射手座']
  const earthSigns = ['金牛座', '处女座', '摩羯座']
  const airSigns = ['双子座', '天秤座', '水瓶座']
  const waterSigns = ['巨蟹座', '天蝎座', '双鱼座']
  const counts = { fire: 0, earth: 0, air: 0, water: 0 }
  for (const p of positions.value) {
    if (fireSigns.includes(p.sign)) counts.fire++
    else if (earthSigns.includes(p.sign)) counts.earth++
    else if (airSigns.includes(p.sign)) counts.air++
    else if (waterSigns.includes(p.sign)) counts.water++
  }
  const total = positions.value.length || 1
  return [
    { key: 'fire', icon: '🔥', label: '火象', pct: Math.round(counts.fire / total * 100), color: '#f87171' },
    { key: 'earth', icon: '🌍', label: '土象', pct: Math.round(counts.earth / total * 100), color: '#34d399' },
    { key: 'air', icon: '💨', label: '风象', pct: Math.round(counts.air / total * 100), color: '#60a5fa' },
    { key: 'water', icon: '🌊', label: '水象', pct: Math.round(counts.water / total * 100), color: '#818cf8' },
  ]
})

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [p, a, m] = await Promise.all([
      api.planetPositions(), api.aspects(), api.moonPhase(),
    ])
    positions.value = p
    aspects.value = a
    moon.value = m
  } catch (e) {
    error.value = (e as Error).message
  } finally {
    loading.value = false
  }
}
onMounted(() => { load(); loadAlerts() })

async function loadInterpret() {
  interpLoading.value = true; interpError.value = ''
  try {
    const d = await api.interpret('当前整体天象对科技板块的倾向')
    interpretation.value = { text: d.text, tokens: d.tokens }
  } catch (e) { interpError.value = (e as Error).message }
  finally { interpLoading.value = false }
}

async function loadAlerts() {
  try { alerts.value = await api.listAlerts(true) as any }
  catch { alerts.value = [] } // 未登录静默跳过
}
async function dismissAlert(id: string) {
  await api.markAlertRead(id)
  alerts.value = alerts.value.filter(a => a.id !== id)
}

const zodiacSymbols = ['♈', '♉', '♊', '♋', '♌', '♍', '♎', '♏', '♐', '♑', '♒', '♓']
</script>

<template>
  <div class="theme-init" :data-theme="theme.current">
    <section>
      <h1>📊 仪表盘</h1>
      <!-- 今日过运提醒 -->
      <div v-if="alerts.length" class="alert-bar">
        <span class="alert-icon">🔔 今日过运提醒（{{ alerts.length }}）</span>
        <div class="alert-list">
          <div v-for="a in alerts" :key="a.id" class="alert-chip" :class="{ warn: a.aspect_type === 'square' || a.aspect_type === 'opposition', good: a.aspect_type === 'trine' || a.aspect_type === 'sextile' }">
            <span class="chip-text">{{ a.text }}</span>
            <button class="chip-x" @click="dismissAlert(a.id)">×</button>
          </div>
        </div>
      </div>
      <p v-if="loading" class="muted">加载中…</p>
      <p v-if="error" class="error">❌ {{ error }} <button @click="load">重试</button></p>

      <div v-if="!loading && !error" class="grid-2">
        <!-- 当前行星位置 -->
        <div class="card">
          <div class="card-title">🌌 当前行星位置</div>
          <div class="planet-grid">
            <div v-for="p in positions" :key="p.planet" class="planet-row">
              <div class="planet">
                <span class="dot" :style="{ background: planetColor[p.planet] }"></span>
                {{ planetSymbol[p.planet] }} {{ planetName[p.planet] }}
                <span v-if="p.is_retrograde" class="retro">逆</span>
              </div>
              <span class="sign-pos">{{ p.sign_symbol }} {{ p.sign }} {{ p.degree_fmt }}</span>
            </div>
          </div>
        </div>

        <!-- 元素能量平衡 + 月相 -->
        <div class="card">
          <div class="card-title">🔥 元素能量平衡</div>
          <div class="element-gauge">
            <div v-for="el in elementStats" :key="el.key" class="elem">
              <span class="icon">{{ el.icon }}</span>
              <span class="label">{{ el.label }}</span>
              <span class="pct">{{ el.pct }}%</span>
              <div class="elem-bar">
                <div class="fill" :style="{ width: el.pct + '%', background: el.color }"></div>
              </div>
            </div>
          </div>
          <div v-if="moon" class="moon-section">
            <div class="flex-between">
              <div class="card-title" style="margin-bottom:0">🌙 月亮相位</div>
              <span class="muted">{{ moon.name }} · {{ moon.illumination_pct }}%</span>
            </div>
            <div class="moon-visual">
              <svg width="120" height="60" viewBox="0 0 120 60">
                <circle cx="60" cy="30" r="28" fill="none" stroke="var(--border)" stroke-width="0.5" />
                <circle cx="60" cy="30" r="26" fill="var(--surface2)" />
                <circle cx="60" cy="30" r="26" fill="var(--planet-moon, #c7d2fe)" :opacity="moon.illumination_pct / 100" />
              </svg>
            </div>
          </div>
        </div>

        <!-- 相位轮 -->
        <div class="card full-width">
          <div class="card-title">🔯 当前相位轮</div>
          <div class="wheel-container">
            <svg width="340" height="340" viewBox="0 0 340 340">
              <!-- 12 星座环 -->
              <circle :cx="WHEEL_CX" :cy="WHEEL_CY" :r="WHEEL_R" fill="none" stroke="var(--border)" stroke-width="1" />
              <circle :cx="WHEEL_CX" :cy="WHEEL_CY" :r="WHEEL_R - 30" fill="none" stroke="var(--border)" stroke-width="0.5" stroke-dasharray="4 6" />
              <g fill="var(--text3)" font-size="11" text-anchor="middle">
                <text v-for="(sym, i) in zodiacSymbols" :key="i"
                  :x="WHEEL_CX + (WHEEL_R - 15) * Math.cos((i * 30 - 90) * Math.PI / 180)"
                  :y="WHEEL_CY + (WHEEL_R - 15) * Math.sin((i * 30 - 90) * Math.PI / 180) + 4">{{ sym }}</text>
              </g>
              <!-- 相位连线 -->
              <g stroke-width="1.5" opacity="0.7">
                <line v-for="(l, i) in aspectLines" :key="i"
                  :x1="l.x1" :y1="l.y1" :x2="l.x2" :y2="l.y2"
                  :stroke="l.color" :stroke-dasharray="l.dash" />
              </g>
              <!-- 行星点 -->
              <g>
                <circle v-for="wp in wheelPositions" :key="wp.planet"
                  :cx="wp.x" :cy="wp.y" r="10" :fill="planetColor[wp.planet]" opacity="0.9" />
                <text v-for="wp in wheelPositions" :key="wp.planet + '-t'"
                  :x="wp.x" :y="wp.y + 4" text-anchor="middle" fill="#000" font-size="10" font-weight="700">{{ planetSymbol[wp.planet] }}</text>
              </g>
            </svg>
            <div class="wheel-legend">
              <span><span class="legend-line" style="background:var(--success)"></span> 三分/六分（和谐）</span>
              <span><span class="legend-line" style="background:var(--danger)"></span> 四分/对冲（张力）</span>
            </div>
          </div>
        </div>
        <!-- AI 占星解读 -->
        <div class="card ai-card">
          <div class="card-title">✨ AI 占星解读</div>
          <p v-if="interpLoading" class="muted">🔮 星象推演中…（推理模型需 ~10-30 秒）</p>
          <p v-if="interpError" class="error">❌ {{ interpError }} <button @click="loadInterpret">重试</button></p>
          <div v-if="interpretation && !interpLoading" class="interp-body">
            <p class="interp-text">{{ interpretation.text }}</p>
            <p class="interp-meta muted">LongCat-2.0 · {{ interpretation.tokens }} tokens · <button class="refresh" @click="loadInterpret">重新生成</button></p>
          </div>
          <button v-if="!interpretation && !interpLoading && !interpError" class="interp-trigger" @click="loadInterpret">✨ 生成今日天象解读</button>
        </div>

      </div>
    </section>
  </div>
</template>

<style scoped>
.grid-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}
.full-width { grid-column: 1 / -1; }
.card {
  padding: 20px;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: var(--surface);
}
.card-title { font-weight: 600; margin-bottom: 16px; }
.muted { color: var(--text2); }
.error { color: var(--danger); }
.error button { margin-left: 8px; padding: 4px 12px; cursor: pointer; }

.planet-grid { display: flex; flex-direction: column; gap: 6px; }
.planet-row {
  display: flex; justify-content: space-between; align-items: center;
  padding: 6px 0; border-bottom: 1px solid var(--border);
}
.planet { display: flex; align-items: center; gap: 8px; }
.dot { width: 10px; height: 10px; border-radius: 50%; display: inline-block; }
.retro {
  font-size: 10px; padding: 1px 4px; border-radius: 4px;
  background: var(--danger); color: #fff;
}
.sign-pos { color: var(--text2); font-size: 13px; }

.element-gauge { display: flex; flex-direction: column; gap: 10px; }
.elem { display: grid; grid-template-columns: 24px 40px 40px 1fr; align-items: center; gap: 8px; }
.elem-bar { height: 8px; background: var(--surface2); border-radius: 4px; overflow: hidden; }
.fill { height: 100%; transition: width 0.6s ease; }

.moon-section { margin-top: 20px; }
.flex-between { display: flex; justify-content: space-between; align-items: center; }
.moon-visual { display: flex; justify-content: center; margin: 12px 0; }

.wheel-container { display: flex; flex-direction: column; align-items: center; gap: 12px; }
.wheel-legend { display: flex; gap: 16px; font-size: 12px; color: var(--text2); }
.legend-line { display: inline-block; width: 16px; height: 2px; vertical-align: middle; margin-right: 4px; }

@media (max-width: 768px) {
  .grid-2 { grid-template-columns: 1fr; }
}
.alert-bar { margin-bottom: 16px; padding: 12px 16px; border: 1px solid var(--accent); border-radius: 8px; background: var(--surface2); }
.alert-icon { font-weight: 600; color: var(--accent); }
.alert-list { display: flex; flex-direction: column; gap: 8px; margin-top: 10px; }
.alert-chip { display: flex; align-items: center; justify-content: space-between; gap: 8px; padding: 6px 12px; border-radius: 6px; background: var(--surface); border: 1px solid var(--border); }
.alert-chip.warn { border-color: var(--danger); }
.alert-chip.good { border-color: var(--success); }
.chip-text { font-size: 13px; line-height: 1.5; }
.chip-x { background: none; border: none; color: var(--text2); cursor: pointer; font-size: 18px; padding: 0 4px; }
.chip-x:hover { color: var(--danger); }
.ai-card { grid-column: 1 / -1; }
.interp-body { display: flex; flex-direction: column; gap: 12px; }
.interp-text { line-height: 1.7; color: var(--text); }
.interp-meta { font-size: 12px; }
.interp-meta .refresh { background: none; border: none; color: var(--accent); cursor: pointer; font-size: 12px; padding: 0; }
.interp-trigger { padding: 12px 24px; border: 1px solid var(--accent); border-radius: 8px; background: var(--surface2); color: var(--accent); cursor: pointer; font-size: 14px; }
.interp-trigger:hover { background: var(--accent); color: #fff; }
</style>
