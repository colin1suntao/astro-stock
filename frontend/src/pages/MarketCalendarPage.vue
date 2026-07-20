<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { api, type PlanetPosition, type Aspect, type MoonPhase } from '@/api'

// P5-2: AI 投资日历 — 全年重要相位日替当前相位聚合
const year = ref(new Date().getFullYear())
type CalendarDay = {
  date: string
  aspects: Aspect[]
  mood: string
  mood_emoji: string
  intensity: number
}
const calendar = ref<{ year: number; days: CalendarDay[]; note: string } | null>(null)
const calLoading = ref(false)
const calError = ref('')
const selectedDay = ref<CalendarDay | null>(null)

// 保留原 MVP 段：当前相位聚合 + 行星位置 + 月相（侧栏辅助）
const moon = ref<MoonPhase | null>(null)
const positions = ref<PlanetPosition[]>([])
const upcomingAspects = ref<Aspect[]>([])
const loading = ref(true)
const error = ref('')

const typeLabel: Record<string, string> = {
  conjunction: '合相', opposition: '对冲', trine: '三分', square: '四分', sextile: '六分',
}

// 日历按月分组 — 12 月网格，每月显相位日 chip
const byMonth = computed(() => {
  if (!calendar.value) return []
  const months: Array<{ month: number; days: typeof calendar.value extends null ? never : calendar.value['days'] }> = []
  for (let m = 0; m < 12; m++) {
    const days = calendar.value.days.filter(d => parseInt(d.date.slice(5, 7)) === m + 1)
    months.push({ month: m + 1, days })
  }
  return months
})

// P5-3c: localStorage 客户端缓存 + SWR（陈旧期内用缓存否则重取）
// 陈旧 24h 内直用 localStorage，超则后台静默重取（SWR stale-while-revalidate）
const SWR_STALE_MS = 24 * 60 * 60 * 1000  // 24h 陈旧期
const calCacheKey = (y: number) => `sky-cal-${y}`
type CalPayload = { year: number; days: CalendarDay[]; note: string }
type CalCacheEntry = { ts: number; payload: CalPayload }

function readCalCache(y: number): CalPayload | null {
  try {
    const raw = localStorage.getItem(calCacheKey(y))
    if (!raw) return null
    return JSON.parse(raw).payload as CalPayload
  } catch { return null }
}

function writeCalCache(y: number, payload: CalPayload) {
  try {
    localStorage.setItem(calCacheKey(y), JSON.stringify({ ts: Date.now(), payload }))
  } catch { /* quota exceeded — silently skip */ }
}

function calCacheAgeMs(y: number): number {
  try {
    const raw = localStorage.getItem(calCacheKey(y))
    if (!raw) return Infinity
    return Date.now() - (JSON.parse(raw).ts as number)
  } catch { return Infinity }
}

async function loadCalendar() {
  calLoading.value = true; calError.value = ''
  // P5-3c: 先显 localStorage 陈旧缓存（若 <24h），后台静默重取
  const cached = readCalCache(year.value)
  if (cached) {
    calendar.value = cached
    selectedDay.value = null
    if (calCacheAgeMs(year.value) < SWR_STALE_MS) {
      calLoading.value = false  // 陈旧期内用缓存，不再 loading
      return  // 跳后台重取
    }
  }
  // miss 或陈旧超 → 真取
  try {
    const payload = await api.skyCalendar(year.value)
    calendar.value = payload
    writeCalCache(year.value, payload)
    selectedDay.value = null
  } catch (e) { calError.value = (e as Error).message }
  finally { calLoading.value = false }
}

async function loadLegacy() {
  loading.value = true; error.value = ''
  try {
    const [m, p, a] = await Promise.all([api.moonPhase(), api.planetPositions(), api.aspects()])
    moon.value = m
    positions.value = p
    upcomingAspects.value = a.slice(0, 5)
  } catch (e) { error.value = (e as Error).message }
  finally { loading.value = false }
}

onMounted(() => { loadCalendar(); loadLegacy() })

function prevYear() { year.value--; loadCalendar() }
function nextYear() { year.value++; loadCalendar() }
function pickToday() { year.value = new Date().getFullYear(); loadCalendar() }
</script>

