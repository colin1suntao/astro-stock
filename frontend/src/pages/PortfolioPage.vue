<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api, type AstroScore, type Holding, isLoggedIn } from '@/api'
import { useRouter } from 'vue-router'

const router = useRouter()
const holdings = ref<Holding[]>([])
const stats = ref<Array<Holding & { price: number; value: number; pnl_pct: number; score: AstroScore | null }>>([])
const loading = ref(true)
const error = ref('')

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

async function add() {
  try {
    await api.addHolding(newTicker.value.toUpperCase(), newShares.value, newEntry.value)
    await load()
  } catch (e) { error.value = (e as Error).message }
}

async function remove(id: string) {
  try { await api.deleteHolding(id); await load() }
  catch (e) { error.value = (e as Error).message }
}

onMounted(load)

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
</style>
