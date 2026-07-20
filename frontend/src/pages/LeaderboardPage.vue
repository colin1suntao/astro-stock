<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { api } from '@/api'
import { useThemeStore } from '@/stores/theme'

const theme = useThemeStore()
onMounted(() => theme.init())

const board = ref<{
  computed_at: string
  entries: Array<{
    rank: number
    user_id: string
    user_name: string
    avg_score: number
    holdings_count: number
    tickers: string[]
    share_token: string
  }>
  note: string
} | null>(null)
const loading = ref(true)
const error = ref('')

const medal = computed(() => (r: number) =>
  r === 1 ? '🥇' : r === 2 ? '🥈' : r === 3 ? '🥉' : `#${r}`)

async function load() {
  loading.value = true; error.value = ''
  try {
    board.value = await api.leaderboard()
  } catch (e) { error.value = (e as Error).message }
  finally { loading.value = false }
}
onMounted(() => load())

function copyShare(e: { share_token: string; user_name: string }) {
  const url = `${window.location.origin}/share/${e.share_token}`
  navigator.clipboard?.writeText(url).then(
    () => alert(`分享链接已复制：\n${url}\n\n可发给好友看「${e.user_name}」的占星持仓`),
    () => prompt(`复制分享链接：`, url)
  )
}
</script>

<template>
  <div class="theme-init" :data-theme="theme.current">
    <section>
      <h1>🏆 占星持仓排行榜</h1>
      <p class="muted">全用户持仓占星分排行（mean astro_score），点「分享」拷链接可发给好友看你的占星持仓</p>

      <p v-if="loading" class="muted">推演中…</p>
      <p v-if="error" class="error">❌ {{ error }} <button @click="load">重试</button></p>

      <div v-if="board && !loading">
        <div v-if="!board.entries.length" class="empty card">
          <p class="muted">暂无上榜用户 — 先去「💼 投资组合」加几只持仓，再来这里看排行</p>
        </div>
        <div v-else class="board">
          <div v-for="e in board.entries" :key="e.user_id" class="row" :class="{ top: e.rank <= 3 }">
            <div class="rank">{{ medal(e.rank) }}</div>
            <div class="user">
              <div class="name">{{ e.user_name }}</div>
              <div class="tickers">
                <span v-for="t in e.tickers" :key="t" class="ticker-chip">{{ t }}</span>
                <span class="muted">· {{ e.holdings_count }} 持仓</span>
              </div>
            </div>
            <div class="score">
              <div class="score-num">{{ e.avg_score }}</div>
              <div class="score-label">占星分</div>
            </div>
            <button class="share" @click="copyShare(e)">🔗 分享</button>
          </div>
        </div>
        <p class="note muted">{{ board.note }}</p>
      </div>
    </section>
  </div>
</template>

<style scoped>
.muted { color: var(--text2); }
.error { color: var(--danger); }
.error button { margin-left: 8px; padding: 4px 12px; cursor: pointer; }
.empty { padding: 24px; border: 1px dashed var(--border); border-radius: 12px; text-align: center; }
.board { display: flex; flex-direction: column; gap: 8px; }
.row {
  display: grid; grid-template-columns: 60px 1fr 120px 80px; align-items: center; gap: 16px;
  padding: 14px 18px; border: 1px solid var(--border); border-radius: 10px; background: var(--surface);
}
.row.top { border-color: var(--accent); background: var(--surface2); }
.rank { font-size: 22px; font-weight: 700; text-align: center; }
.user .name { font-weight: 600; font-size: 14px; }
.tickers { display: flex; flex-wrap: wrap; gap: 4px; align-items: center; margin-top: 4px; font-size: 12px; }
.ticker-chip { padding: 1px 6px; border-radius: 4px; background: var(--surface2); color: var(--text2); border: 1px solid var(--border); }
.score { text-align: center; }
.score-num { font-size: 22px; font-weight: 700; color: var(--accent); }
.score-label { font-size: 11px; color: var(--text3); }
.share { padding: 6px 12px; border: 1px solid var(--border); border-radius: 6px; background: var(--surface2); color: var(--text); cursor: pointer; font-size: 12px; }
.share:hover { background: var(--accent); color: #fff; }
.note { margin-top: 16px; font-size: 11px; }
@media (max-width: 640px) {
  .row { grid-template-columns: 50px 1fr 80px; }
  .share { grid-column: 1 / -1; }
}
</style>
