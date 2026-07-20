<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { api, type AstroScore, type Holding, isLoggedIn } from '@/api'
import { useRouter } from 'vue-router'

const router = useRouter()
const holdings = ref<Holding[]>([])
const stats = ref<Array<Holding & { price: number; value: number; pnl_pct: number; score: AstroScore | null }>>([])
const loading = ref(true)
const error = ref('')

// P4-6b: 占星归因
const attrib = ref<{
  user_name: string
  holdings: Array<{
    ticker: string
    shares: number
    entry_price: number
    current_price: number
    pnl: number
    pnl_pct: number
    astro_score: number
    direction: 'bull' | 'bear' | 'neutral'
    direction_label: string
    direction_emoji: string
    breakdown: { planetary: number; aspect: number; transit: number; personal: number }
    planetary_linkage: string
  }>
  total_pnl: number
  planet_exposure: Record<string, number>
  note: string
} | null>(null)
const attribLoading = ref(false)
const attribError = ref('')

const planetName: Record<string, string> = {
  sun: '太阳', moon: '月亮', mercury: '水星', venus: '金星', mars: '火星',
  jupiter: '木星', saturn: '土星', uranus: '天王', neptune: '海王', pluto: '冥王',
}
const planetSymbol: Record<string, string> = {
  sun: '☉', moon: '☽', mercury: '☿', venus: '♀', mars: '♂',
  jupiter: '♃', saturn: '♄', uranus: '♅', neptune: '♆', pluto: '♇',
}
const exposureSorted = computed(() => {
  if (!attrib.value?.planet_exposure) return []
  return Object.entries(attrib.value.planet_exposure)
    .map(([p, v]) => ({ planet: p, value: v, name: planetName[p] || p, symbol: planetSymbol[p] || '' }))
    .sort((a, b) => b.value - a.value)
})
const exposureMax = computed(() => Math.max(1, ...exposureSorted.value.map(e => e.value)))

// 新增持仓表单
const newTicker = ref('NVDA')
const newShares = ref(10)
const newEntry = ref(100)

async function load() {
  loading.value = true; error.value = ''
  if (!isLoggedIn()) { router.push('/auth'); return }
  try {
    holdings.value = await api.listHoldings()
    const out: typeof stats.value = []
    for (const h of holdings.value) {
      const [q, s] = await Promise.all([api.quote(h.ticker), api.astroScore(h.ticker)])
      out.push({
        ...h,
        price: q.price,
        value: Math.round(q.price * h.shares),
        pnl_pct: Math.round((q.price - h.entry_price) / h.entry_price * 1000) / 10,
        score: s,
      })
    }
    stats.value = out
  } catch (e) { error.value = (e as Error).message }
  finally { loading.value = false }
}

async function loadAttrib() {
  attribLoading.value = true; attribError.value = ''
  try { attrib.value = await api.attribution() }
  catch (e) { attribError.value = (e as Error).message }
  finally { attribLoading.value = false }
}

async function add() {
  try {
    await api.addHolding(newTicker.value.toUpperCase(), newShares.value, newEntry.value)
    await Promise.all([load(), loadAttrib()])
  } catch (e) { error.value = (e as Error).message }
}

async function remove(id: string) {
  try { await api.deleteHolding(id); await Promise.all([load(), loadAttrib()]) }
  catch (e) { error.value = (e as Error).message }
}

onMounted(() => { load(); loadAttrib() })

const totalValue = () => stats.value.reduce((s, h) => s + h.value, 0)
const scoreColor = (s: AstroScore | null) =>
  s?.direction === 'bull' ? 'var(--success)' : s?.direction === 'bear' ? 'var(--danger)' : 'var(--warning)'
</script>

