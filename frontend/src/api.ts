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
}
