<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { api, type AstroScore } from '@/api'

const props = defineProps<{ ticker: string }>()

const score = ref<AstroScore | null>(null)
const quote = ref<{ name: string; price: number; change_pct: number; sector_label: string | null } | null>(null)
const pred = ref<{ bars: Array<{ day_offset: number; confidence: number }> } | null>(null)
const interpretation = ref<{ text: string; tokens: number | null } | null>(null)
const interpLoading = ref(false)
const interpError = ref('')
const loading = ref(true)
const error = ref('')

// 评分环 SVG — 圆形进度环
const ringRadius = 38, ringStroke = 6
const ringDash = computed(() => {
  if (!score.value) return '0 999'
  const circumference = 2 * Math.PI * ringRadius
  const filled = (score.value.score / 100) * circumference
  return `${filled} ${circumference}`
})
const scoreColor = computed(() =>
  score.value?.direction === 'bull' ? 'var(--success)' :
  score.value?.direction === 'bear' ? 'var(--danger)' : 'var(--warning)'
)

// 7 日柱状图 — confidence 映射到柱高（0-100 → 0-100%）
const predBars = computed(() => pred.value?.bars ?? [])

async function load() {
  loading.value = true; error.value = ''
  try {
    const [s, q, p] = await Promise.all([
      api.astroScore(props.ticker), api.quote(props.ticker), api.prediction(props.ticker),
    ])
    score.value = s
    quote.value = q
    pred.value = p
  } catch (e) { error.value = (e as Error).message }
  finally { loading.value = false }
}
onMounted(load)

async function loadInterpret() {
  interpLoading.value = true; interpError.value = ''
  try {
    const d = await api.interpret(`当前天象对 ${props.ticker} 的综合影响`, props.ticker)
    interpretation.value = { text: d.text, tokens: d.tokens }
  } catch (e) { interpError.value = (e as Error).message }
  finally { interpLoading.value = false }
}
</script>

<template>
  <section>
    <div class="topbar">
      <h1><span class="subtitle">占星分析 /</span> {{ ticker }}</span></h1>
      <span v-if="quote" class="muted">{{ quote.name }} · ${{ quote.price }} ({{ quote.change_pct }}%)</span>
    </div>
    <p v-if="loading" class="muted">加载中…</p>
    <p v-if="error" class="error">❌ {{ error }} <button @click="load">重试</button></p>

    <div v-if="!loading && !error" class="grid-2">
      <!-- 综合评分环 -->
      <div class="card">
        <div class="card-title">🔯 综合占星评分</div>
        <div v-if="score" class="score-block">
          <svg width="96" height="96" viewBox="0 0 96 96">
            <circle :cx="48" :cy="48" :r="ringRadius" fill="none" stroke="var(--surface2)" :stroke-width="ringStroke" />
            <circle :cx="48" :cy="48" :r="ringRadius" fill="none" :stroke="scoreColor" :stroke-width="ringStroke"
              :stroke-dasharray="ringDash" stroke-linecap="round" transform="rotate(-90 48 48)" />
            <text x="48" y="54" text-anchor="middle" :fill="scoreColor" font-size="32" font-weight="700">{{ score.score }}</text>
          </svg>
          <div class="score-meta">
            <div class="dir">{{ score.direction_emoji }} {{ score.direction_label }}</div>
            <div class="breakdown">
              <span class="badge bull">行星 +{{ score.breakdown.planetary }}</span>
              <span class="badge bull">相位 +{{ score.breakdown.aspect }}</span>
              <span class="badge neutral">过运 +{{ score.breakdown.transit }}</span>
              <span class="badge neutral">个人 +{{ score.breakdown.personal }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 7 日预测柱状图 -->
      <div class="card">
        <div class="card-title">📈 7 日预测趋势</div>
        <div class="bars">
          <div v-for="b in predBars" :key="b.day_offset" class="bar-wrap">
            <div class="bar" :style="{ height: Math.max(b.confidence, 3) + '%', background: b.confidence >= 60 ? 'var(--success)' : b.confidence >= 40 ? 'var(--warning)' : 'var(--danger)' }"></div>
            <span class="bar-label">{{ b.confidence }}</span>
          </div>
        </div>
        <div class="bar-axis muted">今日 → +6日</div>
      </div>

      <!-- AI 占星解读 -->
      <div class="card ai-card">
        <div class="card-title">✨ AI 占星解读</div>
        <p v-if="interpLoading" class="muted">🔮 推演中…（推理模型 ~10-30 秒）</p>
        <p v-if="interpError" class="error">❌ {{ interpError }} <button @click="loadInterpret">重试</button></p>
        <div v-if="interpretation && !interpLoading" class="interp-body">
          <p class="interp-text">{{ interpretation.text }}</p>
          <p class="interp-meta muted">LongCat-2.0 · {{ interpretation.tokens }} tokens · <button class="refresh" @click="loadInterpret">重新生成</button></p>
        </div>
        <button v-if="!interpretation && !interpLoading && !interpError" class="interp-trigger" @click="loadInterpret">✨ 生成 {{ ticker }} 天象解读</button>
      </div>
    </div>
  </section>
</template>

<style scoped>
.topbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.subtitle { color: var(--text2); font-weight: 400; }
.muted { color: var(--text2); }
.error { color: var(--danger); }
.error button { margin-left: 8px; padding: 4px 12px; cursor: pointer; }
.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.card { padding: 20px; border: 1px solid var(--border); border-radius: 12px; background: var(--surface); }
.card-title { font-weight: 600; margin-bottom: 16px; }
.score-block { display: flex; align-items: center; gap: 24px; flex-wrap: wrap; }
.score-meta { display: flex; flex-direction: column; gap: 12px; }
.dir { font-weight: 600; font-size: 16px; }
.breakdown { display: flex; gap: 8px; flex-wrap: wrap; }
.badge { padding: 4px 10px; border-radius: 8px; font-size: 12px; }
.badge.bull { background: rgba(52,211,153,0.15); color: var(--success); }
.badge.neutral { background: rgba(167,139,250,0.15); color: var(--accent); }
.bars { height: 100px; display: flex; align-items: flex-end; gap: 6px; padding-top: 16px; }
.bar-wrap { flex: 1; display: flex; flex-direction: column; align-items: center; position: relative; }
.bar { width: 100%; border-radius: 4px 4px 0 0; transition: height 0.6s ease; min-height: 3px; }
.bar-label { position: absolute; top: -16px; font-size: 10px; color: var(--text2); }
.bar-axis { font-size: 12px; margin-top: 8px; text-align: center; }
@media (max-width: 768px) { .grid-2 { grid-template-columns: 1fr; } }
.ai-card { grid-column: 1 / -1; }
.interp-body { display: flex; flex-direction: column; gap: 12px; }
.interp-text { line-height: 1.7; color: var(--text); }
.interp-meta { font-size: 12px; }
.interp-meta .refresh { background: none; border: none; color: var(--accent); cursor: pointer; font-size: 12px; padding: 0; }
.interp-trigger { padding: 12px 24px; border: 1px solid var(--accent); border-radius: 8px; background: var(--surface2); color: var(--accent); cursor: pointer; font-size: 14px; }
.interp-trigger:hover { background: var(--accent); color: #fff; }
</style>