<template>
  <section>
    <div class="topbar">
      <h1>💼 投资组合</h1>
      <span v-if="stats.length" class="muted">总市值 <strong style="color:var(--success)">${{ totalValue().toLocaleString() }}</strong></span>
    </div>
    <p v-if="loading" class="muted">加载中…</p>
    <p v-if="error" class="error">❌ {{ error }} <button @click="load">重试</button></p>

    <!-- 新增持仓 -->
    <div class="card add-form">
      <div class="card-title">➕ 新增持仓</div>
      <div class="inputs">
        <input v-model="newTicker" placeholder="Ticker">
        <input v-model.number="newShares" type="number" placeholder="股数">
        <input v-model.number="newEntry" type="number" placeholder="入场价">
        <button @click="add">添加</button>
      </div>
    </div>

    <div v-if="!loading" class="card">
      <div class="card-title">📋 持仓列表（{{ stats.length }}）</div>
      <table v-if="stats.length" class="hold-table">
        <thead><tr><th>股票</th><th>持仓</th><th>入场价</th><th>现价</th><th>市值</th><th>盈亏</th><th>占星评分</th><th></th></tr></thead>
        <tbody>
          <tr v-for="h in stats" :key="h.id">
            <td><strong>{{ h.ticker }}</strong></td>
            <td>{{ h.shares }}股</td>
            <td>${{ h.entry_price }}</td>
            <td>${{ h.price }}</td>
            <td>${{ h.value.toLocaleString() }}</td>
            <td :style="{ color: h.pnl_pct >= 0 ? 'var(--success)' : 'var(--danger)' }">{{ h.pnl_pct >= 0 ? '+' : '' }}{{ h.pnl_pct }}%</td>
            <td v-if="h.score" :style="{ color: scoreColor(h.score), fontWeight: 700 }">⭐ {{ h.score.score }} {{ h.score.direction_emoji }}</td>
            <td><button class="del" @click="remove(h.id)">×</button></td>
          </tr>
        </tbody>
      </table>
      <p v-else class="muted">暂无持仓，上方添加</p>
    </div>

    <!-- P4-6b: 占星归因卡 -->
    <div v-if="attrib" class="card attrib-card">
      <div class="card-title">✨ 占星归因 — 盈亏 vs 当下行星影响</div>
      <p v-if="attribLoading" class="muted">推演中…</p>
      <p v-if="attribError" class="error">❌ {{ attribError }} <button @click="loadAttrib">重试</button></p>
      <div v-if="!attribLoading" class="attrib-grid">
        <div v-for="h in attrib.holdings" :key="h.ticker" class="attrib-tile" :class="'dir-' + h.direction">
          <div class="tile-head">
            <strong>{{ h.ticker }}</strong>
            <span class="dir-badge">{{ h.direction_emoji }} {{ h.direction_label }}</span>
          </div>
          <div class="tile-body">
            <div class="tile-pnl" :class="{ up: h.pnl >= 0, down: h.pnl < 0 }">
              ¥{{ h.pnl.toFixed(2) }} ({{ h.pnl_pct >= 0 ? '+' : '' }}{{ h.pnl_pct }}%)
            </div>
            <div class="tile-score">占星分: <b>{{ h.astro_score }}</b></div>
            <div class="tile-linkage">{{ h.planetary_linkage }}</div>
            <div class="tile-breakdown">
              <span>行星 {{ h.breakdown.planetary }}</span>
              <span>相位 {{ h.breakdown.aspect }}</span>
              <span>过运 {{ h.breakdown.transit }}</span>
              <span>个人 {{ h.breakdown.personal }}</span>
            </div>
          </div>
        </div>
      </div>
      <div class="exposure-row">
        <div class="card-title" style="margin:12px 0 8px">🌍 风险敞口按行星分布（score×|pnl|）</div>
        <div v-if="!exposureSorted.length" class="muted">暂无敞口数据</div>
        <div v-else class="exposure-bars">
          <div v-for="e in exposureSorted" :key="e.planet" class="expo">
            <span class="expo-sym">{{ e.symbol }} {{ e.name }}</span>
            <div class="expo-bar-wrap">
              <div class="expo-fill" :style="{ width: (e.value / exposureMax * 100) + '%' }" :title="e.value.toFixed(0)" />
            </div>
            <span class="expo-val">{{ e.value.toFixed(0) }}</span>
          </div>
        </div>
      </div>
      <div class="total-pnl-row">
        <strong>总盈亏:</strong>
        <span :class="{ up: attrib.total_pnl >= 0, down: attrib.total_pnl < 0 }" class="total-pnl">
          ¥{{ attrib.total_pnl.toFixed(2) }}
        </span>
      </div>
      <p class="note muted">{{ attrib.note }}</p>
    </div>
  </section>
