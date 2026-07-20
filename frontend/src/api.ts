// API client — typed wrappers over the backend. Vite proxy forwards /api → :8000.

export interface PlanetPosition {
  planet: string
  symbol: string
  sign: string
  sign_symbol: string
  degree: number
  degree_fmt: string
  longitude: number
  is_retrograde: boolean
  house: number | null
}

export interface Aspect {
  planet1: string
  planet2: string
  type: 'conjunction' | 'opposition' | 'trine' | 'square' | 'sextile'
  orb: number
  influence: 'positive' | 'neutral' | 'negative'
}

export interface MoonPhase {
  name: string
  illumination_pct: number
  phase_angle: number
}

export interface ScoreBreakdown {
  planetary: number
  aspect: number
  transit: number
  personal: number
}

export interface AstroScore {
  ticker: string
  score: number
  direction: 'bull' | 'bear' | 'neutral'
  direction_label: string
  direction_emoji: string
  breakdown: ScoreBreakdown
  computed_at: string
}

export interface BirthChart {
  birth_iso: string
  latitude: number
  longitude: number
  ascendant_deg: number
  ascendant_sign: [string, string]
  houses: Array<{ house: number; sign: string; cusp_deg: number }>
  planets: PlanetPosition[]
  aspects: Aspect[]
}

export interface Transit {
  transiting_planet: string
  natal_planet: string
  type: Aspect['type']
  orb: number
}

async function jget<T>(url: string): Promise<T> {
  const r = await fetch(url)
  if (!r.ok) throw new Error(`${r.status} ${url}`)
  return r.json() as Promise<T>
}

export interface Holding {
  id: string
  ticker: string
  shares: number
  entry_price: number
  note: string | null
}

export interface UserOut {
  id: string
  email: string
  name: string
  birth_iso: string | null
  birth_lat: number | null
  birth_lng: number | null
}

export function authHeaders(): Record<string, string> {
  const tok = localStorage.getItem('astro-token')
  return tok ? { Authorization: `Bearer ${tok}` } : {}
}

export function isLoggedIn(): boolean {
  return !!localStorage.getItem('astro-token')
}

async function jsend<T>(url: string, opts: RequestInit = {}): Promise<T> {
  const r = await fetch(url, { ...opts, headers: { ...authHeaders(), ...(opts.headers || {}) } })
  if (!r.ok) throw new Error(`${r.status} ${url}`)
  return (r.status === 204 ? undefined : r.json()) as Promise<T>
}

