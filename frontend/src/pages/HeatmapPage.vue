<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { api } from '@/api'

interface Cell {
  sector: string; sector_label: string
  planet: string; planet_name: string
  sign: string | null; sign_symbol: string | null
  is_retrograde: boolean
  strength: number
}

const sectors = ref<string[]>([])
const planets = ref<string[]>([])
const cells = ref<Cell[]>([])
const loading = ref(true)
const error = ref('')

// 行星中文名 + 符号
const planetSymbol: Record<string, string> = {
  sun: '☉', moon: '☽', mercury: '☿', venus: '♀', mars: '♂',
  jupiter: '♃', saturn: '♄',
}

// cells 按 (sector × planet) 唯一，用 lookup map 加快渲染
const cellMap = computed(() => {
  const m = new Map<string, Cell>()
  for (const c of cells.value) m.set(`${c.sector}|${c.planet}`, c)
  return m
})

// strength → 颜色（0 冷灰 → 1 暖红，过 0.7 转金）
function cellColor(s: number): string {
  if (s >= 0.85) return 'rgba(253, 224, 71, 0.85)'   // 强 → 金黄
  if (s >= 0.6) return 'rgba(52, 211, 153, 0.7)'     // 偏强 → 绿
  if (s >= 0.3) return 'rgba(167, 139, 250, 0.45)'   // 中 → 紫
  return 'rgba(100, 116, 139, 0.25)'                // 弱 → 灰
}

async function load() {
  loading.value = true; error.value = ''
  try {
    const d = await api.sectorHeatmap()
    sectors.value = d.sectors
    planets.value = d.planets
    cells.value = d.cells as any
  } catch (e) { error.value = (e as Error).message }
  finally { loading.value = false }
}
onMounted(load)
</script>

<template>
  <section>
    <div class="topbar">
      <h1>🔥 板块 × 行星 热力图</h1>
      <button @click="load">刷新</button>
    </div>
    <p v-if="loading" class="muted">加载中…</p>
    <p v-if="error" class="error">❌ {{ error }}</p>

    <div v-if="!loading && !error" class="card">
      <table class="heatmap">
        <thead>
          <tr>
            <th>板块 / 行星</th>
            <th v-for="p in planets" :key="p" class="col-head">
              <span class="sym">{{ planetSymbol[p] || '' }}</span>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="sk in sectors" :key="sk">
            <td class="row-head">
              {{ cellMap.get(`${sk}|${planets[0]}`)?.sector_label || sk }}
            </td>
            <td v-for="p in planets" :key="p"
                class="cell"
                :style="{ background: cellColor(cellMap.get(`${sk}|${p}`)?.strength || 0) }">
              <div v-if="cellMap.get(`${sk}|${p}`)?.sign" class="cell-info">
                <span class="sign">{{ cellMap.get(`${sk}|${p}`)?.sign_symbol }}</span>
                <span v-if="cellMap.get(`${sk}|${p}`)?.is_retrograde" class="retro">逆</span>
              </div>
            </td>
          </tr>
        </tbody>
      </table>

      <div class="legend">
        <span><span class="sw" style="background:rgba(253,224,71,0.85)"></span> 强助（friendly）</span>
        <span><span class="sw" style="background:rgba(52,211,153,0.7)"></span> 偏强</span>
        <span><span class="sw" style="background:rgba(167,139,250,0.45)"></span> 中性</span>
        <span><span class="sw" style="background:rgba(100,116,139,0.25)"></span> 弱/忌</span>
      </div>
    </div>
  </section>
</template>

<style scoped>
.topbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.topbar button { padding: 6px 16px; border: 1px solid var(--border); border-radius: 6px; background: var(--surface2); color: var(--text); cursor: pointer; }
.muted { color: var(--text2); }
.error { color: var(--danger); }
.card { padding: 20px; border: 1px solid var(--border); border-radius: 12px; background: var(--surface); overflow-x: auto; }
.heatmap { border-collapse: separate; border-spacing: 3px; font-size: 13px; }
.heatmap th { color: var(--text2); font-weight: 500; padding: 4px 8px; text-align: center; }
.col-head .sym { font-size: 16px; }
.row-head { color: var(--text); font-weight: 600; padding: 6px 12px; text-align: right; white-space: nowrap; }
.cell {
  width: 56px; height: 36px; text-align: center; border-radius: 6px;
  transition: background 0.4s ease;
}
.cell-info { display: flex; flex-direction: column; align-items: center; gap: 1px; }
.sign { font-size: 14px; }
.retro { font-size: 9px; padding: 0 3px; border-radius: 3px; background: var(--danger); color: #fff; }
.legend { display: flex; gap: 16px; margin-top: 16px; font-size: 12px; color: var(--text2); flex-wrap: wrap; }
.sw { display: inline-block; width: 14px; height: 14px; border-radius: 3px; vertical-align: middle; margin-right: 4px; }
</style>