<template>
  <section>
    <div class="topbar">
      <h1>📅 AI 投资日历</h1>
      <span v-if="moon" class="muted">{{ moon.name }} · {{ moon.illumination_pct }}%</span>
    </div>
    <p class="muted intro">全年重要相位日（orb≤2° 精确相位）+ 每日投资倾向 — 替当前相位聚合，可点日查详情</p>

    <!-- 年导航 -->
    <div class="year-bar">
      <button @click="prevYear">← {{ year - 1 }}</button>
      <strong class="year">{{ year }}</strong>
      <button @click="nextYear">{{ year + 1 }} →</button>
      <button class="today" @click="pickToday">今日</button>
      <span v-if="calLoading" class="muted">推演中…（全年逐日算约 5s）</span>
      <span v-else-if="calendar" class="muted">{{ calendar.days.length }} 个相位日</span>
    </div>
    <p v-if="calError" class="error">❌ {{ calError }} <button @click="loadCalendar">重试</button></p>

    <!-- 12 月日历网格 -->
    <div v-if="calendar && !calLoading" class="months-grid">
      <div v-for="m in byMonth" :key="m.month" class="month-card">
        <div class="month-title">{{ m.month }}月</div>
        <div v-if="!m.days.length" class="muted empty">无精确相位</div>
        <div v-else class="day-chips">
          <button v-for="d in m.days" :key="d.date"
                  class="day-chip"
                  :class="{ high: d.intensity >= 0.7, med: d.intensity >= 0.3 && d.intensity < 0.7 }"
                  :title="`${d.date} · ${d.mood}`"
                  @click="selectedDay = d">
            <span class="chip-day">{{ parseInt(d.date.slice(8)) }}</span>
            <span class="chip-emoji">{{ d.mood_emoji }}</span>
          </button>
        </div>
      </div>
    </div>

    <!-- 选中日详情抽屉 -->
    <div v-if="selectedDay" class="day-detail card">
      <div class="detail-head">
        <strong>{{ selectedDay.date }} {{ selectedDay.mood_emoji }} {{ selectedDay.mood }}</strong>
        <button class="close" @click="selectedDay = null">×</button>
      </div>
      <div class="intensity-bar">
        <span>相位强度</span>
        <div class="bar-wrap"><div class="bar-fill" :style="{ width: selectedDay.intensity * 100 + '%' }" /></div>
        <span class="muted">{{ selectedDay.intensity }}</span>
      </div>
      <div class="aspects-list">
        <div v-for="(a, i) in selectedDay.aspects" :key="i" class="aspect-row">
          <span class="as">{{ a.planet1 }} {{ typeLabel[a.type] }} {{ a.planet2 }}</span>
          <span class="orb muted">orb {{ a.orb }}°</span>
          <span :class="a.influence === 'positive' ? 'pos' : a.influence === 'negative' ? 'neg' : 'neu'">
            {{ a.influence === 'positive' ? '🟢 和谐' : a.influence === 'negative' ? '🔴 张力' : '⚪ 中性' }}
          </span>
        </div>
      </div>
    </div>

    <!-- 侧栏：当前相位聚合 + 行星位置（保留 MVP 辅助） -->
    <div v-if="!loading && !error" class="grid-2">
      <div class="card">
        <div class="card-title">本周重要天象（当前相位聚合）</div>
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
    <p v-if="calendar" class="note muted">{{ calendar.note }}</p>
  </section>
</template>

<style scoped>
.topbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.muted { color: var(--text2); }
.error { color: var(--danger); }
.error button { margin-left: 8px; padding: 4px 12px; cursor: pointer; }
.intro { margin-bottom: 16px; font-size: 13px; }

.year-bar { display: flex; gap: 12px; align-items: center; margin-bottom: 16px; flex-wrap: wrap; }
.year-bar button { padding: 6px 14px; border: 1px solid var(--border); border-radius: 6px; background: var(--surface2); color: var(--text); cursor: pointer; font-size: 13px; }
.year-bar button:hover { background: var(--accent); color: #fff; }
.year { font-size: 22px; color: var(--accent); }
.today { background: var(--surface); }

.months-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 12px; margin-bottom: 16px; }
.month-card { padding: 12px 14px; border: 1px solid var(--border); border-radius: 10px; background: var(--surface); }
.month-title { font-weight: 600; margin-bottom: 8px; color: var(--text2); font-size: 13px; }
.empty { font-size: 12px; }
.day-chips { display: flex; flex-wrap: wrap; gap: 4px; }
.day-chip { display: flex; flex-direction: column; align-items: center; gap: 1px; padding: 3px 6px; border: 1px solid var(--border); border-radius: 5px; background: var(--surface2); cursor: pointer; font-size: 11px; min-width: 30px; }
.day-chip:hover { border-color: var(--accent); }
.day-chip.high { border-color: var(--danger); background: color-mix(in srgb, var(--danger) 15%, var(--surface2)); }
.day-chip.med { border-color: var(--warning); }
.chip-day { font-weight: 700; color: var(--text); }
.chip-emoji { font-size: 10px; }

.day-detail { margin-bottom: 16px; }
.detail-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.close { background: none; border: none; color: var(--text2); cursor: pointer; font-size: 20px; padding: 0 4px; }
.close:hover { color: var(--danger); }
.intensity-bar { display: grid; grid-template-columns: 80px 1fr 40px; align-items: center; gap: 12px; margin-bottom: 14px; font-size: 12px; }
.bar-wrap { height: 8px; background: var(--surface2); border-radius: 4px; overflow: hidden; }
.bar-fill { height: 100%; background: var(--accent); transition: width 0.5s; }
.aspects-list { display: flex; flex-direction: column; gap: 6px; }
.aspect-row { display: flex; justify-content: space-between; align-items: center; padding: 6px 0; border-bottom: 1px solid var(--border); font-size: 13px; }
.aspect-row .as { font-weight: 500; }
.orb { font-size: 11px; }
.pos { color: var(--success); }
.neg { color: var(--danger); }
.neu { color: var(--text3); }

.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.card { padding: 20px; border: 1px solid var(--border); border-radius: 12px; background: var(--surface); }
.card-title { font-weight: 600; margin-bottom: 16px; }
.event-list { display: flex; flex-direction: column; gap: 12px; }
.event-row { padding: 12px; border-radius: 8px; background: var(--surface2); }
.event-info .title { font-weight: 600; }
.event-info .desc { font-size: 13px; margin-top: 4px; }
.planet-list { display: flex; flex-direction: column; gap: 6px; }
.planet-row { display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid var(--border); }
.note { margin-top: 16px; font-size: 11px; }
@media (max-width: 768px) {
  .grid-2 { grid-template-columns: 1fr; }
  .months-grid { grid-template-columns: 1fr; }
}
</style>