</template>

<style scoped>
.topbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.muted { color: var(--text2); }
.error { color: var(--danger); }
.error button { margin-left: 8px; padding: 4px 12px; cursor: pointer; }
.card { padding: 20px; border: 1px solid var(--border); border-radius: 12px; background: var(--surface); margin-bottom: 16px; }
.card-title { font-weight: 600; margin-bottom: 16px; }
.add-form .inputs { display: flex; gap: 8px; flex-wrap: wrap; }
.add-form input { padding: 8px 10px; border: 1px solid var(--border); border-radius: 6px; background: var(--bg); color: var(--text); width: 120px; }
.add-form button { padding: 8px 16px; border: none; border-radius: 6px; background: var(--accent); color: #fff; cursor: pointer; }
.hold-table { width: 100%; border-collapse: collapse; font-size: 14px; }
.hold-table th { text-align: left; padding: 10px 6px; color: var(--text2); font-weight: 500; border-bottom: 1px solid var(--border); }
.hold-table td { padding: 10px 6px; border-bottom: 1px solid var(--border); }
.del { color: var(--danger); background: none; border: none; cursor: pointer; font-size: 18px; }

/* P4-6b: 占星归因 */
.attrib-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 12px; }
.attrib-tile { padding: 14px 16px; border: 1px solid var(--border); border-radius: 8px; background: var(--surface2); }
.attrib-tile.dir-bull { border-left: 3px solid var(--success); }
.attrib-tile.dir-bear { border-left: 3px solid var(--danger); }
.attrib-tile.dir-neutral { border-left: 3px solid var(--text3); }
.tile-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.dir-badge { font-size: 11px; padding: 2px 8px; border-radius: 4px; background: var(--surface); color: var(--text2); }
.tile-body { display: flex; flex-direction: column; gap: 6px; font-size: 13px; }
.tile-pnl { font-size: 16px; font-weight: 700; }
.tile-pnl.up { color: var(--success); }
.tile-pnl.down { color: var(--danger); }
.tile-score b { color: var(--text); }
.tile-linkage { color: var(--text3); line-height: 1.5; }
.tile-breakdown { display: flex; gap: 12px; flex-wrap: wrap; font-size: 11px; color: var(--text3); padding-top: 4px; border-top: 1px dashed var(--border); }
.exposure-row { margin-top: 16px; }
.exposure-bars { display: flex; flex-direction: column; gap: 8px; }
.expo { display: grid; grid-template-columns: 90px 1fr 60px; align-items: center; gap: 10px; font-size: 12px; }
.expo-sym { color: var(--text2); }
.expo-bar-wrap { height: 10px; background: var(--surface); border-radius: 4px; overflow: hidden; }
.expo-fill { height: 100%; background: var(--accent); transition: width 0.5s ease; }
.expo-val { color: var(--text2); text-align: right; }
.total-pnl-row { display: flex; justify-content: flex-end; align-items: baseline; gap: 12px; margin-top: 16px; padding-top: 16px; border-top: 1px solid var(--border); }
.total-pnl { font-size: 20px; font-weight: 700; }
.total-pnl.up { color: var(--success); }
.total-pnl.down { color: var(--danger); }
.note { margin-top: 8px; font-size: 11px; }
@media (max-width: 640px) {
  .attrib-grid { grid-template-columns: 1fr; }
  .expo { grid-template-columns: 80px 1fr 50px; }
}
</style>