export const api = {
  health: () => jget('/api/health'),
  planetPositions: (when?: string) =>
    jget<PlanetPosition[]>('/api/planet-positions' + (when ? `?when=${when}` : '')),
  aspects: (when?: string) =>
    jget<Aspect[]>('/api/aspects' + (when ? `?when=${when}` : '')),
  moonPhase: (when?: string) =>
    jget<MoonPhase>('/api/moon-phase' + (when ? `?when=${when}` : '')),
  birthChart: (birth: string, lat: number, lon: number) =>
    jget<BirthChart>(`/api/birth-chart?birth=${birth}&lat=${lat}&lon=${lon}`),
  transits: (birth: string, when?: string) =>
    jget<Transit[]>(`/api/transits?birth=${birth}` + (when ? `&when=${when}` : '')),
  astroScore: (ticker: string, birth?: string) =>
    jget<AstroScore>(`/api/stocks/${ticker}/astro-score` + (birth ? `?birth=${birth}` : '')),
  prediction: (ticker: string, birth?: string) =>
    jget<{ ticker: string; base_score: number; direction: string; bars: Array<{ day_offset: number; confidence: number }>; note: string }>(
      `/api/stocks/${ticker}/prediction` + (birth ? `?birth=${birth}` : '')),
  quote: (ticker: string) =>
    jget<{ ticker: string; name: string; price: number; change_pct: number; sector: string | null; sector_label: string | null }>(
      `/api/stocks/${ticker}`),
  // auth + portfolio
  register: (email: string, password: string, name: string) =>
    jsend<{ access_token: string; user: UserOut }>('/api/auth/register',
      { method: 'POST', body: JSON.stringify({ email, password, name }), headers: { 'Content-Type': 'application/json' } }),
  login: (email: string, password: string) =>
    jsend<{ access_token: string; user: UserOut }>('/api/auth/login',
      { method: 'POST', body: JSON.stringify({ email, password }), headers: { 'Content-Type': 'application/json' } }),
  me: () => jsend<UserOut>('/api/auth/me'),
  updateMe: (body: Partial<UserOut>) =>
    jsend<UserOut>('/api/auth/me', { method: 'PUT', body: JSON.stringify(body), headers: { 'Content-Type': 'application/json' } }),
  listHoldings: () => jsend<Holding[]>('/api/portfolio'),
  addHolding: (ticker: string, shares: number, entry_price: number, note?: string) =>
    jsend<Holding>('/api/portfolio', { method: 'POST', body: JSON.stringify({ ticker, shares, entry_price, note }), headers: { 'Content-Type': 'application/json' } }),
  deleteHolding: (id: string) => jsend<void>(`/api/portfolio/${id}`, { method: 'DELETE' }),
  // heatmap
  sectorHeatmap: (when?: string) =>
    jget<{ sectors: string[]; planets: string[]; cells: Array<{ sector: string; sector_label: string; planet: string; planet_name: string; sign: string | null; sign_symbol: string | null; is_retrograde: boolean; strength: number }>; computed_at: string }>(
      '/api/sector-heatmap' + (when ? `?when=${when}` : '')),
  // LLM interpret
  interpret: (topic: string, ticker?: string) =>
    jget<{ text: string; model: string; tokens: number | null; reasoning_tokens: number | null; topic: string; ticker: string | null; generated_at: string }>(
      '/api/interpret?topic=' + encodeURIComponent(topic) + (ticker ? `&ticker=${ticker}` : '')),
  // transit alerts
  listAlerts: (unread?: boolean) =>
    jsend<{ id: string; triggered_at: string; transiting_planet: string; natal_planet: string; aspect_type: string; orb: number; text: string; read: boolean }[]>(
      '/api/alerts' + (unread ? '?unread=true' : ''),
    ),
  markAlertRead: (id: string) => jsend<{ id: string; read: boolean }>(`/api/alerts/${id}/read`, { method: 'POST' }),
  // dashboard (P4-C: 天象→板块→个股 联动)
  dashboard: () => jget<{
    computed_at: string
    sectors: Array<{
      sector_key: string
      sector_label: string
      ticker: string
      name: string
      price: number
      change_pct: number
      astro_score: number
      direction: 'bull' | 'bear' | 'neutral'
      direction_label: string
      direction_emoji: string
      linkage: string
    }>
    sky_summary: string
    note: string
  }>('/api/dashboard'),
  // P4-3: 回看任意日天象
  skyHistory: (date: string) => jget<{
    ts: string
    positions: PlanetPosition[]
    aspects: Aspect[]
    moon: { name: string; illumination_pct: number }
    highlighted_aspects: Aspect[]
    note: string
  }>(`/api/sky/history?date=${encodeURIComponent(date)}`),
  // P4-1: 全用户持仓占星分排行
  leaderboard: (limit?: number) => jget<{
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
  }>('/api/leaderboard' + (limit ? `?limit=${limit}` : '')),
  // P4-6: 持仓盈亏占星归因
  attribution: () => jsend<{
    computed_at: string
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
  }>('/api/portfolio/attribution'),
  // P5-2: AI 投资日历
  skyCalendar: (year: number) => jget<{
    year: number
    days: Array<{
      date: string
      aspects: Aspect[]
      mood: string
      mood_emoji: string
      intensity: number
    }>
    note: string
  }>(`/api/sky/calendar?year=${year}`),
}
